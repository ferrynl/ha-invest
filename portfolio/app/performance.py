"""Investment performance, with explicit gaps and dated investment cash flows."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from bisect import bisect_right
import math
from home_euro import build, identity
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

def summarize(positions,trades,dividends,today,missing=0,charges=()):
    current=defaultdict(lambda:ZERO)
    annual_positions=defaultdict(list)
    for p in positions:
        points=annual_points(p['history'])
        for field in ('cost','realised','invested'):
            current[field]+=Decimal(points[-1][field])
        current['value']+=Decimal(p['value'])
        previous=None
        for index,point in enumerate(points):
            cumulative=(Decimal(point['value'])-Decimal(point['cost'])+Decimal(point['realised'])
                        if point['value'] is not None else None)
            day=point['day']
            comparable=cumulative is not None and (index==0 or previous is not None)
            annual_positions[day[:4]].append((day,cumulative-(previous or ZERO) if comparable else None))
            previous=cumulative
    current['dividend']=sum((Decimal(d['amount']) for d in dividends),ZERO)
    available=bool(positions or dividends or charges)
    complete=available and not missing
    from charges import FEES
    additional=sum((Decimal(c['amount']) for c in charges if not c['included_in_net']),ZERO)
    profit=current['value']-current['cost']+current['realised']+current['dividend']-additional if available else None
    annual=[]
    for year,rows in sorted(annual_positions.items()):
        day=max(day for day,_ in rows)
        known=[gain for _,gain in rows if gain is not None]
        # Cash income remains a known component even where some historical prices are missing.
        income=sum((Decimal(d['amount']) for d in dividends if d['paid_on'][:4]==year and d['paid_on']<=day),ZERO)
        fees=sum((Decimal(c['amount']) for c in charges if not c['included_in_net'] and c['paid_on'][:4]==year and c['paid_on']<=day),ZERO)
        value=sum(known,ZERO)+income-fees if known else None
        spent=sum((Decimal(t['quantity'])*Decimal(t['price']) for t in trades if t['side']=='BUY' and not t.get('split_before') and not t.get('transfer_id') and t['purchased_on'].startswith(year)),ZERO)
        annual.append(dict(year=year,day=day,gain=str(value) if value is not None else None,invested=str(spent)))
    flows=[];transfers=defaultdict(list)
    for t in trades:
        if t.get('transfer_id'):transfers[t['transfer_id']].append(t);continue
        if t.get('split_before'):continue
        amount=Decimal(t['quantity'])*Decimal(t['price'])
        flows.append((t['purchased_on'],amount if t['side']=='SELL' else -amount))
    flows.extend((d['paid_on'],d['amount']) for d in dividends)
    flows.extend((c['paid_on'],-Decimal(c['amount'])) for c in charges if not c['included_in_net'])
    flows.append((today.isoformat(),current['value']))
    rate=xirr(flows) if available and all(len(pair)==2 for pair in transfers.values()) else None
    def percent(value):return str(value/current['invested']*100) if value is not None and current['invested']>0 else None
    gain=current['value']-current['cost'] if available else None
    return dict(complete=complete,count=len(positions),omitted=missing,invested=str(current['invested']),value=str(current['value']) if available else None,
                price_gain=str(gain) if gain is not None else None,price_percent=percent(gain),dividend=str(current['dividend']),dividend_percent=percent(current['dividend']),
                realised=str(current['realised']),realised_percent=percent(current['realised']),total=str(profit) if profit is not None else None,total_percent=percent(profit),
                irr=rate,twr=None,costs=str(sum((Decimal(c['amount']) for c in charges if c['category'] in FEES),ZERO)) if any(c['category'] in FEES for c in charges) else None,taxes=str(sum((Decimal(c['amount']) for c in charges if c['category'] not in FEES),ZERO)) if any(c['category'] not in FEES for c in charges) else None,
                additional_costs=str(sum((Decimal(c['amount']) for c in charges if c['category'] in FEES and not c['included_in_net']),ZERO)),additional_taxes=str(sum((Decimal(c['amount']) for c in charges if c['category'] not in FEES and not c['included_in_net']),ZERO)),included_charges=str(sum((Decimal(c['amount']) for c in charges if c['included_in_net']),ZERO)),years=annual)

def overview(store,snapshot,account='all',instrument=None,currency='',today=None):
    today=today or date.today()
    with store.read() as db:
        owner=scope(db,account)
        rates=[dict(r) for r in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR' ORDER BY day")]
    if instrument is not None and (not isinstance(instrument,list) or len(instrument)!=3 or any(not isinstance(v,str) for v in instrument)):raise ValueError('Ongeldige positie.')
    def matches(r):return (owner is None or r['account_id']==owner) and (not currency or r['currency']==currency) and (instrument is None or [r[k] for k in ('symbol','exchange','currency')]==instrument)
    selected={**snapshot,**{k:[r for r in snapshot[k] if matches(r)] for k in ('positions','purchases','dividends')}}
    accounts={a['id']:a['name'] for a in snapshot['accounts']}

    def issue(row,kind,reason,days=()):
        return dict(kind=kind,reason=reason,id=row.get('id'),symbol=row.get('symbol'),
                    exchange=row.get('exchange'),currency=row['currency'],
                    account_name=accounts.get(row['account_id']),dates=list(days))

    def finite(row,*fields):
        return all(Decimal(row[field]).is_finite() for field in fields)

    issues=[]
    blocked=set()
    positions=[]
    for p in selected['positions']:
        try:
            history=annual_points(p['history'])
            if not history or not all(finite(point,'cost','realised','invested') and
                                      (point['value'] is None or finite(point,'value')) for point in history):
                raise ValueError()
            if p['value'] is None:
                issues.append(issue(p,'position','quote',[today.isoformat()]))
                blocked.add(identity(p))
                continue
            if not finite(p,'value','quantity','cost','realised','dividend'):
                raise ValueError()
            positions.append({**p,'history':history})
        except (ArithmeticError,ValueError,TypeError,KeyError):
            issues.append(issue(p,'position','position'))
            blocked.add(identity(p))

    def valid_rows(rows,kind,day_field,fields):
        valid=[]
        for row in rows:
            try:
                day=date.fromisoformat(row[day_field])
                if not finite(row,*fields) or (kind=='trade' and Decimal(row['quantity'])<=0):
                    raise ValueError()
                if day<=today:valid.append(row)
            except (ArithmeticError,ValueError,TypeError,KeyError):
                issues.append(issue(row,kind,kind,[row[day_field]] if row.get(day_field) else []))
                if kind=='trade':blocked.add(identity(row))
        return valid

    trades=valid_rows(selected['purchases'],'trade','purchased_on',('quantity','price'))
    dividends=valid_rows(selected['dividends'],'dividend','paid_on',('amount',))
    charges=valid_rows([c for c in snapshot.get('charges',[]) if (owner is None or c['account_id']==owner)
                        and (not currency or c['currency']==currency) and instrument is None],
                       'charge','paid_on',('amount',))
    transfers=defaultdict(set)
    for trade in selected['purchases']:
        if trade.get('transfer_id'):transfers[trade['transfer_id']].add(identity(trade))
    linked=defaultdict(set)
    for pair in transfers.values():
        for key in pair:linked[key].update(pair)
    position_by_key={identity(p):p for p in positions}

    def exclude_linked(excluded,diagnostics):
        queue=list(excluded)
        while queue:
            for key in linked[queue.pop()]-excluded:
                excluded.add(key)
                queue.append(key)
                if key in position_by_key:
                    diagnostics.append(issue(position_by_key[key],'position','transfer'))

    exclude_linked(blocked,issues)
    native={**selected,'positions':[p for p in positions if identity(p) not in blocked],
            'purchases':[t for t in trades if identity(t) not in blocked],
            'dividends':[d for d in dividends if identity(d) not in blocked]}
    valid_rates=[]
    for r in rates:
        try:
            if Decimal(r['rate']).is_finite() and Decimal(r['rate'])>0:date.fromisoformat(r['day']);valid_rates.append(r)
        except (ArithmeticError,ValueError,TypeError):continue
    euro=build(native,valid_rates,account,today,include_history=True,skip_invalid=True,sparse_history=True)
    indexed=defaultdict(list)
    for r in valid_rates:indexed[r['quote']].append(r)
    dates={c:[r['day'] for r in rows] for c,rows in indexed.items()}
    def factor(code,day):
        base,scale=unit(code)
        if base=='EUR':return scale
        i=bisect_right(dates.get(base,[]),day)-1
        if i<0 or (date.fromisoformat(day)-date.fromisoformat(dates[base][i])).days>7:return None
        return scale/Decimal(indexed[base][i]['rate'])
    euro_issues=[]
    euro_blocked=set()
    for row in euro['excluded']:
        euro_blocked.add(identity(row))
        euro_issues.append(issue(row,'position','fx' if row['dates'] else 'position',row['dates']))
    for kind,rows,day_field in (('trade',native['purchases'],'purchased_on'),('dividend',native['dividends'],'paid_on')):
        for row in rows:
            if identity(row) in euro_blocked and not row.get('split_before') and factor(row['currency'],row[day_field]) is None:
                euro_issues.append(issue(row,kind,'fx',[row[day_field]]))
    exclude_linked(euro_blocked,euro_issues)
    euro_positions=[p for p in euro['positions'] if identity({**p,'currency':p['native_currency']}) not in euro_blocked]

    def converted(rows,kind,field,day_field):
        result=[]
        for row in rows:
            if kind!='charge' and identity(row) in euro_blocked:
                continue
            fx=Decimal(1) if row.get('split_before') else factor(row['currency'],row[day_field])
            if fx is None:
                euro_issues.append(issue(row,kind,'fx',[row[day_field]]))
                continue
            result.append({**row,field:str(Decimal(row[field])*fx),'currency':'EUR'})
        return result

    converted_trades=converted(native['purchases'],'trade','price','purchased_on')
    converted_income=converted(native['dividends'],'dividend','amount','paid_on')
    converted_charges=converted(charges,'charge','amount','paid_on')

    def group(code,combined,positions,trades,dividends,charges,diagnostics):
        history_issues=[]
        for p in positions:
            for point in p['history']:
                if point['value'] is None:
                    source={**p,'currency':p.get('native_currency',p['currency'])}
                    reason='historic_fx' if combined and point['day'] in native_valued.get(identity(source),set()) else 'historic_quote'
                    history_issues.append(issue(source,'position',reason,[point['day']]))
        return dict(currency=code,combined=combined,issues=diagnostics+history_issues,
                    **summarize(positions,trades,dividends,today,len(diagnostics),charges))

    native_valued={identity(p):{point['day'] for point in p['history'] if point['value'] is not None}
                   for p in native['positions']}
    groups=[group('EUR',True,euro_positions,converted_trades,converted_income,converted_charges,issues+euro_issues)]
    for code in sorted({r['currency'] for r in selected['positions']+selected['dividends']+charges+issues}):
        groups.append(group(code,False,*([r for r in rows if r['currency']==code] for rows in
                      (native['positions'],native['purchases'],native['dividends'],charges,issues))))
    return dict(data_revision=snapshot.get('data_revision'),as_of=today.isoformat(),groups=groups)
