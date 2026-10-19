"""Bounded, persistent diagnostics with centralized redaction and request context."""
import base64
import json
import re
import sqlite3
import time
from contextvars import ContextVar
from datetime import datetime,timedelta,timezone
from functools import wraps
from uuid import uuid4

context=ContextVar('diagnostic_context',default=None)
SENSITIVE=re.compile(r'authorization|password|secret|token|cookie|api.?key|download.?link|signature|credential',re.I)

def scrub(value,secrets=(),depth=0):
    if depth>5:return '[afgekapt]'
    if isinstance(value,dict):return {str(k)[:80]:'[afgeschermd]' if SENSITIVE.search(str(k)) else scrub(v,secrets,depth+1) for k,v in list(value.items())[:40]}
    if isinstance(value,(list,tuple)):return [scrub(v,secrets,depth+1) for v in value[:30]]
    if isinstance(value,(int,float,bool)) or value is None:return value
    text=str(value)
    for secret in sorted((str(v) for v in secrets if v),key=len,reverse=True):text=text.replace(secret,'[afgeschermd]')
    text=re.sub(r'https?://[^\s<>"\']+', '[URL afgeschermd]',text,flags=re.I)
    text=re.sub(r'\b(?:Basic|Bearer)\s+[A-Za-z0-9+/=._-]+','[autorisatie afgeschermd]',text,flags=re.I)
    text=re.sub(r'(?i)(api[_ -]?key|secret|password|token|authorization|cookie|signature)\s*[=:]\s*[^\s,;]+',r'\1=[afgeschermd]',text)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[e-mail afgeschermd]',text)
    return ''.join(c for c in text if c.isprintable() or c=='\n')[:1200]

def auth_secrets(authorization):
    values=[authorization]
    if authorization and authorization.startswith('Basic '):
        try:values.extend(base64.b64decode(authorization[6:]).decode().split(':',1));values.append(authorization[6:])
        except (ValueError,UnicodeError):pass
    return values

def record(store,level,source,event,message,details=None,secrets=(),reference=None):
    reference=reference or uuid4().hex[:12]
    try:
        stamp=datetime.now(timezone.utc)
        with store.connect() as db:
            db.execute('INSERT INTO app_logs(created_at,level,source,event,message,details,reference) VALUES(?,?,?,?,?,?,?)',(stamp.isoformat(),level if level in ('INFO','WARNING','ERROR') else 'INFO',scrub(source,secrets),scrub(event,secrets),scrub(message,secrets),json.dumps(scrub(details or {},secrets),ensure_ascii=False),reference))
            db.execute('DELETE FROM app_logs WHERE created_at<?',((stamp-timedelta(days=7)).isoformat(),))
            db.execute('DELETE FROM app_logs WHERE id NOT IN (SELECT id FROM app_logs ORDER BY id DESC LIMIT 5000)')
    except (sqlite3.Error,OSError):pass  # Diagnostics must never break the financial operation.
    return reference

def current_record(level,event,message,details=None,secrets=()):
    current=context.get()
    if not current:return None
    return record(current['store'],level,current['source'],event,message,{**current['details'],**(details or {})},secrets)

class DiagnosticError(ValueError):pass

def operation(source,event):
    def decorate(function):
        @wraps(function)
        def wrapped(store,account_id,*args,**kwargs):
            token=context.set(dict(store=store,source=source,details={'account_id':account_id,'operation':event}))
            started=time.monotonic()
            try:
                result=function(store,account_id,*args,**kwargs)
                current_record('INFO',event,'Actie afgerond.',{'duration_ms':round((time.monotonic()-started)*1000),'pending':result.get('pending') if isinstance(result,dict) else None})
                return result
            except DiagnosticError:raise
            except Exception as exc:
                # Arguments and exception text may contain credentials; never log them here.
                reference=current_record('WARNING' if isinstance(exc,ValueError) else 'ERROR',event,'Actie niet afgerond.',{'error_type':type(exc).__name__,'duration_ms':round((time.monotonic()-started)*1000)})
                if isinstance(exc,ValueError):raise DiagnosticError(str(exc)+(f' · Log-ID {reference}' if reference else '')) from None
                raise
            finally:context.reset(token)
        return wrapped
    return decorate

def read_logs(store,level='',source='',before=0,query=''):
    if level not in ('','INFO','WARNING','ERROR'):raise ValueError('Ongeldig logniveau.')
    if len(source)>80 or before<0 or len(query)>100:raise ValueError('Ongeldig logfilter.')
    clauses=[];values=[]
    for column,value in (('level',level),('source',source)):
        if value:clauses.append(column+'=?');values.append(value)
    if before:clauses.append('id<?');values.append(before)
    if query:
        clauses.append('(instr(reference,?)>0 OR instr(lower(message),lower(?))>0 OR instr(lower(event),lower(?))>0)');values.extend([query]*3)
    with store.connect() as db:
        cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
        db.execute('DELETE FROM app_logs WHERE created_at<?',(cutoff,))
        rows=[dict(r) for r in db.execute('SELECT * FROM app_logs'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY id DESC LIMIT 101',values)]
        sources=[r[0] for r in db.execute('SELECT DISTINCT source FROM app_logs ORDER BY source')]
    for row in rows:row['details']=json.loads(row['details'])
    return {'entries':rows[:100],'sources':sources,'next_before':rows[99]['id'] if len(rows)>100 else None,'retention_days':7,'max_entries':5000}
