"""A combined EUR view with dated cash flows and explicit missing FX."""
from bisect import bisect_right
from datetime import date
from decimal import Decimal
from forex import unit,prepare_rates
from history import daily_values,with_dividends
from diagnostics import record
from functools import lru_cache

def identity(row):return tuple(row[k] for k in ('account_id','symbol','exchange','currency'))
def build(snapshot,rates,account='all',today=None,include_history=True,skip_invalid=False,sparse_history=False,retain_history=True,positions=None,allow_missing_value=False):
    today=today or date.today();owner=None
    if str(account)!='all':
        try:owner=int(account)
        except (ValueError,TypeError):raise ValueError('Ongeldig brokeraccount.') from None
        if not any(a['id']==owner for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    indexed={}
    for row in rates:
        if row['base']!='EUR':continue
        if skip_invalid:
            try:
                date.fromisoformat(row['day'])
                value=Decimal(row['rate'])
                if not value.is_finite() or value<=0:continue
            except (ArithmeticError,ValueError,TypeError):
                continue
        indexed.setdefault(row['quote'],[]).append(row)
    for rows in indexed.values():rows.sort(key=lambda row:row['day'])
    position_source=snapshot['positions'] if positions is None else positions
    days={currency:[row['day'] for row in rows] for currency,rows in indexed.items()};used=set();positions=[];excluded=[]
    @lru_cache(maxsize=None)
    def rate(currency,day):
        base,scale=unit(currency)
        if base=='EUR':return scale,day
        i=bisect_right(days.get(base,[]),day)-1
        if i<0:return None
        row=indexed[base][i]
        if (date.fromisoformat(day)-date.fromisoformat(row['day'])).days>7:return None
        used.add((currency,day,row['day']));return scale/Decimal(row['rate']),row['day']
    trades={};income={};totals={};by_currency={}
    for row in snapshot['purchases']:trades.setdefault(identity(row),[]).append(row)
    for row in snapshot['dividends']:income.setdefault(identity(row),[]).append(row)
    for p in position_source:
        if owner is not None and p['account_id']!=owner:continue
        try:
            if skip_invalid:
                for field in ('quantity','cost','value','realised','dividend'):
                    raw=p.get(field)
                    if field=='value' and raw is None and allow_missing_value:continue
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
            if not p['history']:raise ValueError()
            source_points=p['history'] if include_history else [{**p['history'][-1],'day':today.isoformat()}]
            if sparse_history:
                basis={point['day']:daily_values(converted,[],[],date.fromisoformat(point['day']),summary_only=True)[-1] for point in source_points}
            else:basis={point['day']:point for point in daily_values(converted,[],[],today,summary_only=not include_history,history_start=date.fromisoformat(source_points[0]['day']) if include_history and source_points else None)}
            history=[]
            for point in source_points:
                if point['day'] not in basis:continue
                cost=basis[point['day']]
                if skip_invalid and any(point[field] is not None and not Decimal(point[field]).is_finite() for field in ('price','value')):raise ValueError()
                fx=rate(p['currency'],point['day']);value=Decimal(point['value'])*fx[0] if point['value'] is not None and fx else (Decimal(0) if point['value'] is not None and Decimal(point['value'])==0 else None)
                history.append({**point,'cost':cost['cost'],'realised':cost['realised'],'invested':cost['invested'],'value':str(value) if value is not None else None,'price':str(Decimal(point['price'])*fx[0]) if point['price'] is not None and fx else None})
            with_dividends(history,converted_income);last=history[-1];value=Decimal(p['value'])*current[0] if p['value'] is not None else None;cost=Decimal(last['cost']);realised=Decimal(last['realised']);received=Decimal(last['dividend'])
            positions.append({**p,'native_currency':p['currency'],'currency':'EUR','fx_day':current[1],'cost':str(cost),'value':str(value) if value is not None else None,'dividend':str(received),'realised':str(realised),'gain':str(value-cost+realised) if value is not None else None,'total_gain':str(value-cost+realised+received) if value is not None else None,'history':history if retain_history else history[-1:]})
            # Aggregate while processing one position; the compact chart never
            # needs hundreds of full converted position histories in memory.
            for point in history:
                day=point['day']
                for group in (totals,by_currency.setdefault(p['currency'],{})):
                    row=group.setdefault(day,dict(cost=Decimal(0),invested=Decimal(0),dividend=Decimal(0),value=Decimal(0),with_dividends=Decimal(0),total_gain=Decimal(0),return_invested=Decimal(0),active=0,known=0,carried=False))
                    row['active']+=1;row['carried']=row['carried'] or point['carried']
                    for field in ('cost','invested','dividend'):row[field]+=Decimal(point[field])
                    if point['value'] is not None:
                        row['known']+=1
                        for field in ('value','with_dividends','total_gain'):row[field]+=Decimal(point[field])
                        row['return_invested']+=Decimal(point['invested'])
        except (ArithmeticError,ValueError,TypeError,KeyError,IndexError):
            if not skip_invalid:raise
            excluded.append({**{field:p.get(field,'') for field in ('symbol','exchange','currency','account_id','name','account_name')},'reason':'Ontbrekende of ongeldige positiegegevens','dates':[]})
    def aggregate(group):
        history=[]
        for day,row in sorted(group.items()):
            point={field:str(row[field]) for field in ('cost','invested','dividend','return_invested')}
            point.update({field:str(row[field]) if row['known'] else None for field in ('value','with_dividends','total_gain')})
            history.append(dict(point,day=day,return_gain=point['total_gain'],price=None,carried=row['carried'],missing=row['active']-row['known'],count=row['known']))
        return history
    return dict(account_id=str(account),as_of=today.isoformat(),positions=positions,portfolios=[dict(name='Alle valuta’s in euro',currency='EUR',history=aggregate(totals),excluded_count=len(excluded)),*[dict(name=c,native_currency=c,currency='EUR',history=aggregate(group)) for c,group in sorted(by_currency.items())]],excluded=excluded,fx_dates=[dict(currency=c,requested_on=d,rate_on=r) for c,d,r in sorted(used)])

def prepare_portfolio_rates(store,snapshot,account='all'):
    # Validate scope before requesting any external rates.
    if str(account)!='all' and not any(str(a['id'])==str(account) for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    owner=None if str(account)=='all' else int(account);requests=[];today=date.today().isoformat()
    for rows,field in [(snapshot['purchases'],'purchased_on'),(snapshot['dividends'],'paid_on'),(snapshot.get('charges',[]),'paid_on')]:
        requests.extend((row['currency'],'EUR',row[field]) for row in rows if (owner is None or row['account_id']==owner) and row['currency']!='EUR' and not row.get('split_before'))
    requests.extend((p['currency'],'EUR',today) for p in snapshot['positions'] if (owner is None or p['account_id']==owner) and p['currency']!='EUR' and Decimal(p['quantity'] or '0')>0)
    try:prepare_rates(store,requests)
    except Exception as error:record(store,'WARNING','fx','home_euro_rates_failed','Wisselkoersen voor het totaaloverzicht konden niet volledig worden opgehaald.',{'error_type':type(error).__name__,'requested_pairs':len(set((a,b) for a,b,d in requests))})

def overview(store,snapshot,account='all',fetch_rates=True,include_history=True,retain_history=True,skip_invalid=False,positions=None,expected_revision=None,allow_missing_value=False):
    if str(account)!='all' and not any(str(a['id'])==str(account) for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    if fetch_rates:prepare_portfolio_rates(store,snapshot,account)
    with store.read() as db:
        db.execute('BEGIN')
        if expected_revision is not None and db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]!=expected_revision:
            from storage import PortfolioRevisionChanged
            raise PortfolioRevisionChanged('De portefeuille is gewijzigd. Vernieuw het overzicht.')
        rates=[dict(row) for row in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR'")]
    return build(snapshot,rates,account,include_history=include_history,retain_history=retain_history,skip_invalid=skip_invalid,positions=positions,allow_missing_value=allow_missing_value)


def compact_overview(store,snapshot,account='all'):
    from dashboard import compact
    from storage import PortfolioRevisionChanged
    try:
        result=overview(store,snapshot,account,fetch_rates=False,include_history=False,
                        skip_invalid=True,allow_missing_value=True,expected_revision=snapshot['data_revision'])
    except PortfolioRevisionChanged:
        # Read positions and FX in one transaction if quotes are being refreshed.
        snapshot,rates=store.compact_state_with_euro_rates(account)
        result=build(snapshot,rates,account,include_history=False,skip_invalid=True,allow_missing_value=True)
    return compact({**result,'data_revision':snapshot['data_revision'],'chart_status':'pending'})
