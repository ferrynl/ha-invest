import hashlib
import hmac
import http.client
import json
import secrets
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from feedback_service.store import RelayStore,Rejected
from feedback_service.github import Worker,GitHubFailure,GitHub
from feedback_service.server import LimitedServer,make_handler
import feedback_client as client
from storage import Store


def submission(**kwargs):
    return dict(request_id=str(uuid4()),kind='bug',title='<img src=x>',description='Steps to reproduce',version='0.39.0',**kwargs)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=RelayStore(Path(self.tmp.name)/'relay.sqlite3','s'*32)
        self.credential=secrets.token_urlsafe(32)
        self.code=self.store.invite()
        self.identity=self.store.enroll(self.code,self.credential)

    def test_activation_idempotent_scoped_revocable_and_hashed(self):
        self.assertEqual(self.store.enroll(self.code,self.credential),self.identity)
        with self.assertRaises(Rejected):self.store.enroll(self.code,secrets.token_urlsafe(32))
        self.assertEqual(self.store.authenticate(self.credential),self.identity)
        with self.store.db() as db:
            stored=[dict(r) for r in db.execute('SELECT * FROM installations')]
            self.assertNotIn(self.credential,json.dumps(stored))
            self.assertNotIn(self.code,json.dumps([dict(r) for r in db.execute('SELECT * FROM invitations')]))
        self.store.revoke(self.identity)
        with self.assertRaises(Rejected):self.store.authenticate(self.credential)
        with self.assertRaises(Rejected):self.store.enroll(self.code,self.credential)
        with self.assertRaises(Rejected):self.store.submit(self.identity,submission())

    def test_enrollment_expiry_and_rejected_attempts_are_throttled(self):
        with self.store.db() as db:db.execute('UPDATE invitations SET expires=0')
        with self.assertRaises(Rejected):self.store.enroll(self.code,self.credential)
        for _ in range(30):self.store.throttle('192.0.2.1','enrollment',30)
        with self.assertRaises(Rejected) as error:self.store.throttle('192.0.2.1','enrollment',30)
        self.assertEqual(error.exception.status,429)
        self.assertGreater(error.exception.retry_after,0)

    def test_durable_idempotency_payload_conflicts_isolation_and_limits(self):
        data=submission();result=self.store.submit(self.identity,data)
        self.assertEqual(result,self.store.submit(self.identity,data))
        with self.assertRaises(Rejected) as error:self.store.submit(self.identity,{**data,'title':'Changed'})
        self.assertEqual(error.exception.status,409)
        other=self.store.enroll(self.store.invite(),secrets.token_urlsafe(32))
        self.assertEqual(self.store.mine(other),[])
        for _ in range(4):self.store.submit(self.identity,submission())
        with self.assertRaises(Rejected) as error:self.store.submit(self.identity,submission())
        self.assertEqual(error.exception.status,429)
        again=RelayStore(self.store.path,'s'*32)
        self.assertEqual(len(again.mine(self.identity)),5)
        self.assertEqual(again.submit(self.identity,data),result)

    def test_never_retry_an_ambiguous_github_post_after_timeout_or_restart(self):
        self.store.submit(self.identity,submission())
        github=Mock();github.create.side_effect=GitHubFailure()
        Worker(self.store,github).step()
        self.assertEqual(self.store.mine(self.identity)[0]['state'],'uncertain')
        self.store.set_meta('github_after',0)
        self.store.set_meta('board_due',time.time()+600)
        self.store.recover();Worker(self.store,github).step()
        github.create.assert_called_once()
        self.store.submit(self.identity,submission())
        self.assertIsNotNone(self.store.claim())
        self.store.recover()
        self.assertTrue(all(r['state']=='uncertain' for r in self.store.mine(self.identity)))

    def test_explicit_rate_limit_waits_then_publishes_once_and_erases_body(self):
        result=self.store.submit(self.identity,submission())
        github=Mock();github.create.side_effect=[GitHubFailure(429,123),{'number':17}]
        worker=Worker(self.store,github);worker.step();worker.step()
        self.assertEqual(github.create.call_count,1)
        self.assertGreater(self.store.get_meta('github_after'),time.time()+100)
        self.store.set_meta('github_after',0);worker.step()
        self.assertEqual(self.store.mine(self.identity)[0]['number'],17)
        with self.store.db() as db:self.assertEqual(db.execute('SELECT payload FROM jobs WHERE id=?',(result['id'],)).fetchone()[0],'')

    def test_token_request_only_grants_issues_to_the_single_repository(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        github=GitHub(1,2,3,pem)
        expiry='2099-01-01T00:00:00Z'
        with patch.object(github,'request',return_value=({'token':'private','expires_at':expiry},None)) as request:
            self.assertEqual(github.access_token(),'private')
            github.access_token();request.assert_called_once()
            args=request.call_args.args
            self.assertEqual(args[0],'/app/installations/2/access_tokens')
            self.assertEqual(args[2],{'repository_ids':[3],'permissions':{'issues':'write'}})
        with patch.object(github,'request',return_value=({'number':1},None)) as request:
            github.create({'id':str(uuid4()),'payload':json.dumps(submission())})
            self.assertNotIn('assignees',request.call_args.args[2])


class RelayHttpTests(unittest.TestCase):
    setUp=RelayTests.setUp
    def test_http_auth_scope_webhook_signatures_replay_and_revocation(self):
        server=LimitedServer(('127.0.0.1',0),make_handler(self.store,'w'*32,99))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,body=None,headers=None):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            try:
                conn.request('POST' if body else 'GET',path,body,headers or {})
                response=conn.getresponse();return response.status,json.loads(response.read())
            finally:conn.close()
        try:
            self.assertEqual(request('/v1/issues')[0],401)
            headers={'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'}
            data=submission()
            code,result=request('/v1/submissions',json.dumps(data),headers);self.assertEqual(code,202)
            self.assertEqual(request('/v1/submissions',json.dumps(data),headers)[1],result)
            self.store.mark(result['id'],'open',123)
            payload=json.dumps({'repository':{'id':99},'issue':{'number':123,'state':'closed'}}).encode()
            signed={'Content-Type':'application/json','X-Hub-Signature-256':'sha256='+hmac.new(b'w'*32,payload,hashlib.sha256).hexdigest(),'X-GitHub-Delivery':str(uuid4()),'X-GitHub-Event':'issues'}
            self.assertEqual(request('/v1/github-webhook',payload,{**signed,'X-Hub-Signature-256':'wrong'})[0],401)
            self.assertEqual(self.store.mine(self.identity)[0]['state'],'open')
            self.assertEqual(request('/v1/github-webhook',payload,signed)[0],202)
            self.assertEqual(request('/v1/github-webhook',payload,signed)[0],202)
            self.assertEqual(self.store.mine(self.identity)[0]['state'],'closed')
            wrong=payload.replace(b'99',b'98');bad={**signed,'X-GitHub-Delivery':str(uuid4()),'X-Hub-Signature-256':'sha256='+hmac.new(b'w'*32,wrong,hashlib.sha256).hexdigest()}
            self.assertEqual(request('/v1/github-webhook',wrong,bad)[0],400)
            self.store.revoke(self.identity)
            self.assertEqual(request('/v1/submissions',headers=headers)[0],401)
            self.assertEqual(request('/health')[1],{'ok':True})
        finally:server.shutdown();server.server_close();thread.join()


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.options={'feedback_service_url':'https://meldingen.home-invest.nl'}
        self.user={'id':7,'role':'basic'}

    def activate(self):
        with patch('feedback_client.transport',return_value={'installation_id':str(uuid4())}):
            client.connect(self.store,self.options,{'code':secrets.token_urlsafe(32)})

    def data(self):return {**submission(),'public_consent':True}

    def test_disabled_by_default_and_https_only(self):
        self.assertFalse(client.overview(self.store,{},self.user)['connected'])
        for value in ('http://example.org','https://user:password@example.org','https://127.0.0.1','https://example.org/path','https://example.org?token=secret'):
            with self.assertRaises(ValueError):client.endpoint({'feedback_service_url':value})
        with self.assertRaises(ValueError):client.enqueue(self.store,self.options,self.user,self.data())

    def test_local_encrypted_queue_preserves_identity_deduplicates_and_scopes(self):
        self.activate();data=self.data();first=client.enqueue(self.store,self.options,self.user,data)
        self.assertEqual(first,client.enqueue(self.store,self.options,self.user,{**data,'request_id':str(uuid4())}))
        again=Store(self.tmp.name)
        self.assertEqual(len(client.overview(again,self.options,self.user)['mine']),1)
        self.assertEqual(client.overview(again,self.options,{'id':8})['mine'],[])
        encrypted=(self.store.root/'feedback/state.encrypted').read_bytes()
        self.assertNotIn(b'Steps to reproduce',encrypted)
        changed={**data,'title':'Changed'}
        with self.assertRaises(ValueError):client.enqueue(self.store,self.options,self.user,changed)
        with self.assertRaises(ValueError):client.enqueue(self.store,self.options,self.user,{**self.data(),'public_consent':False})

    def test_network_loss_retries_same_request_id_without_portfolio_or_user_fields(self):
        self.activate();data=self.data();client.enqueue(self.store,self.options,self.user,data)
        with patch('feedback_client.transport',side_effect=client.RelayError()):client.pump(self.store,self.options)
        state=client.read(self.store);entry=state['entries'][0]
        self.assertEqual(entry['state'],'local')
        self.assertGreater(entry['next_attempt'],time.time())
        state['retry_after']=0;entry['next_attempt']=0;client.save(self.store,state)
        with patch('feedback_client.transport',return_value={'id':str(uuid4()),'state':'queued'}) as request:
            client.pump(self.store,self.options)
            sent=request.call_args.args[3]
            self.assertEqual(set(sent),{'request_id','kind','title','description','version'})
            self.assertEqual(sent['request_id'],data['request_id'])
        self.assertEqual(client.read(self.store)['entries'][0]['state'],'queued')
        self.assertNotIn('payload',client.read(self.store)['entries'][0])

    def test_lost_enrollment_response_reuses_same_credential_and_does_not_leak_to_new_host(self):
        code=secrets.token_urlsafe(32)
        with patch('feedback_client.transport',side_effect=client.RelayError()):
            with self.assertRaises(ValueError):client.connect(self.store,self.options,{'code':code})
        credential=client.read(self.store)['credential']
        with patch('feedback_client.transport',return_value={'installation_id':str(uuid4())}) as request:
            client.connect(self.store,self.options,{'code':code})
            self.assertEqual(request.call_args.kwargs['data']['credential'],credential)
        other={'feedback_service_url':'https://other.example.org'}
        with patch('feedback_client.transport') as request:
            client.pump(self.store,other);request.assert_not_called()
        self.assertFalse(client.overview(self.store,other,self.user)['connected'])

    def test_portfolio_restore_does_not_import_or_replace_the_relay_identity(self):
        from restore import restore_backup
        self.activate();before=client.read(self.store)['credential']
        client.enqueue(self.store,self.options,self.user,self.data())
        backup=self.store.backup()
        restore_backup(self.store,Path(backup).read_bytes())
        self.assertEqual(client.read(self.store)['credential'],before)
        self.assertEqual(len(client.read(self.store)['entries']),1)


if __name__=='__main__':unittest.main()
