"""Investment performance, with explicit gaps and dated investment cash flows."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from bisect import bisect_right
import math
from home_euro import build
from forex import unit
from transactions import scope

ZERO=Decimal(0)

def annual_points(points):
    """Keep each year's last saved day, including the current incomplete year."""
    annual={}
    for point in points:
        year=point['day'][:4]
        if year not in annual or point['day']>annual[year]['day']:annual[year]=point
    return [annual[year] for year in sorted(annual)]

def xirr(flows):
    """365-day XIRR; decline ambiguous cash-flow schedules instead of guessing."""
    totals=defaultdict(lambda:ZERO)
    for day,amount in flows:totals[day]+=Decimal(amount)
    ordered=sorted((date.fromisoformat(day),amount) for day,amount in totals.items() if amount)
    if len(ordered)<2 or ordered[0][0]==ordered[-1][0]:return None
    if not any(a>0 for _,a in ordered) or not any(a<0 for _,a in ordered):return None
    first=ordered[0][0];scale=max(abs(float(a)) for _,a in ordered)
    values=[((day-first).days/365,float(amount)/scale) for day,amount in ordered]
    def npv(log_rate):
        exponents=[-log_rate*t for t,_ in values];offset=max(exponents)
        return math.fsum(amount*math.exp(power-offset) for (_,amount),power in zip(values,exponents))
    roots=[];left=-20.0;low=npv(left)
    for index in range(1,401):
        right=-20+index/10;high=npv(right)
        if low==0:roots.append(left)
        if low*high<0:
            a,b,fa=left,right,low
            for _ in range(100):
                mid=(a+b)/2;value=npv(mid)
                if (value>0)==(fa>0):a=mid;fa=value
                else:b=mid
            roots.append((a+b)/2)
        left,low=right,high
    if low==0:roots.append(left)
    unique=[]
    for root in roots:
        if not unique or abs(root-unique[-1])>1e-8:unique.append(root)
    return str(math.expm1(unique[0])*100) if len(unique)==1 else None

def summarize(positions,trades,dividends,today,missing=0):
    histories={};current=defaultdict(lambda:ZERO);complete=bool(positions);years={}
    for p in positions:
        points=p['history']
        if not points:complete=False;continue
        for point in points:histories.setdefault(point['day'],[]).append(point)
        last=points[-1]
        for field in ('cost','realised','invested'):
            current[field]+=Decimal(last[field])
        if p['value'] is None:complete=False
        else:current['value']+=Decimal(p['value'])
    current['dividend']=sum((Decimal(d['amount']) for d in dividends),ZERO)
    complete=complete and not missing
    profit=current['value']-current['cost']+current['realised']+current['dividend'] if complete else None
    previous=ZERO
    for day,points in sorted(histories.items()):
        valid=all(point['value'] is not None for point in points) and not missing
        gain=sum((Decimal(p['value'])-Decimal(p['cost'])+Decimal(p['realised']) for p in points),ZERO) if valid else None
        income=sum((Decimal(d['amount']) for d in dividends if d['paid_on']<=day),ZERO)
        years[day[:4]]=dict(year=day[:4],day=day,cumulative=gain+income if gain is not None else None)
    annual=[]
    for year,row in sorted(years.items()):
        value=row['cumulative']-previous if row['cumulative'] is not None and previous is not None else None
        spent=sum((Decimal(t['quantity'])*Decimal(t['price']) for t in trades if t['side']=='BUY' and not t.get('split_before') and not t.get('transfer_id') and t['purchased_on'].startswith(year)),ZERO)
        annual.append(dict(year=year,day=row['day'],gain=str(value) if value is not None else None,invested=str(spent)))
        previous=row['cumulative']
    flows=[];transfers=defaultdict(list)
    for t in trades:
        if t.get('transfer_id'):transfers[t['transfer_id']].append(t);continue
        if t.get('split_before'):continue
        amount=Decimal(t['quantity'])*Decimal(t['price'])
        flows.append((t['purchased_on'],amount if t['side']=='SELL' else -amount))
    flows.extend((d['paid_on'],d['amount']) for d in dividends)
    flows.append((today.isoformat(),current['value']))
    rate=xirr(flows) if complete and all(len(pair)==2 for pair in transfers.values()) else None
    def percent(value):return str(value/current['invested']*100) if value is not None and current['invested']>0 else None
    gain=current['value']-current['cost'] if complete else None
    return dict(complete=complete,count=len(positions),omitted=missing,invested=str(current['invested']),value=str(current['value']) if complete else None,
                price_gain=str(gain) if gain is not None else None,price_percent=percent(gain),dividend=str(current['dividend']),dividend_percent=percent(current['dividend']),
                realised=str(current['realised']),realised_percent=percent(current['realised']),total=str(profit) if profit is not None else None,total_percent=percent(profit),
                irr=rate,twr=None,costs=None,taxes=None,years=annual)

def overview(store,snapshot,account='all',instrument=None,currency='',today=None):
    today=today or date.today()
    with store.read() as db:
        owner=scope(db,account)
        rates=[dict(r) for r in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR' ORDER BY day")]
    if instrument is not None and (not isinstance(instrument,list) or len(instrument)!=3 or any(not isinstance(v,str) for v in instrument)):raise ValueError('Ongeldige positie.')
    def matches(r):return (owner is None or r['account_id']==owner) and (not currency or r['currency']==currency) and (instrument is None or [r[k] for k in ('symbol','exchange','currency')]==instrument)
    selected={**snapshot,**{k:[r for r in snapshot[k] if matches(r)] for k in ('positions','purchases','dividends')}}
    # The report needs year boundaries and today's totals, not a second daily
    # portfolio simulation. Keep stored historical observations at those dates.
    selected['positions']=[{**p,'history':annual_points(p['history'])} for p in selected['positions']]
    valid_rates=[]
    for r in rates:
        try:
            if Decimal(r['rate']).is_finite() and Decimal(r['rate'])>0:date.fromisoformat(r['day']);valid_rates.append(r)
        except (ArithmeticError,ValueError,TypeError):continue
    euro=build(selected,valid_rates,account,today,include_history=True,skip_invalid=True,sparse_history=True)
    indexed=defaultdict(list)
    for r in valid_rates:indexed[r['quote']].append(r)
    dates={c:[r['day'] for r in rows] for c,rows in indexed.items()}
    def factor(code,day):
        base,scale=unit(code)
        if base=='EUR':return scale
        i=bisect_right(dates.get(base,[]),day)-1
        if i<0 or (date.fromisoformat(day)-date.fromisoformat(dates[base][i])).days>7:return None
        return scale/Decimal(indexed[base][i]['rate'])
    converted_trades=[];converted_income=[];missing=len(euro['excluded'])
    for t in selected['purchases']:
        fx=Decimal(1) if t.get('split_before') else factor(t['currency'],t['purchased_on'])
        if fx is None:missing+=1;continue
        converted_trades.append({**t,'price':str(Decimal(t['price'])*fx),'currency':'EUR'})
    for d in selected['dividends']:
        fx=factor(d['currency'],d['paid_on'])
        if fx is None:missing+=1;continue
        converted_income.append({**d,'amount':str(Decimal(d['amount'])*fx),'currency':'EUR'})
    groups=[dict(currency='EUR',combined=True,**summarize(euro['positions'],converted_trades,converted_income,today,missing))]
    for code in sorted({p['currency'] for p in selected['positions']}|{d['currency'] for d in selected['dividends']}):
        groups.append(dict(currency=code,combined=False,**summarize([p for p in selected['positions'] if p['currency']==code],[t for t in selected['purchases'] if t['currency']==code],[d for d in selected['dividends'] if d['currency']==code],today)))
    return dict(data_revision=snapshot.get('data_revision'),as_of=today.isoformat(),groups=groups)
