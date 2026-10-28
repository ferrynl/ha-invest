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
