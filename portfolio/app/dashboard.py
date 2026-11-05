"""Small initial responses and on-demand history for at most six positions."""
from datetime import date
from decimal import Decimal
from itertools import islice
import json


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
            price, close = Decimal(current['price']), Decimal(previous['price'])
            if price.is_finite() and close.is_finite() and price > 0 and close > 0:
                change = (price / close - 1) * 100
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
