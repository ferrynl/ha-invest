"""Small initial responses and on-demand history for at most six positions."""
from datetime import date, timedelta
from decimal import Decimal
from itertools import islice
import json

MOVER_PERIODS = {1, 7, 30, 90, 365}


def price_change(price, baseline):
    try:
        current, previous = Decimal(price), Decimal(baseline)
        if current.is_finite() and previous.is_finite() and current > 0 and previous > 0:
            return (current / previous - 1) * 100
    except (ArithmeticError, ValueError, TypeError):
        pass
    return None


def daily_moves(db, listing, quote, prices):
    if listing[1] == 'PRIVATE' or (quote and quote.get('manual')):
        return None
    latest_close = prices[-1] if prices else None
    quote_day = quote['quoted_at'][:10] if quote else ''
    if latest_close and latest_close['day'] > quote_day:
        day, price = latest_close['day'], latest_close['price']
    elif quote:
        day, price = quote_day, quote['price']
    else:
        return None
    earlier = (row for row in reversed(prices) if row['day'] < day)
    sessions = [{'day': day, 'price': price}, *islice(earlier, 2)]
    moves = []
    for current, previous in zip(sessions, sessions[1:]):
        try:
            date.fromisoformat(current['day'])
            change = price_change(current['price'], previous['price'])
            if change:
                moves.append({'day': current['day'], 'percent': str(change)})
        except (ArithmeticError, ValueError, TypeError):
            continue
    if not moves:
        return None
    domain = ''
    for row in db.execute(
        """SELECT payload FROM api_cache WHERE cache_key=?
           AND namespace IN ('yahoo-company-v2','company-display-v2')
           ORDER BY fetched_at DESC""", ('|'.join(listing),),
    ):
        try:
            domain = json.loads(row[0]).get('domain', '')
        except (ValueError, TypeError, AttributeError):
            continue
        if isinstance(domain, str) and domain:
            break
    return {'sessions': moves, 'domain': domain if isinstance(domain, str) else ''}


def stock_movers(store, snapshot, account, period, today=None):
    from storage import PortfolioRevisionChanged
    if period not in MOVER_PERIODS:
        raise ValueError()
    if account != 'all' and not any(str(row['id']) == account for row in snapshot['accounts']):
        raise ValueError()
    today = today or date.today()
    end = today.isoformat()
    start = (today - timedelta(days=period)).isoformat()
    fields = ('symbol', 'exchange', 'currency')
    seen = set()
    rows = []
    latest_day = ''
    with store.read() as db:
        db.execute('BEGIN')
        if db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0] != snapshot['data_revision']:
            raise PortfolioRevisionChanged()
        for position in snapshot['positions']:
            if account != 'all' and str(position['account_id']) != account:
                continue
            key = tuple(position[field] for field in fields)
            quote = position.get('quote')
            if (key in seen or Decimal(position['quantity'] or '0') <= 0 or key[1] == 'PRIVATE'
                    or position.get('quote_paused') or (quote and quote.get('manual'))):
                continue
            seen.add(key)
            close = db.execute(
                'SELECT day,price FROM daily_prices WHERE symbol=? AND exchange=? AND currency=? AND day<=? ORDER BY day DESC LIMIT 1',
                (*key, end),
            ).fetchone()
            quote_day = quote['quoted_at'][:10] if quote else ''
            if quote and (close['day'] if close else '') <= quote_day <= end:
                day, price = quote_day, quote['price']
            elif close:
                day, price = close['day'], close['price']
            else:
                continue
            latest_day = max(latest_day, day)
            if period != 1 and day <= start:
                continue
            cutoff = (date.fromisoformat(day) - timedelta(days=1)).isoformat() if period == 1 else start
            previous = db.execute(
                'SELECT price FROM daily_prices WHERE symbol=? AND exchange=? AND currency=? AND day<=? ORDER BY day DESC LIMIT 1',
                (*key, cutoff),
            ).fetchone()
            change = price_change(price, previous['price']) if previous else None
            if change:
                listing = {field: position[field] for field in (*fields, 'name')}
                listing['logo_domain'] = (position.get('daily_moves') or {}).get('domain', '')
                rows.append((change, day, listing))
    if period == 1:
        rows = [row for row in rows if row[1] == latest_day]
    rows.sort(key=lambda row: row[0])
    def ranked(items):
        return [dict(listing, change=str(change), day=day) for change, day, listing in items[:10]]
    return {
        'day': latest_day if period == 1 else None,
        'gainers': ranked([row for row in reversed(rows) if row[0] > 0]),
        'losers': ranked([row for row in rows if row[0] < 0]),
    }


def compact(snapshot):
    return {**snapshot,**({'quotes':[]} if 'quotes' in snapshot else {}),'compact':True,'positions':[{**p,'history':p['history'][-1:],'history_loaded':False} for p in snapshot['positions']]}

def histories(snapshot,account,selections):
    if not isinstance(selections,list) or not 1<=len(selections)<=6:raise ValueError('Selecteer maximaal zes posities.')
    owner=None if account=='all' else int(account)
    if owner is not None and not any(a['id']==owner for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    available={(p['account_id'],p['symbol'],p['exchange'],p.get('native_currency',p['currency'])):p for p in snapshot['positions'] if owner is None or p['account_id']==owner}
    result=[]
    for selection in selections:
        if not isinstance(selection,dict):raise ValueError('Ongeldige positie.')
        key=tuple(selection[k] for k in ('account_id','symbol','exchange','currency'))
        if key not in available:raise ValueError('Positie niet gevonden in dit brokeraccount.')
        result.append({**selection,'history':available[key]['history']})
    return {'histories':result,'data_revision':snapshot.get('data_revision')}
