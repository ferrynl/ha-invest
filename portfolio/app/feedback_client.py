"""Opt-in relay client. Credentials/outbox are separate from portfolio restore."""
import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4
from cryptography.fernet import Fernet, InvalidToken
from version import APP_VERSION

_lock=threading.RLock()
UNAVAILABLE='De meldservice is tijdelijk niet bereikbaar. Je melding blijft bewaard.'
INVALID='Vul een geldige titel en beschrijving in en bevestig dat je melding openbaar wordt.'
NOT_CONNECTED='De beheerder moet de meldservice eerst activeren.'


class RelayError(Exception):
    def __init__(self, status=0, retry_after=60):
        self.status,self.retry_after=status,retry_after
        super().__init__('relay_unavailable')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def endpoint(options):
    value=str((options or {}).get('feedback_service_url','')).strip().rstrip('/')
    if not value: return ''
    try:
        url=urlsplit(value)
        valid=url.scheme=='https' and not (url.username or url.password or url.path or url.query or url.fragment) and url.port in (None,443) and re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?',url.hostname or '') and '.' in url.hostname and not url.hostname.replace('.','').isdigit()
    except ValueError: valid=False
    if not valid:
        raise ValueError('Stel een geldig HTTPS-adres voor de meldservice in bij de appconfiguratie.')
    return 'https://'+url.hostname.lower()


def private_write(path, value):
    temporary=path.with_name(path.name+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    try:
        if hasattr(os,'fchmod'): os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as target:
            target.write(value)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists(): temporary.unlink()


def vault(store):
    folder=store.root/'feedback'
    folder.mkdir(mode=0o700,exist_ok=True)
    key=folder/'encryption.key'
    if not key.exists(): private_write(key,Fernet.generate_key())
    return folder/'state.encrypted',Fernet(key.read_bytes())


def read(store):
    path,cipher=vault(store)
    if not path.exists(): return {'entries':[]}
    try: return json.loads(cipher.decrypt(path.read_bytes()))
    except (InvalidToken,ValueError,TypeError):
        raise ValueError('De meldverbinding kan niet worden gelezen. Herstel de volledige appback-up.') from None


def save(store,state):
    path,cipher=vault(store)
    private_write(path,cipher.encrypt(json.dumps(state,separators=(',',':')).encode()))


def transport(origin, path, credential='', data=None):
    headers={'Accept':'application/json','User-Agent':'Home-Invest-feedback'}
    if credential: headers['Authorization']='Bearer '+credential
    body=None if data is None else json.dumps(data,separators=(',',':')).encode()
    if body is not None: headers['Content-Type']='application/json'
    try:
        with build_opener(NoRedirect()).open(Request(origin+path,data=body,headers=headers),timeout=15) as response:
            raw=response.read(1000001)
            if len(raw)>1000000: raise RelayError()
            result=json.loads(raw)
            if not isinstance(result,dict): raise RelayError()
            return result
    except HTTPError as error:
        try: delay=max(60,min(604800,int(error.headers.get('Retry-After','60'))))
        except (ValueError,TypeError): delay=60
        status=error.code
        error.close()
        raise RelayError(status,delay) from None
    except (OSError,ValueError): raise RelayError() from None


def owner(user): return str(user['id']) if user.get('id') is not None else 'home-assistant'


def connect(store,options,data):
    origin=endpoint(options)
    if not origin: raise ValueError('De centrale meldservice is nog niet ingesteld.')
    code=data.get('code')
    if not isinstance(code,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',code.strip()):
        raise ValueError('Vul een geldige eenmalige activeringscode in.')
    code=code.strip()
    with _lock:
        state=read(store)
        if state.get('installation_id') and not state.get('blocked'):
            raise ValueError('Deze installatie is al verbonden met de meldservice.')
        # Persist the locally generated credential before enrollment; retries of a
        # lost enrollment response use the same credential and single-use invitation.
        if state.get('pending_code')!=code or state.get('origin')!=origin:
            state.update(origin=origin,credential=secrets.token_urlsafe(32),pending_code=code)
            save(store,state)
        try: result=transport(origin,'/v1/enroll',data={'code':code,'credential':state['credential']})
        except RelayError as error:
            if error.status in (400,403): raise ValueError('De activeringscode is ongeldig, verlopen of al gebruikt.') from None
            raise ValueError('De meldservice is niet bereikbaar. Probeer activeren later opnieuw.') from None
        try: identity=str(UUID(result['installation_id']))
        except (KeyError,ValueError,TypeError,AttributeError):
            raise ValueError('De meldservice gaf een ongeldig antwoord.') from None
        state.update(installation_id=identity,blocked=False,board_due=0,status_due=0)
        state.pop('pending_code',None)
        save(store,state)
    return {'ok':True}


def enqueue(store,options,user,data):
    origin=endpoint(options)
    title,description=data.get('title'),data.get('description')
    try: request_id=str(UUID(data.get('request_id')))
    except (ValueError,TypeError,AttributeError): raise ValueError(INVALID) from None
    if data.get('public_consent') is not True or data.get('kind') not in ('wish','bug') or not isinstance(title,str) or not isinstance(description,str) or not 1<=len(title.strip())<=120 or not 1<=len(description.strip())<=4000 or '\n' in title or any(ord(c)<32 and c not in '\n\t' for c in title+description):
        raise ValueError(INVALID)
    payload={'request_id':request_id,'kind':data['kind'],'title':title.strip(),'description':description.strip(),'version':APP_VERSION}
    content_hash=hashlib.sha256(json.dumps({k:v for k,v in payload.items() if k!='request_id'},sort_keys=True).encode()).hexdigest()
    with _lock:
        state=read(store)
        if not origin or state.get('origin')!=origin or not state.get('installation_id') or state.get('blocked'): raise ValueError(NOT_CONNECTED)
        entries=state['entries']
        for entry in entries:
            if entry['owner']==owner(user) and entry['request_id']==request_id:
                if entry['digest']!=content_hash: raise ValueError(INVALID)
                return {'ok':True,'request_id':entry['request_id']}
            if entry['owner']==owner(user) and entry['digest']==content_hash and entry['created']>time.time()-86400:
                return {'ok':True,'request_id':entry['request_id']}
        if sum(entry['created']>time.time()-86400 for entry in entries)>=5:
            raise ValueError('Deze installatie heeft de daglimiet van vijf meldingen bereikt.')
        if sum(entry['state']=='local' for entry in entries)>=50 or (len(entries)>=200 and not any(e['state'] in ('open','closed','blocked') for e in entries)):
            raise ValueError('De lokale meldwachtrij is vol. Probeer het later opnieuw.')
        entries.append({'request_id':request_id,'owner':owner(user),'digest':content_hash,'created':time.time(),'payload':payload,'title':payload['title'],'kind':payload['kind'],'state':'local','next_attempt':0,'attempts':0})
        # Bound local history without ever discarding unsent or ambiguous messages.
        while len(entries)>200:
            removable=next((i for i,e in enumerate(entries) if e['state'] in ('open','closed','blocked')),None)
            if removable is None: break
            entries.pop(removable)
        save(store,state)
    return {'ok':True,'request_id':request_id}


def overview(store,options=None,user=None):
    origin=endpoint(options)
    with _lock:
        state=read(store)
        connected=bool(origin and state.get('origin')==origin and state.get('installation_id') and not state.get('blocked'))
        board=state.get('board',{}) if state.get('origin')==origin else {}
        mine=[{k:e.get(k) for k in ('request_id','title','kind','state','number')} for e in state['entries'] if e['owner']==owner(user or {})]
        return {**board,'issues':board.get('issues',[]),'mine':mine,'configured':bool(origin),'connected':connected,'can_connect':bool(user and user.get('role')=='admin'),'limited':board.get('limited',False),'checked_at':board.get('checked_at')}


def pump(store,options):
    origin=endpoint(options)
    if not origin: return
    with _lock:
        state=read(store)
        if state.get('origin')!=origin or not state.get('installation_id') or state.get('blocked'): return
        if state.get('retry_after',0)>time.time(): return
        pending=next((e for e in state['entries'] if e['state']=='local' and e['next_attempt']<=time.time()),None)
        try:
            if pending:
                result=transport(origin,'/v1/submissions',state['credential'],pending['payload'])
                identity=str(UUID(result['id']))
                pending.update(remote_id=identity,state='queued')
                pending.pop('payload',None)
                state['status_due']=0
            elif state.get('status_due',0)<=time.time():
                result=transport(origin,'/v1/submissions',state['credential'])
                remote={row['request_id']:row for row in result['submissions'] if isinstance(row,dict)}
                for entry in state['entries']:
                    update=remote.get(entry['request_id'])
                    if update and update.get('id')==entry.get('remote_id') and update.get('state') in ('queued','uncertain','blocked','open','closed','sending'):
                        entry['state']=update['state']
                        if type(update.get('number')) is int: entry['number']=update['number']
                state['status_due']=time.time()+600
            elif state.get('board_due',0)<=time.time():
                result=transport(origin,'/v1/issues',state['credential'])
                if not isinstance(result.get('issues'),list) or len(result['issues'])>100: raise RelayError()
                items=[]
                for row in result['issues']:
                    if not isinstance(row,dict) or type(row.get('number')) is not int or row.get('kind') not in ('wish','bug','other') or row.get('state') not in ('open','closed') or not isinstance(row.get('title'),str): raise RelayError()
                    items.append({k:row[k] for k in ('number','kind','state','title')})
                state['board']={'issues':items,'limited':bool(result.get('limited')),'checked_at':result.get('checked_at')}
                state['board_due']=time.time()+600
            save(store,state)
        except RelayError as error:
            state['retry_after']=time.time()+error.retry_after
            if error.status in (401,403):
                state['blocked']=True
                for entry in state['entries']:
                    if entry['state']=='local': entry['state']='blocked'
            if pending:
                pending['attempts']+=1
                pending['next_attempt']=time.time()+max(error.retry_after,min(3600,60*2**min(pending['attempts'],6)))
                if error.status in (400,409,413): pending['state']='blocked'
            save(store,state)
        except (KeyError,TypeError,ValueError,AttributeError):
            state['retry_after']=time.time()+300
            save(store,state)


def background(store,options):
    while True:
        try: pump(store,options)
        except Exception:
            from diagnostics import record
            record(store,'WARNING','feedback','relay_failed','Meldservice bijwerken mislukt.',{'code':'relay_unavailable'})
        time.sleep(45+secrets.randbelow(31))
