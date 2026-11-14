"""Verified corporate actions for which broker export rows can be reconciled."""
import json
from decimal import Decimal, InvalidOperation

from storage import now, positive


def cvr_settlements(rows, provider):
    if provider != 'trading212':
        return {}
    # OCC memo 57447: each ESSA share became cash plus one non-transferable CVR.
    # Trading 212 posted both legs on October 16, a week after the effective date.
    candidates = [row for row in rows if row.get('day') == '2025-10-16'
                  and row.get('currency') == 'USD' and row.get('decision') in (None, 'retry')]
    sales = [row for row in candidates if row.get('kind') == 'SELL'
             and row['ticker'].upper() == 'EPIX' and not row.get('error')
             and row['raw'].get('ISIN', '').upper() in ('', 'CA29668H7085')]
    rights = [row for row in candidates if row.get('kind') == 'DISTRIBUTION'
              and row['ticker'].upper() == 'EPIX.CVR']
    if len(sales) != 1 or len(rights) != 1:
        return {}
    sale, right = sales[0], rights[0]
    try:
        quantity = Decimal(right['quantity'])
        cash = Decimal(sale['raw']['Total'])
        matches = (quantity.is_finite() and quantity > 0
                   and quantity == Decimal(sale['quantity'])
                   and cash.is_finite() and cash > 0
                   and Decimal(right['raw']['Total']) == 0
                   and sale['raw'].get('Currency (Total)') == 'USD'
                   and right['raw'].get('Currency (Total)') == 'USD')
    except (KeyError, InvalidOperation, TypeError):
        return {}
    return {right['line']: sale} if matches else {}


def book_cvr(db, batch, right, sale):
    prior = db.execute(
        'SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',
        (batch['account_id'], batch['provider'], sale['external_id']),
    ).fetchone()
    # Ignored rows also have source records, so require an actual booked sale.
    booked = db.execute(
        "SELECT 1 FROM purchases WHERE account_id=? AND symbol='EPIX' AND exchange='NASDAQ' "
        "AND currency='USD' AND side='SELL' AND trade_time=? AND quantity=? AND price=?",
        (batch['account_id'], sale['trade_time'], positive(sale['quantity']), positive(sale['price'])),
    ).fetchone()
    if not prior or prior[0] != sale['digest'] or not booked:
        raise ValueError('De gekoppelde EPIX-afwikkeling is nog niet geboekt.')
    db.execute(
        'INSERT INTO corporate_action_rights(batch_id,account_id,provider,external_id,'
        'source_external_id,ticker,quantity,currency,received_on,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
        (batch['id'], batch['account_id'], batch['provider'], right['external_id'],
         sale['external_id'], right['ticker'], positive(right['quantity']), right['currency'], right['day'], now()),
    )
    db.execute(
        'INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',
        (batch['id'], batch['account_id'], batch['provider'], right['external_id'],
         right['digest'], json.dumps(right['raw'])),
    )
