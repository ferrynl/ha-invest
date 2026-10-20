"""Daily reference FX with durable observations and explicit penny units."""
import json
import re
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from persistent_cache import cached_json
from diagnostics import ActionError

SOURCE='Frankfurter daily reference'

def code(value):
    value=str(value).strip()
    value='GBX' if value in ('GBp','GBX','GBx') else str(value).upper().strip()
    if not re.fullmatch('[A-Z]{3}',value):raise ActionError('Ongeldige valutacode.')
    return value

def unit(value):
    value=code(value)
    return ('GBP',Decimal('0.01')) if value=='GBX' else (value,Decimal(1))

def day_value(value):
    day=date.fromisoformat(value)
    if day>date.today():raise ActionError('Kies een datum tot en met vandaag.')
    return day

def load_json(path):
    request=Request('https://api.frankfurter.dev/v2/'+path,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    try:
        with urlopen(request,timeout=25) as response:
            raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024:raise ActionError('Wisselkoersantwoord te groot.')
            return json.loads(raw,parse_float=Decimal)
    except Exception as exc:
        if isinstance(exc,ValueError) and str(exc)=='Wisselkoersantwoord te groot.':raise
        raise ActionError('Wisselkoersen niet beschikbaar. Opgeslagen koersen blijven behouden; probeer later opnieuw.') from None

def decimal_json(value):
    # Keep exact decimal text while allowing the shared JSON cache to serialize it.
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,list):return [decimal_json(v) for v in value]
    if isinstance(value,dict):return {k:decimal_json(v) for k,v in value.items()}
    return value

def currencies(store):
    def load():
        items=decimal_json(load_json('currencies'))
        if not isinstance(items,list) or not items:raise ActionError('Geen valutaoverzicht beschikbaar.')
        if any(not isinstance(item,dict) or 'iso_code' not in item or not isinstance(item.get('name'),str) for item in items):raise ActionError('Ongeldig valutaoverzicht ontvangen.')
        for item in items:code(item['iso_code']);str(item['name'])
        return items
    result=cached_json(store,'fx','currencies',7*86400,load)
    if not isinstance(result,list):raise ActionError('Ongeldig valutaoverzicht van koersdienst.')
    stamp=datetime.now(timezone.utc).isoformat()
    with store.connect() as db:
        for item in result:
            currency=code(item['iso_code'])
            db.execute('INSERT OR REPLACE INTO fx_currencies VALUES(?,?,?)',(currency,str(item['name'])[:160],stamp))
        db.execute('INSERT OR REPLACE INTO fx_currencies VALUES(?,?,?)',('GBX','Britse pence · 100 GBX = 1 GBP',stamp))
        return [dict(r) for r in db.execute('SELECT * FROM fx_currencies ORDER BY code')]

def save_rates(store,items,last_day):
    if not isinstance(items,list) or not items:raise ActionError('Geen geldige wisselkoersen beschikbaar voor deze periode.')
    if any(not isinstance(item,dict) or not {'base','quote','date','rate'}.issubset(item) or not isinstance(item['date'],str) for item in items):raise ActionError('Ongeldige wisselkoersgegevens ontvangen.')
    validated=[];stamp=datetime.now(timezone.utc).isoformat()
    for item in items:
        base,quote=code(item['base']),code(item['quote']);day=date.fromisoformat(item['date'])
        try:rate=Decimal(str(item['rate']))
        except InvalidOperation:raise ActionError('Ongeldige wisselkoers ontvangen.') from None
        if base!='EUR' or day>last_day or not rate.is_finite() or rate<=0:raise ActionError('Ongeldige wisselkoers of toekomstige koersdatum.')
        validated.append((base,quote,day.isoformat(),str(rate),SOURCE,stamp))
    with store.connect() as db:db.executemany('INSERT OR IGNORE INTO fx_rates VALUES(?,?,?,?,?,?)',validated)

def snapshot(store,day):
    target=day_value(day)
    def load():
        items=decimal_json(load_json('rates?'+urlencode({'base':'EUR','date':day})))
        save_rates(store,items,target)
        return items
    result=cached_json(store,'fx','day:'+day,21600 if target>=date.today()-timedelta(days=7) else 10*365*86400,load)
    save_rates(store,result,target)
    remember_coverage(store,[r['quote'] for r in result],day,day)

def remember_coverage(store,currencies,first,last):
    stamp=datetime.now(timezone.utc).isoformat()
    with store.connect() as db:db.executemany('INSERT OR REPLACE INTO fx_coverage VALUES(?,?,?,?)',[(code(c),first,last,stamp) for c in currencies])

def covered(store,currency,day):
    if currency=='EUR':return True
    with store.connect() as db:row=db.execute('SELECT checked_at FROM fx_coverage WHERE currency=? AND start<=? AND end>=? ORDER BY checked_at DESC LIMIT 1',(currency,day,day)).fetchone()
    return bool(row and (date.fromisoformat(day)<date.today()-timedelta(days=7) or datetime.fromisoformat(row['checked_at'])>datetime.now(timezone.utc)-timedelta(hours=6)))

def observation(store,currency,day):
    if currency=='EUR':return {'rate':'1','day':day,'source':'identity'}
    with store.connect() as db:
        row=db.execute("SELECT rate,day,source FROM fx_rates WHERE base='EUR' AND quote=? AND day<=? AND day>=? ORDER BY day DESC LIMIT 1",(currency,day,(date.fromisoformat(day)-timedelta(days=7)).isoformat())).fetchone()
    return dict(row) if row else None

def get_rate(store,source,target,day):
    source,target=code(source),code(target);requested=day_value(day)
    base,base_scale=unit(source);quote,quote_scale=unit(target)
    if base==quote:return {'rate':str(base_scale/quote_scale),'requested_on':day,'rate_on':day,'source':'Vaste rekeneenheid','from':source,'to':target}
    left,right=observation(store,base,day),observation(store,quote,day)
    if not left or not right or (left['day']!=day and not covered(store,base,day)) or (right['day']!=day and not covered(store,quote,day)):
        snapshot(store,day);left,right=observation(store,base,day),observation(store,quote,day)
    if not left or not right:raise ActionError('Geen historische wisselkoers voor '+source+' → '+target+' op '+day+'. Er is niets geboekt.')
    # Align the cross rate to the same observation day; never mix dates silently.
    actual=min(left['day'],right['day'])
    left=observation(store,base,actual);right=observation(store,quote,actual)
    if not left or not right or (base!='EUR' and quote!='EUR' and left['day']!=right['day']):raise ActionError('Geen gezamenlijke koersdatum beschikbaar voor dit valutapaar.')
    rate=Decimal(right['rate'])/Decimal(left['rate'])*base_scale/quote_scale
    return {'rate':str(rate),'requested_on':day,'rate_on':actual,'source':SOURCE,'from':source,'to':target}

def convert(store,amount,source,target,day):
    try:value=Decimal(str(amount))
    except InvalidOperation:raise ActionError('Ongeldig bedrag.') from None
    if not value.is_finite() or value.copy_abs()>Decimal('1e15'):raise ActionError('Ongeldig bedrag.')
    rate=get_rate(store,source,target,day)
    return {**rate,'amount':str(value),'converted':str(value*Decimal(rate['rate']))}

def prepare_rates(store,requests):
    requests=sorted(set(requests))
    needed=set();days=[]
    for source,target,day in requests:
        first,last=unit(source)[0],unit(target)[0]
        if first==last:continue
        days.append(day_value(day));needed.update({first,last}-{'EUR'})
    if not days:return
    # Fetch only when the required observations are not already in the database.
    if all(observation(store,unit(c)[0],d) and (observation(store,unit(c)[0],d)['day']==d or covered(store,unit(c)[0],d)) for a,b,d in requests for c in (a,b)):return
    first=min(days)-timedelta(days=7);last=max(days)
    while first<=last:
        end=min(date(first.year,12,31),last)
        params={'base':'EUR','quotes':','.join(sorted(needed)),'from':first.isoformat(),'to':end.isoformat()}
        key='history:'+urlencode(params)
        def load():
            items=decimal_json(load_json('rates?'+urlencode(params)))
            save_rates(store,items,end)
            return items
        result=cached_json(store,'fx',key,86400 if end>=date.today()-timedelta(days=7) else 10*365*86400,load)
        save_rates(store,result,end);remember_coverage(store,needed,first.isoformat(),end.isoformat());first=end+timedelta(days=1)

def overview(store,day):
    day_value(day)
    try:available=currencies(store);snapshot(store,day);error=None
    except ValueError as exc:
        error=str(exc)
        with store.connect() as db:available=[dict(r) for r in db.execute('SELECT * FROM fx_currencies ORDER BY code')]
    rates=[]
    for item in available:
        currency=item['code'];base,scale=unit(currency);observed=observation(store,base,day)
        rates.append({**item,'to_eur':str(scale/Decimal(observed['rate'])) if observed else None,'rate_on':observed['day'] if observed else None})
    with store.connect() as db:
        history=[dict(r) for r in db.execute('SELECT * FROM fx_rates ORDER BY day DESC,quote LIMIT 500')]
        audit=[dict(r) for r in db.execute('SELECT * FROM import_fx ORDER BY id DESC LIMIT 100')]
    return {'currencies':rates,'history':history,'conversions':audit,'requested_on':day,'error':error}

def history(store,currency):
    currency=code(currency);underlying,scale=unit(currency)
    with store.connect() as db:rows=[dict(r) for r in db.execute("SELECT * FROM fx_rates WHERE base='EUR' AND quote=? ORDER BY day DESC LIMIT 500",(underlying,))]
    for row in rows:row.update(quote=currency,rate=str(Decimal(row['rate'])/scale))
    return {'currency':currency,'rates':list(reversed(rows))}
