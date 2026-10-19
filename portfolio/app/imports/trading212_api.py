"""Trading 212 export API. Never send broker credentials to report download hosts."""
import base64
import csv
import io
import json
import os
import re
import secrets
import threading
import time
from datetime import date,datetime,timezone,timedelta
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from urllib.error import HTTPError,URLError
from cryptography.fernet import Fernet,InvalidToken
from persistent_cache import cached_json
from .service import preview
from .trading212 import history_reader
from diagnostics import operation,current_record,auth_secrets,DiagnosticError,ActionError,action_context

_lock=threading.RLock()
EXPORT='/api/v0/equity/history/exports'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def request(url,authorization=None,data=None,csv=False):
    started=time.monotonic()
    parsed=urlsplit(url)
    details={'method':'POST' if data is not None else 'GET','endpoint':'report_download' if csv else parsed.path,'environment':'demo' if parsed.hostname=='demo.trading212.com' else 'live' if parsed.hostname=='live.trading212.com' else 'download'}
    if data is not None:details['period']={key:data.get(key) for key in ('timeFrom','timeTo')}
    hidden=auth_secrets(authorization)
    headers={'User-Agent':'Home-Invest','Accept':'text/csv' if csv else 'application/json'}
    if authorization:headers['Authorization']=authorization
    body=None if data is None else json.dumps(data).encode()
    if body:headers['Content-Type']='application/json'
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request(url,data=body,headers=headers),timeout=25) as response:
            raw=response.read(5*1024*1024+1)
            if len(raw)>5*1024*1024:raise ActionError('Trading 212-rapport is groter dan 5 MB. Kies een kortere periode.')
            result=raw.decode('utf-8-sig') if csv else json.loads(raw)
            current_record('INFO','http_response','Trading 212-aanvraag geslaagd.',{**details,'http_status':getattr(response,'status',200),'duration_ms':round((time.monotonic()-started)*1000),'response_bytes':len(raw)},hidden)
            return result
    except HTTPError as exc:
        messages={400:'Trading 212 wijst de rapportaanvraag af. Controleer periode en rapportinstellingen.',401:'API-sleutel of secret onjuist.',403:'API mist rapportrechten of je IP-adres is niet toegestaan.',404:'Trading 212-endpoint niet gevonden. Controleer Live/Demo en bekijk de logs.',408:'Trading 212-aanvraag duurde te lang.',422:'Trading 212 accepteert de aanvraagvelden niet.',429:'Trading 212-aanvraaglimiet bereikt. Wacht minstens een minuut.'}
        provider={};response_format='json'
        try:
            payload=json.loads(exc.read(16384))
            if isinstance(payload,dict):provider={key:payload[key] for key in ('code','errorCode','message','error','detail','errors') if key in payload}
        except (ValueError,OSError,TypeError):response_format='non_json'
        reference=current_record('ERROR','http_error','Trading 212 gaf een HTTP-fout.',{**details,'http_status':exc.code,'duration_ms':round((time.monotonic()-started)*1000),'provider':provider,'response_format':response_format,'request_id':exc.headers.get('x-request-id') if exc.headers else None,'edge_request_id':exc.headers.get('cf-ray') if exc.headers else None,'retry_after':exc.headers.get('Retry-After') if exc.headers else None},hidden)
        hint=messages.get(exc.code,'Trading 212-aanvraag mislukt. Bekijk de logs voor details.')
        raise DiagnosticError(f'{hint} (HTTP {exc.code})'+(f' · Log-ID {reference}' if reference else '')) from None
    except (URLError,TimeoutError,UnicodeError,json.JSONDecodeError) as exc:
        reason='timeout' if isinstance(exc,TimeoutError) else 'invalid_response' if isinstance(exc,(UnicodeError,json.JSONDecodeError)) else 'network'
        reference=current_record('ERROR','connection_error','Trading 212 is niet bereikbaar of gaf een ongeldig antwoord.',{**details,'reason':reason,'error_type':type(exc).__name__,'network_reason':str(exc.reason) if isinstance(exc,URLError) else None,'duration_ms':round((time.monotonic()-started)*1000)},hidden)
        raise DiagnosticError('Trading 212-verbindingsfout: '+reason+(f' · Log-ID {reference}' if reference else '')) from None

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
    if result['broker']!='Trading 212':raise ActionError('Kies een Trading 212-brokeraccount.')
    return result

def read_connection(store,account_id):
    owner=account(store,account_id);folder,cipher=vault(store);path=folder/f'{account_id}.encrypted'
    if not path.exists():return None
    try:result=json.loads(cipher.decrypt(path.read_bytes()))
    except (InvalidToken,ValueError):raise ActionError('Verbinding kan niet worden gelezen. Sla de API-sleutels opnieuw op.') from None
    report_context(result,'connection_loaded')
    if result['owner']!=owner['created_at']:raise ActionError('Brokeraccount is gewijzigd. Verbind opnieuw.')
    return result

def report_context(value,stage):
    plan=value.get('plan') or {}
    parts=plan.get('parts',[]);completed=len(plan.get('completed',[]))
    details={'stage':stage,'environment':value.get('environment'),'report_id':value.get('job'),'completed':completed,'total':len(parts),'has_pending_request':bool(value.get('job') or value.get('plan'))}
    if completed<len(parts):details['period']=parts[completed]
    action_context(**details)

@operation('trading212','connection_save')
def save_connection(store,account_id,key,secret,environment):
    owner=account(store,account_id)
    if environment not in ('live','demo'):raise ActionError('Kies Live of Demo.')
    if not all(isinstance(v,str) and 1<=len(v)<=1024 and not re.search(r'[\s:]',v) for v in (key,secret)):raise ActionError('Vul een geldige API-sleutel en secret in.')
    with _lock:
        folder,cipher=vault(store)
        value=dict(owner=owner['created_at'],key=key,secret=secret,environment=environment,identity=secrets.token_hex(16))
        write_private(folder/f'{account_id}.encrypted',cipher.encrypt(json.dumps(value).encode()))
    return {'saved':True,'environment':environment}

def connection_status(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        result={'saved':bool(value),'environment':value['environment'] if value else None,'pending':bool(value and (value.get('job') or value.get('plan')))}
        if value and value.get('plan'):result.update(completed=len(value['plan']['completed']),total=len(value['plan']['parts']))
        return result

@operation('trading212','connection_remove')
def forget(store,account_id):
    with _lock:
        account(store,account_id);folder,_=vault(store);(folder/f'{account_id}.encrypted').unlink(missing_ok=True)
    return {'saved':False}

@operation('trading212','report_cancel')
def cancel(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        if not value:raise ActionError('Geen verbinding opgeslagen.')
        value.pop('job',None);value.pop('plan',None);persist(store,account_id,value)
    return {'message':'Lokale rapportaanvraag gewist. Je kunt een nieuwe periode aanvragen.'}

def api(value,data=None):
    host='https://'+value['environment']+'.trading212.com'
    authorization='Basic '+base64.b64encode((value['key']+':'+value['secret']).encode()).decode()
    return request(host+EXPORT,authorization,data)

def persist(store,account_id,value):
    folder,cipher=vault(store);write_private(folder/f'{account_id}.encrypted',cipher.encrypt(json.dumps(value).encode()))

def report_periods(first,end):
    # Less than a year even around leap years. Shared boundaries prevent gaps;
    # any boundary transaction is handled by the existing source-ID deduplication.
    parts=[]
    cursor=datetime.combine(first,datetime.min.time(),tzinfo=timezone.utc)
    while cursor<end:
        stop=min(cursor+timedelta(days=364),end)
        parts.append({'start':cursor.isoformat(),'end':stop.isoformat()})
        cursor=stop
    if len(parts)>100:raise ActionError('Kies een periode van maximaal 100 jaar.')
    return parts

def progress(value,message):
    plan=value['plan'];total=len(plan['parts']);done=len(plan['completed'])
    return {'pending':True,'completed':done,'total':total,'message':f'{done} van {total} rapporten opgehaald. '+message}

def submit_part(store,account_id,value):
    if time.time()-value.get('requested',0)<30:
        return progress(value,'De volgende aanvraag volgt bij de volgende statuscontrole; wacht minstens 30 seconden.')
    report_context(value,'request_part')
    plan=value['plan'];part=plan['parts'][len(plan['completed'])]
    payload={'timeFrom':part['start'],'timeTo':part['end'],'dataIncluded':{'includeOrders':True,'includeDividends':plan['dividends'],'includeInterest':False,'includeTransactions':False}}
    value['requested']=time.time();persist(store,account_id,value)
    result=api(value,payload)
    if not isinstance(result,dict) or not isinstance(result.get('reportId'),int):raise ActionError('Trading 212 gaf geen geldig rapportnummer.')
    value['job']=result['reportId'];persist(store,account_id,value)
    cached_json(store,'trading212',value['identity']+':request:'+str(result['reportId']),86400,lambda:result)
    return progress(value,'Rapport aangevraagd. Controleer over een minuut de status.')

@operation('trading212','report_request')
def start(store,account_id,start_day,end_day,dividends=True):
    first,last=date.fromisoformat(start_day),date.fromisoformat(end_day)
    if first>last or last>date.today():raise ActionError('Kies een geldige periode tot en met vandaag.')
    with _lock:
        value=read_connection(store,account_id)
        if not value:raise ActionError('Sla eerst een API-verbinding op.','connection_missing')
        if value.get('job') or value.get('plan'):raise ActionError('Er staat al een rapportaanvraag klaar of in behandeling. Gebruik Rapportstatus controleren en ophalen om verder te gaan.','request_already_pending')
        if time.time()-value.get('requested',0)<30:raise ActionError('Wacht 30 seconden voor een nieuw rapport.','request_cooldown',{'retry_after_seconds':max(1,round(30-(time.time()-value.get('requested',0))))})
        end=min(datetime.combine(last,datetime.max.time(),tzinfo=timezone.utc),datetime.now(timezone.utc))
        value['plan']={'parts':report_periods(first,end),'completed':[],'dividends':bool(dividends)}
        persist(store,account_id,value)
        return submit_part(store,account_id,value)

def combined_report(store,value):
    report_context(value,'combine_reports')
    output=io.StringIO();columns=[];readers=[];size=0;count=0
    for report_id in value['plan']['completed']:
        key=value['identity']+':csv:'+str(report_id)
        with store.connect() as db:cached=db.execute("SELECT payload FROM api_cache WHERE namespace='trading212' AND cache_key=?",(key,)).fetchone()
        if not cached:raise ActionError('Een deelrapport ontbreekt in de lokale cache. Wis de aanvraag en probeer opnieuw.')
        text=json.loads(cached['payload']);size+=len(text)
        if size>5*1024*1024:raise ActionError('Gecombineerd rapport is groter dan 5 MB. Kies een kortere periode.')
        try:reader=history_reader(text)
        except ValueError:
            fields=csv.DictReader(io.StringIO(text.lstrip('\ufeff'))).fieldnames or []
            raise ActionError('Trading 212 gaf een niet-ondersteund CSV-rapport. Verwacht Action, Time of Time (UTC), Ticker en Name, zonder dubbele kolommen.','csv_columns_missing',{'received_columns':fields}) from None
        for column in reader.fieldnames:
            if column not in columns:columns.append(column)
        readers.append(reader)
    writer=csv.DictWriter(output,fieldnames=columns);writer.writeheader()
    for reader in readers:
        for row in reader:
            count+=1
            if count>10000:raise ActionError('Meer dan 10.000 transacties. Wis de aanvraag en kies een kortere periode.')
            if None in row:raise ActionError('Trading 212 CSV bevat meer waarden dan kolommen.','csv_row_invalid')
            writer.writerow(row)
        if output.tell()>5*1024*1024:raise ActionError('Gecombineerd rapport is groter dan 5 MB. Kies een kortere periode.')
    return output.getvalue() if count else None


def download_url(url):
    parsed=urlsplit(url)
    host=parsed.hostname or ''
    approved=host.endswith('.trading212.com') or host.endswith('.cloudfront.net') or (host.endswith('.amazonaws.com') and '.s3' in host)
    if parsed.scheme!='https' or not approved or parsed.username or parsed.password or parsed.port not in (None,443):raise ActionError('Trading 212 gaf een niet-ondersteund downloadadres. Gebruik voorlopig CSV.','download_host_rejected',{'download_host':host,'scheme':parsed.scheme})
    return url

@operation('trading212','report_poll')
def poll(store,account_id):
    with _lock:
        value=read_connection(store,account_id)
        if not value or not (value.get('job') or value.get('plan')):raise ActionError('Vraag eerst een rapport aan. Er is geen lopende lokale rapportaanvraag.','request_missing')
        if value.get('plan') and not value.get('job'):
            if len(value['plan']['completed'])<len(value['plan']['parts']):return submit_part(store,account_id,value)
            return finish_plan(store,account_id,value)
        report_context(value,'poll_report')
        key=value['identity']+':reports'
        def load_reports():
            if time.time()-value.get('polled',0)<60:raise ActionError('Wacht een minuut voor de volgende statuscontrole.','poll_cooldown',{'retry_after_seconds':max(1,round(60-(time.time()-value.get('polled',0))))})
            value['polled']=time.time();persist(store,account_id,value)
            return api(value)
        reports=cached_json(store,'trading212',key,60,load_reports)
        if not isinstance(reports,list) or any(not isinstance(r,dict) for r in reports):raise ActionError('Ongeldig Trading 212-rapportoverzicht.')
        report=next((r for r in reports if r.get('reportId')==value['job']),None)
        if not report or report.get('status') in ('Queued','Processing','Running'):
            return progress(value,'Rapport wordt gemaakt. Controleer over een minuut opnieuw.') if value.get('plan') else {'pending':True,'message':'Rapport wordt gemaakt. Controleer over een minuut opnieuw.'}
        if report.get('status')!='Finished':
            value.pop('job',None);persist(store,account_id,value)
            raise ActionError('Trading 212 kon dit rapport niet maken. Controleer opnieuw om dit deel opnieuw aan te vragen, of wis de lokale aanvraag.','report_failed',{'report_status':report.get('status')})
        report_context(value,'download_report')
        url=download_url(str(report.get('downloadLink','')))
        text=cached_json(store,'trading212',value['identity']+':csv:'+str(value['job']),86400,lambda:request(url,csv=True))
        if account(store,account_id)['created_at']!=value['owner']:raise ActionError('Brokeraccount is tijdens het ophalen gewijzigd. Verbind opnieuw.')
        if value.get('plan'):
            value['plan']['completed'].append(value.pop('job'));persist(store,account_id,value)
            if len(value['plan']['completed'])<len(value['plan']['parts']):return submit_part(store,account_id,value)
            return finish_plan(store,account_id,value)
        result=preview(store,account_id,'trading212','Trading 212 API '+str(value['job'])+'.csv',text)
        value.pop('job',None);persist(store,account_id,value)
        return {'pending':False,'preview':result}

def finish_plan(store,account_id,value):
    text=combined_report(store,value)
    report_context(value,'create_preview')
    result=preview(store,account_id,'trading212','Trading 212 API gecombineerde periode.csv',text) if text else None
    total=len(value['plan']['parts'])
    value.pop('plan',None);persist(store,account_id,value)
    if result:return {'pending':False,'preview':result,'completed':total,'total':total}
    return {'pending':False,'message':'Alle rapporten opgehaald. Geen transacties gevonden in deze periode.'}
