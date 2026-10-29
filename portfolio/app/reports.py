"""Read-only report history from saved portfolio data; no provider requests."""
from decimal import Decimal, InvalidOperation


def history(snapshot, account='all', instrument=None, currency=''):
    owner = None if account == 'all' else int(account)
    if owner is not None and not any(a['id'] == owner for a in snapshot['accounts']):
        raise ValueError('Brokeraccount niet gevonden.')
    if instrument is not None and (not isinstance(instrument, list) or len(instrument) != 3
                                   or any(not isinstance(v, str) for v in instrument)):
        raise ValueError('Ongeldige positie.')
    groups = {}
    for position in snapshot['positions']:
        if owner is not None and position['account_id'] != owner:
            continue
        if currency and position['currency'] != currency:
            continue
        if instrument is not None and [position[k] for k in ('symbol', 'exchange', 'currency')] != instrument:
            continue
        days = groups.setdefault(position['currency'], {})
        for point in position['history']:
            day = days.setdefault(point['day'], dict(value=Decimal(0), cost=Decimal(0),
                                                     dividend=Decimal(0), count=0, skipped=0))
            try:
                amounts = [Decimal(point[k]) for k in ('value', 'cost', 'dividend')]
                if not all(v.is_finite() for v in amounts):
                    raise InvalidOperation
            except (InvalidOperation, TypeError, KeyError, ValueError):
                day['skipped'] += 1
                continue
            for key, value in zip(('value', 'cost', 'dividend'), amounts):
                day[key] += value
            day['count'] += 1
    return dict(data_revision=snapshot.get('data_revision'), currencies=[
        dict(currency=code, as_of=max(days, default=''), history=[dict(day=date, **{
            key: str(value) if isinstance(value, Decimal) else value for key, value in point.items()
        }) for date, point in sorted(days.items()) if point['count']],
             omitted_days=sum(not point['count'] for point in days.values()),
             omitted_dates=[day for day, point in sorted(days.items()) if not point['count']])
        for code, days in sorted(groups.items())
    ])


def combined(store, snapshot, account='all', instrument=None, currency='', include_history=False, today=None):
    """Convert report inputs using saved, dated FX; never fetch providers here."""
    from bisect import bisect_right
    from datetime import date
    from home_euro import build
    from forex import unit
    today = today or date.today()
    owner = None if str(account) == 'all' else int(account)
    if owner is not None and not any(a['id'] == owner for a in snapshot['accounts']):
        raise ValueError('Brokeraccount niet gevonden.')
    if instrument is not None and (not isinstance(instrument, list) or len(instrument) != 3
                                  or any(not isinstance(v, str) for v in instrument)):
        raise ValueError('Ongeldige positie.')
    def matches(row):
        return (owner is None or row['account_id'] == owner) and (not currency or row['currency'] == currency) and (instrument is None or [row[k] for k in ('symbol','exchange','currency')] == instrument)
    scoped = {**snapshot, **{key: [row for row in snapshot[key] if matches(row)] for key in ('positions','purchases','dividends')}}
    with store.read() as db:
        rates = [dict(row) for row in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR' ORDER BY day")]
    valid_rates=[]
    for row in rates:
        try:
            date.fromisoformat(row['day']);number=Decimal(row['rate'])
            if number.is_finite() and number>0:valid_rates.append(row)
        except (ArithmeticError,ValueError,TypeError,KeyError):continue
    rates=valid_rates
    euro = build(scoped, rates, account, today, include_history=include_history, skip_invalid=True)
    indexed = {}
    for row in rates:
        indexed.setdefault(row['quote'], []).append(row)
    days = {code: [row['day'] for row in rows] for code, rows in indexed.items()}
    dividends = []; missing = []; used = list(euro['fx_dates'])
    for row in scoped['dividends']:
        try:
            parsed=date.fromisoformat(row['paid_on'])
            if not Decimal(row['amount']).is_finite():raise ValueError()
            if row['paid_on'] > today.isoformat():
                continue
            base, scale = unit(row['currency']); factor = scale; rate_day = row['paid_on']
            if base != 'EUR':
                index = bisect_right(days.get(base, []), row['paid_on']) - 1
                if index < 0 or (date.fromisoformat(row['paid_on']) - date.fromisoformat(indexed[base][index]['day'])).days > 7:
                    missing.append(dict(symbol=row['symbol'], currency=row['currency'], day=row['paid_on'])); continue
                fx = indexed[base][index]; factor /= Decimal(fx['rate']); rate_day = fx['day']
            dividends.append({**row, 'native_currency':row['currency'], 'currency':'EUR', 'source_amount':row['amount'], 'amount':str(Decimal(row['amount']) * factor), 'fx_day':rate_day})
            used.append(dict(currency=row['currency'], requested_on=row['paid_on'], rate_on=rate_day))
        except (ArithmeticError,ValueError,TypeError,KeyError):
            missing.append(dict(symbol=row.get('symbol',''),currency=row.get('currency',''),day=row.get('paid_on',''),reason='Ontbrekende of ongeldige dividendgegevens'))
    result = dict(data_revision=snapshot.get('data_revision'), as_of=today.isoformat(), positions=[{**p, 'history':[]} for p in euro['positions']], dividends=dividends,
                  excluded=euro['excluded'], missing_dividends=missing, fx_dates=used)
    if include_history:
        converted = history({**scoped, 'positions':euro['positions']}, account)
        result['history'] = converted['currencies'][0] if converted['currencies'] else None
    return result
