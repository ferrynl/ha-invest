"""One serialized GitHub worker, scoped installation tokens, fail-closed POST recovery."""
import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class GitHubFailure(Exception):
    def __init__(self, status=0, retry_after=60):
        self.status, self.retry_after = status, retry_after
        super().__init__('github_unavailable')


def b64(value): return base64.urlsafe_b64encode(value).rstrip(b'=')


class GitHub:
    def __init__(self, app_id, installation_id, repository_id, private_key):
        self.app_id, self.installation_id, self.repository_id = int(app_id), int(installation_id), int(repository_id)
        if min(self.app_id,self.installation_id,self.repository_id) < 1: raise ValueError('invalid_github_configuration')
        key_bytes=private_key if isinstance(private_key,bytes) else Path(private_key).read_bytes()
        self.key=serialization.load_pem_private_key(key_bytes,password=None)
        if not isinstance(self.key,rsa.RSAPrivateKey) or self.key.key_size<2048: raise ValueError('invalid_app_key')
        self.token, self.expires = '', 0
        self.opener=build_opener(NoRedirect())

    def request(self, path, token, data=None, etag=None):
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'Home-Invest-feedback-service','X-GitHub-Api-Version':'2026-03-10'}
        if etag: headers['If-None-Match']=etag
        body=None if data is None else json.dumps(data).encode()
        if body: headers['Content-Type']='application/json'
        request=Request('https://api.github.com'+path,data=body,headers=headers)
        try:
            with self.opener.open(request,timeout=15) as response:
                raw=response.read(2000001)
                if len(raw)>2000000: raise GitHubFailure()
                return json.loads(raw),response.headers.get('ETag')
        except HTTPError as error:
            if error.code==304: return None,etag
            try:
                retry=max(60,int(error.headers.get('Retry-After','0')),int(error.headers.get('X-RateLimit-Reset','0'))-int(time.time()))
            except (ValueError,TypeError): retry=60
            error.close()
            raise GitHubFailure(error.code,retry) from None
        except (OSError,ValueError): raise GitHubFailure() from None

    def access_token(self):
        if self.expires>time.time()+120: return self.token
        now=int(time.time())
        parts=[b64(json.dumps({'alg':'RS256','typ':'JWT'},separators=(',',':')).encode()),b64(json.dumps({'iat':now-60,'exp':now+540,'iss':str(self.app_id)},separators=(',',':')).encode())]
        unsigned=b'.'.join(parts)
        jwt=(unsigned+b'.'+b64(self.key.sign(unsigned,padding.PKCS1v15(),hashes.SHA256()))).decode()
        data,_=self.request(f'/app/installations/{self.installation_id}/access_tokens',jwt,{'repository_ids':[self.repository_id],'permissions':{'issues':'write'}})
        self.token=data['token']
        self.expires=datetime.fromisoformat(data['expires_at'].replace('Z','+00:00')).timestamp()
        return self.token

    def create(self, job):
        payload=json.loads(job['payload'])
        prefix='[Bug] ' if payload['kind']=='bug' else '[Wens] '
        body=payload['description']+'\n\nHome Invest '+payload['version']+'\n\n<!-- home-invest:'+job['id']+' -->'
        return self.request('/repos/ferrynl/ha-invest/issues',self.access_token(),{'title':prefix+payload['title'],'body':body})[0]

    def board(self, etag=None):
        rows,etag=self.request('/repos/ferrynl/ha-invest/issues?state=all&sort=updated&direction=desc&per_page=100',self.access_token(),etag=etag)
        if rows is None: return None,etag
        if not isinstance(rows,list): raise GitHubFailure()
        items=[]
        for row in rows:
            if not isinstance(row,dict) or 'pull_request' in row or type(row.get('number')) is not int: continue
            labels={str(label.get('name','')).lower() for label in row.get('labels',[]) if isinstance(label,dict)}
            title=str(row.get('title',''))[:300]
            kind='bug' if 'bug' in labels or title.lower().startswith('[bug]') else 'wish' if labels & {'enhancement','wish','feature'} or title.lower().startswith('[wens]') else 'other'
            items.append({'number':row['number'],'title':title,'kind':kind,'state':'closed' if row.get('state')=='closed' else 'open'})
        return {'issues':items,'limited':len(rows)==100,'checked_at':datetime.now(timezone.utc).isoformat()},etag


class Worker:
    def __init__(self, store, github):
        self.store,self.github=store,github

    def step(self):
        self.store.prune()
        if self.store.get_meta('github_after',0)>time.time(): return
        job=self.store.claim()
        if job:
            try:
                result=self.github.create(job)
                if type(result.get('number')) is not int: raise GitHubFailure()
                self.store.mark(job['id'],'open',result['number'])
                self.store.set_meta('board_due',0)
            except GitHubFailure as error:
                # Only an explicit rate-limit rejection is safe to retry. Timeouts,
                # redirects and 5xx may happen AFTER GitHub created the issue.
                self.store.mark(job['id'],'queued' if error.status==429 else 'uncertain')
                self.store.set_meta('github_after',time.time()+error.retry_after)
            return
        if self.store.get_meta('board_due',0)>time.time(): return
        try:
            board,etag=self.github.board(self.store.get_meta('board_etag'))
            if board:
                self.store.set_meta('board',board)
                for issue in board['issues']:
                    with self.store.db() as db:
                        db.execute("UPDATE jobs SET state=? WHERE number=? AND state IN ('open','closed')",(issue['state'],issue['number']))
            self.store.set_meta('board_etag',etag)
            self.store.set_meta('board_due',time.time()+600)
        except GitHubFailure as error:
            self.store.set_meta('github_after',time.time()+error.retry_after)
            self.store.set_meta('board_due',time.time()+600)

    def run(self, stop):
        self.store.recover()
        while not stop.is_set():
            try: self.step()
            except Exception:
                # Never print response bodies, payloads, tokens or tracebacks.
                try: self.store.set_meta('github_after',time.time()+300)
                except Exception: pass
                print('worker_temporarily_unavailable',flush=True)
                stop.wait(60)
            stop.wait(2)
