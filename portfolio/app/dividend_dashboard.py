"""Received income and a transparent, constant-dividend historical scenario."""
from calendar import monthrange
from datetime import date
from decimal import Decimal

ZERO=Decimal(0)
def month_offset(day,offset):
    n=day.year*12+day.month-1+offset
    return date(n//12,n%12+1,1)
def key(row):return tuple((row.get('native_currency',row[k]) if k=='currency' else row[k]) for k in ('account_id','symbol','exchange','currency'))

def overview(snapshot,account='all',today=None,force_currency=None):
    today=today or date.today()
    if str(account)!='all':
        try:owner=int(account)
        except (TypeError,ValueError):raise ValueError('Ongeldig brokeraccount.') from None
        if not any(a['id']==owner for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    else:owner=None
    positions=[p for p in snapshot['positions'] if owner is None or p['account_id']==owner]
    payments=[p for p in snapshot['dividends'] if (owner is None or p['account_id']==owner) and p['paid_on']<=today.isoformat()]
    splits={}
    for trade in snapshot['purchases']:
        if trade['split_before']:splits.setdefault(key(trade),[]).append(trade)
    start=today.replace(year=today.year-1,day=min(today.day,monthrange(today.year-1,today.month)[1])).isoformat()
    earlier=today.replace(year=today.year-2,day=min(today.day,monthrange(today.year-2,today.month)[1])).isoformat()
    names={key(p):p for p in positions};accounts={a['id']:a['name'] for a in snapshot['accounts']}
    currencies=sorted({p['currency'] for p in positions+payments}|({force_currency} if force_currency else set()));result=[]
    for currency in currencies:
        rows=[p for p in payments if p['currency']==currency];members=[p for p in positions if p['currency']==currency];by_month={};contributors={};baseline={m:ZERO for m in range(1,13)};modeled=set();excluded={}
        for p in members:
            contributors[key(p)]={**{field:p[field] for field in ('symbol','exchange','currency','account_id','name','account_name')},**({'native_currency':p['native_currency']} if p.get('native_currency') else {}),'received':ZERO,'expected':ZERO,'open':Decimal(p['quantity'])>0}
        for payment in rows:
            amount=Decimal(payment['amount']);month=payment['paid_on'][:7];by_month[month]=by_month.get(month,ZERO)+amount;identity=key(payment)
            if identity not in contributors:contributors[identity]=dict(symbol=payment['symbol'],exchange=payment['exchange'],currency=currency,account_id=payment['account_id'],name=payment['symbol'],account_name=accounts[payment['account_id']],received=ZERO,expected=ZERO,open=False,**({'native_currency':payment['native_currency']} if payment.get('native_currency') else {}))
            contributors[identity]['received']+=amount
            position=names.get(identity)
            if payment['paid_on']<=start or not position or Decimal(position['quantity'])<=0:continue
            if payment.get('forecast_amount','available') is None:excluded[identity]='Geen actuele wisselkoers voor de verwachting';continue
            point=next((point for point in reversed(position['history']) if point['day']<=payment['paid_on']),None)
            basis=Decimal(point['quantity']) if point else ZERO
            if basis<=0:excluded[identity]='Geen betrouwbaar aantal op de betaaldatum';continue
            factor=Decimal(1);valid=True
            for trade in splits.get(identity,[]):
                if trade['purchased_on']<=payment['paid_on'] or trade['purchased_on']>today.isoformat():continue
                before=Decimal(trade['split_before'])
                if before<=0:valid=False;break
                factor*=Decimal(trade['quantity'])/before
            if not valid:excluded[identity]='Splitsing zonder bekend oorspronkelijk aantal';continue
            estimate=Decimal(payment.get('forecast_amount',payment['amount']))/basis/factor*Decimal(position['quantity'])
            baseline[int(payment['paid_on'][5:7])]+=estimate;contributors[identity]['expected']+=estimate;modeled.add(identity)
        for p in members:
            if Decimal(p['quantity'])>0 and key(p) not in modeled and key(p) not in excluded:excluded[key(p)]='Geen bruikbaar dividend in de afgelopen twaalf maanden'
        forecast=[dict(month=month_offset(today,i).strftime('%Y-%m'),amount=str(baseline[month_offset(today,i).month])) for i in range(1,61)]
        first=min(by_month,default=today.strftime('%Y-%m'));first_year=int(first[:4]);yearly=[]
        for year in range(first_year,today.year+6):
            received=sum((amount for month,amount in by_month.items() if month.startswith(str(year)+'-')),ZERO)
            expected=sum((Decimal(row['amount']) for row in forecast if row['month'].startswith(str(year)+'-')),ZERO)
            yearly.append(dict(year=year,received=str(received),expected=str(expected),months_expected=sum(row['month'].startswith(str(year)+'-') for row in forecast)))
        total=sum((Decimal(p['amount']) for p in rows),ZERO);ytd=sum((Decimal(p['amount']) for p in rows if p['paid_on'].startswith(str(today.year))),ZERO);trailing=sum((Decimal(p['amount']) for p in rows if p['paid_on']>start),ZERO);previous=sum((Decimal(p['amount']) for p in rows if earlier<p['paid_on']<=start),ZERO)
        latest_months=[month_offset(today,i).strftime('%Y-%m') for i in range(-23,1)]
        for p in contributors.values():p['received']=str(p['received']);p['expected']=str(p['expected'])
        issues=[dict(symbol=identity[1],exchange=identity[2],currency=identity[3],account_id=identity[0],name=names[identity]['name'],account_name=names[identity]['account_name'],reason=reason) for identity,reason in excluded.items()]
        result.append(dict(currency=currency,total=str(total),ytd=str(ytd),trailing12=str(trailing),previous12=str(previous),next12=str(sum(baseline.values(),ZERO)),monthly_average=str(sum(baseline.values(),ZERO)/12),payments=len(rows),first_month=first,monthly=[dict(month=m,amount=str(by_month.get(m,ZERO))) for m in latest_months],months=[dict(month=m,amount=str(a)) for m,a in sorted(by_month.items())],yearly=yearly,forecast=forecast,contributors=sorted(contributors.values(),key=lambda p:Decimal(p['received']),reverse=True),coverage=dict(modeled=len(modeled),open=sum(Decimal(p['quantity'])>0 for p in members),excluded=issues)))
    return dict(account_id=str(account),as_of=today.isoformat(),currencies=result,method='historical_same_month_current_holdings')


def euro_overview(store,snapshot,account='all',today=None):
    from bisect import bisect_right
    from forex import unit,prepare_rates
    from diagnostics import record
    today=today or date.today();native=overview(snapshot,account,today);owner=None if str(account)=='all' else int(account)
    payments=[row for row in snapshot['dividends'] if (owner is None or row['account_id']==owner) and row['paid_on']<=today.isoformat()]
    payment_currencies={row['currency'] for row in payments}
    requests=[(row['currency'],'EUR',row['paid_on']) for row in payments]+[(p['currency'],'EUR',today.isoformat()) for p in snapshot['positions'] if (owner is None or p['account_id']==owner) and Decimal(p['quantity'])>0 and p['currency'] in payment_currencies]
    try:prepare_rates(store,requests)
    except Exception as error:record(store,'WARNING','fx','dividend_euro_rates_failed','Wisselkoersen voor dividend konden niet volledig worden opgehaald.',{'error_type':type(error).__name__})
    with store.connect() as db:rows=[dict(row) for row in db.execute("SELECT quote,day,rate FROM fx_rates WHERE base='EUR' ORDER BY day")]
    rates={}
    for row in rows:rates.setdefault(row['quote'],[]).append(row)
    days={c:[row['day'] for row in values] for c,values in rates.items()};used=set()
    def factor(currency,day):
        base,scale=unit(currency)
        if base=='EUR':return scale
        index=bisect_right(days.get(base,[]),day)-1
        if index<0:return None
        row=rates[base][index]
        if (date.fromisoformat(day)-date.fromisoformat(row['day'])).days>7:return None
        used.add(row['day']);return scale/Decimal(row['rate'])
    converted=[];missing=[]
    for payment in payments:
        fx=factor(payment['currency'],payment['paid_on']);current=factor(payment['currency'],today.isoformat())
        if fx is None:missing.append(dict(symbol=payment['symbol'],exchange=payment['exchange'],currency=payment['currency'],account_id=payment['account_id'],day=payment['paid_on'],reason='Wisselkoers op betaaldatum ontbreekt'));continue
        converted.append({**payment,'native_currency':payment['currency'],'source_amount':payment['amount'],'currency':'EUR','amount':str(Decimal(payment['amount'])*fx),'forecast_amount':str(Decimal(payment['amount'])*current) if current is not None else None})
    positions=[{**p,'native_currency':p['currency'],'currency':'EUR'} for p in snapshot['positions']]
    result=overview({**snapshot,'positions':positions,'dividends':converted},account,today,force_currency='EUR')
    combined=result['currencies'][0] if result['currencies'] else None
    if combined is not None:combined.update(ledger=converted,missing_payments=missing,fx_as_of=max(used) if used else today.isoformat())
    return {**native,'combined':combined}
