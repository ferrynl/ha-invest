"""Trading 212 export API. Never send broker credentials to report download hosts."""
import base64
import json
import os
import re
import secrets
import threading
import time
from datetime import date,datetime,timezone
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from urllib.error import HTTPError,URLError
from cryptography.fernet import Fernet,InvalidToken
from persistent_cache import cached_json
from .service import preview

_lock=threading.RLock()
EXPORT='/api/v0/equity/history/exports'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def request(url,authorization=None,data=None,csv=False):
    headers={'User-Agent':'Home-Invest','Accept':'text/csv' if csv else 'application/json'}
    if authorization:headers['Authorization']=authorization
    body=None if data is None else json.dumps(data).encode()
    if body:headers['Content-Type']='application/json'
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request(url,data=body,headers=headers),timeout=25) as response:
            raw=response.read(5*1024*1024+1)
            if len(raw)>5*1024*1024:raise ValueError('Trading 212-rapport is groter dan 5 MB. Kies een kortere periode.')
            return raw.decode('utf-8-sig') if csv else json.loads(raw)
    except HTTPError as exc:
        messages={401:'API-sleutel of secret onjuist.',403:'API mist rapportrechten of je IP-adres is niet toegestaan.',429:'Trading 212-aanvraaglimiet bereikt. Wacht minstens een minuut.'}
        raise ValueError(messages.get(exc.code,'Trading 212-aanvraag mislukt. Probeer later opnieuw.')) from None
    except (URLError,TimeoutError,UnicodeError,json.JSONDecodeError):
        raise ValueError('Trading 212 is niet bereikbaar of gaf een ongeldig antwoord.') from None

def write_private(path,content):
    temporary=path.with_suffix('.tmp')
    descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    try:
        os.fchmod(descriptor,0o600) if hasattr(os,'fchmod') else None
        with os.fdopen(descriptor,'wb') as target:target.write(content)
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def vault(store):
    folder=store.root/'connections';folder.mkdir(mode=0o700,exist_ok=True)
    key=folder/'encryption.key'
    if not key.exists():write_private(key,Fernet.generate_key())
    return folder,Fernet(key.read_bytes())

def account(store,account_id):
    with store.connect() as db:
        store.require_account(db,account_id)
        result=dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(account_id,)).fetchone())
    if result['broker']!='Trading 212':raise ValueError('Kies een Trading 212-brokeraccount.')
    return result

def read_connection(store,account_id):
    owner=account(store,account_id);folder,cipher=vault(store);path=folder/f'{account_id}.encrypted'
    if not path.exists():return None
    try:result=json.loads(cipher.decrypt(path.read_bytes()))
    except (InvalidToken,ValueError):raise ValueError('Verbinding kan niet worden gelezen. Sla de API-sleutels opnieuw op.') from None
    if result['owner']!=owner['created_at']:raise ValueError('Brokeraccount is gewijzigd. Verbind opnieuw.')
    return result

def save_connection(store,account_id,key,secret,environment):
    owner=account(store,account_id)
    if environment not in ('live','demo'):raise ValueError('Kies Live of Demo.')
    if not all(isinstance(v,str) and 1<=len(v)<=1024 and not re.search(r'[\s:]',v) for v in (key,secret)):raise ValueError('Vul een geldige API-sleutel en secret in.')
    with _lock:
        folder,cipher=vault(store)
        value=dict(owner=owner['created_at'],key=key,secret=secret,environment=environment,identity=secrets.token_hex(16))
        write_private(folder/f'{account_id}.encrypted',cipher.encrypt(json.dumps(value).encode()))
    return {'saved':True,'environment':environment}

def connection_status(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        return {'saved':bool(value),'environment':value['environment'] if value else None,'pending':bool(value and value.get('job'))}

def forget(store,account_id):
    with _lock:
        account(store,account_id);folder,_=vault(store);(folder/f'{account_id}.encrypted').unlink(missing_ok=True)
    return {'saved':False}

def cancel(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        if not value:raise ValueError('Geen verbinding opgeslagen.')
        value.pop('job',None);persist(store,account_id,value)
    return {'message':'Lokale rapportaanvraag gewist. Je kunt een nieuwe periode aanvragen.'}

def api(value,data=None):
    host='https://'+value['environment']+'.trading212.com'
    authorization='Basic '+base64.b64encode((value['key']+':'+value['secret']).encode()).decode()
    return request(host+EXPORT,authorization,data)

def persist(store,account_id,value):
    folder,cipher=vault(store);write_private(folder/f'{account_id}.encrypted',cipher.encrypt(json.dumps(value).encode()))

def start(store,account_id,start_day,end_day,dividends=True):
    first,last=date.fromisoformat(start_day),date.fromisoformat(end_day)
    if first>last or last>date.today():raise ValueError('Kies een geldige periode tot en met vandaag.')
    with _lock:
        value=read_connection(store,account_id)
        if not value:raise ValueError('Sla eerst een API-verbinding op.')
        if value.get('job'):raise ValueError('Er staat al een rapport klaar of in behandeling. Controleer eerst de rapportstatus.')
        if time.time()-value.get('requested',0)<30:raise ValueError('Wacht 30 seconden voor een nieuw rapport.')
        end=datetime.combine(last,datetime.max.time(),tzinfo=timezone.utc)
        end=min(end,datetime.now(timezone.utc))
        payload={'timeFrom':first.isoformat()+'T00:00:00Z','timeTo':end.isoformat(),'dataIncluded':{'includeOrders':True,'includeDividends':bool(dividends),'includeInterest':False,'includeTransactions':False}}
        # Persist the throttle before the request, including ambiguous timeouts.
        value['requested']=time.time();persist(store,account_id,value)
        result=api(value,payload)
        if not isinstance(result,dict) or not isinstance(result.get('reportId'),int):raise ValueError('Trading 212 gaf geen geldig rapportnummer.')
        value['job']=result['reportId'];persist(store,account_id,value)
        cached_json(store,'trading212',value['identity']+':request:'+str(result['reportId']),86400,lambda:result)
        return {'pending':True,'message':'Rapport aangevraagd. Controleer over een minuut de status.'}

def download_url(url):
    parsed=urlsplit(url)
    host=parsed.hostname or ''
    approved=host.endswith('.trading212.com') or host.endswith('.cloudfront.net') or (host.endswith('.amazonaws.com') and '.s3' in host)
    if parsed.scheme!='https' or not approved or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('Trading 212 gaf een niet-ondersteund downloadadres. Gebruik voorlopig CSV.')
    return url

def poll(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        if not value or not value.get('job'):raise ValueError('Vraag eerst een rapport aan.')
        key=value['identity']+':reports'
        def load_reports():
            if time.time()-value.get('polled',0)<60:raise ValueError('Wacht een minuut voor de volgende statuscontrole.')
            value['polled']=time.time();persist(store,account_id,value)
            return api(value)
        reports=cached_json(store,'trading212',key,60,load_reports)
        if not isinstance(reports,list) or any(not isinstance(r,dict) for r in reports):raise ValueError('Ongeldig Trading 212-rapportoverzicht.')
        report=next((r for r in reports if r.get('reportId')==value['job']),None)
        if not report or report.get('status') in ('Queued','Processing','Running'):return {'pending':True,'message':'Rapport wordt gemaakt. Controleer over een minuut opnieuw.'}
        if report.get('status')!='Finished':
            value.pop('job',None);persist(store,account_id,value)
            raise ValueError('Trading 212 kon dit rapport niet maken. Vraag een nieuw rapport aan.')
        url=download_url(str(report.get('downloadLink','')))
        text=cached_json(store,'trading212',value['identity']+':csv:'+str(value['job']),86400,lambda:request(url,csv=True))
        if account(store,account_id)['created_at']!=value['owner']:raise ValueError('Brokeraccount is tijdens het ophalen gewijzigd. Verbind opnieuw.')
        result=preview(store,account_id,'trading212','Trading 212 API '+str(value['job'])+'.csv',text)
        value.pop('job',None);persist(store,account_id,value)
        return {'pending':False,'preview':result}
