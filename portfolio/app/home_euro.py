"""A combined EUR view with dated cash flows and explicit missing FX."""
from bisect import bisect_right
from datetime import date
from decimal import Decimal
from forex import unit,prepare_rates
from history import daily_values,with_dividends
from diagnostics import record

def identity(row):return tuple(row[k] for k in ('account_id','symbol','exchange','currency'))
def build(snapshot,rates,account='all',today=None,include_history=True,skip_invalid=False,sparse_history=False):
    today=today or date.today();owner=None
    if str(account)!='all':
        try:owner=int(account)
        except (ValueError,TypeError):raise ValueError('Ongeldig brokeraccount.') from None
        if not any(a['id']==owner for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    indexed={}
    for row in rates:
        if row['base']=='EUR':indexed.setdefault(row['quote'],[]).append(row)
    for rows in indexed.values():rows.sort(key=lambda row:row['day'])
    days={currency:[row['day'] for row in rows] for currency,rows in indexed.items()};used=set();positions=[];excluded=[]
    def rate(currency,day):
        base,scale=unit(currency)
        if base=='EUR':return scale,day
        i=bisect_right(days.get(base,[]),day)-1
        if i<0:return None
        row=indexed[base][i]
        if (date.fromisoformat(day)-date.fromisoformat(row['day'])).days>7:return None
        used.add((currency,day,row['day']));return scale/Decimal(row['rate']),row['day']
    trades={};income={}
    for row in snapshot['purchases']:trades.setdefault(identity(row),[]).append(row)
    for row in snapshot['dividends']:income.setdefault(identity(row),[]).append(row)
    for p in snapshot['positions']:
        if owner is not None and p['account_id']!=owner:continue
        try:
            if skip_invalid:
                for field in ('quantity','cost','value','realised','dividend'):
                    raw=p.get(field)
                    if raw is None or str(raw).strip()=='' or not Decimal(str(raw)).is_finite():raise ValueError()
                if Decimal(p['quantity'])<0:raise ValueError()
            key=identity(p);lots=trades[key];dividends=income.get(key,[]);converted=[];converted_income=[];missing=[]
            for row in lots:
                if skip_invalid and (not Decimal(row['price']).is_finite() or not Decimal(row['quantity']).is_finite() or Decimal(row['quantity'])<=0):raise ValueError()
                fx=(Decimal(1),row['purchased_on']) if row['split_before'] else rate(p['currency'],row['purchased_on'])
                if fx is None:missing.append(row['purchased_on']);continue
                converted.append({**row,'price':str(Decimal(row['price'])*fx[0]),'currency':'EUR'})
            for row in dividends:
                if skip_invalid:
                    date.fromisoformat(row['paid_on'])
                    if not Decimal(row['amount']).is_finite():raise ValueError()
                fx=rate(p['currency'],row['paid_on'])
                if fx is None:missing.append(row['paid_on']);continue
                converted_income.append({**row,'amount':str(Decimal(row['amount'])*fx[0]),'currency':'EUR'})
            current=rate(p['currency'],today.isoformat()) if p['value'] is not None and Decimal(p['value'])!=0 else (Decimal(1),today.isoformat())
            if current is None:missing.append(today.isoformat())
            if missing:
                excluded.append({**{field:p[field] for field in ('symbol','exchange','currency','account_id','name','account_name')},'reason':'Geen opgeslagen wisselkoers','dates':sorted(set(missing))});continue
            source_points=p['history'] if include_history else [{**p['history'][-1],'day':today.isoformat()}]
            if sparse_history:
                basis={point['day']:daily_values(converted,[],[],date.fromisoformat(point['day']),summary_only=True)[-1] for point in source_points}
            else:basis={point['day']:point for point in daily_values(converted,[],[],today,summary_only=not include_history)}
            history=[]
            for point in source_points:
                if point['day'] not in basis:continue
                cost=basis[point['day']]
                fx=rate(p['currency'],point['day']);value=Decimal(point['value'])*fx[0] if point['value'] is not None and fx else (Decimal(0) if point['value'] is not None and Decimal(point['value'])==0 else None)
                history.append({**point,'cost':cost['cost'],'realised':cost['realised'],'invested':cost['invested'],'value':str(value) if value is not None else None,'price':str(Decimal(point['price'])*fx[0]) if point['price'] is not None and fx else None})
            with_dividends(history,converted_income);last=history[-1];value=Decimal(p['value'])*current[0] if p['value'] is not None else None;cost=Decimal(last['cost']);realised=Decimal(last['realised']);received=Decimal(last['dividend'])
            positions.append({**p,'native_currency':p['currency'],'currency':'EUR','fx_day':current[1],'cost':str(cost),'value':str(value) if value is not None else None,'dividend':str(received),'realised':str(realised),'gain':str(value-cost+realised) if value is not None else None,'total_gain':str(value-cost+realised+received) if value is not None else None,'history':history})
        except (ArithmeticError,ValueError,TypeError,KeyError,IndexError):
            if not skip_invalid:raise
            excluded.append({**{field:p.get(field,'') for field in ('symbol','exchange','currency','account_id','name','account_name')},'reason':'Ontbrekende of ongeldige positiegegevens','dates':[]})
    maps=[{point['day']:point for point in p['history']} for p in positions];history=[]
    for day in sorted({day for rows in maps for day in rows}):
        active=[rows[day] for rows in maps if day in rows];known=[point for point in active if point['value'] is not None];value=sum((Decimal(p['value']) for p in known),Decimal(0)) if known else None
        history.append(dict(day=day,value=str(value) if value is not None else None,cost=str(sum((Decimal(p['cost']) for p in active),Decimal(0))),dividend=str(sum((Decimal(p['dividend']) for p in active),Decimal(0))),with_dividends=str(sum((Decimal(p['with_dividends']) for p in known),Decimal(0))) if known else None,total_gain=str(sum((Decimal(p['total_gain']) for p in known),Decimal(0))) if known else None,price=None,carried=any(p['carried'] for p in active),missing=len(active)-len(known)))
    return dict(account_id=str(account),as_of=today.isoformat(),positions=positions,portfolios=[dict(name='Alle valuta’s in euro',currency='EUR',history=history)],excluded=excluded,fx_dates=[dict(currency=c,requested_on=d,rate_on=r) for c,d,r in sorted(used)])

def prepare_portfolio_rates(store,snapshot,account='all'):
    # Validate scope before requesting any external rates.
    if str(account)!='all' and not any(str(a['id'])==str(account) for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    owner=None if str(account)=='all' else int(account);requests=[];today=date.today().isoformat()
    for rows,field in [(snapshot['purchases'],'purchased_on'),(snapshot['dividends'],'paid_on'),(snapshot.get('charges',[]),'paid_on')]:
        requests.extend((row['currency'],'EUR',row[field]) for row in rows if (owner is None or row['account_id']==owner) and row['currency']!='EUR' and not row.get('split_before'))
    requests.extend((p['currency'],'EUR',today) for p in snapshot['positions'] if (owner is None or p['account_id']==owner) and p['currency']!='EUR' and Decimal(p['quantity'])>0)
    try:prepare_rates(store,requests)
    except Exception as error:record(store,'WARNING','fx','home_euro_rates_failed','Wisselkoersen voor het totaaloverzicht konden niet volledig worden opgehaald.',{'error_type':type(error).__name__,'requested_pairs':len(set((a,b) for a,b,d in requests))})

def overview(store,snapshot,account='all',fetch_rates=True):
    if str(account)!='all' and not any(str(a['id'])==str(account) for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    if fetch_rates:prepare_portfolio_rates(store,snapshot,account)
    with store.read() as db:rates=[dict(row) for row in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR'")]
    return build(snapshot,rates,account)
