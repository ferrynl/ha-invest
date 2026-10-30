"""Daily valuation, preserving unknown prices instead of inventing market data."""
from datetime import date, timedelta
from decimal import Decimal
from diagnostics import ActionError

def daily_values(purchases, daily, quotes, today=None, summary_only=False):
    end = today or date.today()
    start = end if summary_only else date.fromisoformat(min(p['purchased_on'] for p in purchases))
    prices = {r['day']: r['price'] for r in daily}
    # Prefer historical daily closes to old intraday observations on past days.
    quote_days = {q['quoted_at'][:10]: q['price'] for q in sorted(quotes, key=lambda q: q['quoted_at'])}
    for key, quote_price in quote_days.items():
        if key not in prices or key == end.isoformat():
            prices[key] = quote_price
    previous = [day for day in prices if day < start.isoformat()]
    price = prices[max(previous)] if previous else None
    lots = sorted(purchases, key=lambda p: (p['purchased_on'],p.get('trade_time',''),p.get('id',0)))
    quantity, cost, realised, invested, cursor = Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0
    points = []
    day = start
    while day <= end:
        key = day.isoformat()
        while cursor < len(lots) and lots[cursor]['purchased_on'] <= key:
            lot = lots[cursor]
            units,price_at_trade=Decimal(lot['quantity']),Decimal(lot['price'])
            if lot.get('transfer_id'):
                moved_cost,moved_invested=Decimal(lot['transfer_cost']),Decimal(lot['transfer_invested'])
                if lot['side']=='SELL':
                    if units!=quantity or moved_cost!=cost or moved_invested!=invested:
                        raise ValueError('De omboeking sluit niet aan op het voorafgaande bezit. Controleer de transactiehistorie.')
                    quantity=cost=invested=Decimal(0)
                else:
                    quantity+=units;cost+=moved_cost;invested+=moved_invested
            elif lot.get('split_before','')!='':
                before=Decimal(lot['split_before'])
                if quantity<=0:raise ValueError('Splitsing zonder voorafgaand bezit. Importeer de volledige aankoopgeschiedenis.')
                if before and before!=quantity:raise ActionError('Aantal voor splitsing wijkt af van het bezit. Controleer de aankoopgeschiedenis.','split_quantity_mismatch',{'held_quantity':format(quantity,'f'),'expected_quantity':format(before,'f'),'new_quantity':format(units,'f'),'day':key})
                quantity=units
            elif lot.get('side','BUY')=='SELL':
                if units>quantity:raise ActionError('Verkoop groter dan het bezit. Importeer de volledige aankoopgeschiedenis.','sell_exceeds_holdings',{'held_quantity':format(quantity,'f'),'sell_quantity':format(units,'f'),'difference':format(units-quantity,'f'),'day':key})
                removed=cost*units/quantity
                realised+=units*price_at_trade-removed;quantity-=units;cost-=removed
                if not quantity:cost=Decimal(0)
            else:
                quantity+=units;cost+=units*price_at_trade;invested+=units*price_at_trade
            cursor += 1
        observed = key in prices
        if observed:
            price = prices[key]
        points.append(dict(day=key, cost=str(cost), value=str(quantity * Decimal(price)) if price is not None else ('0' if not quantity else None),
                           quantity=format(quantity,'f') if quantity else '0',realised=str(realised),invested=str(invested),price=price, carried=not observed))
        day += timedelta(days=1)
    return points

def with_dividends(points, dividends):
    payments = sorted(dividends, key=lambda d: d['paid_on'])
    cursor, received = 0, Decimal(0)
    for point in points:
        while cursor < len(payments) and payments[cursor]['paid_on'] <= point['day']:
            received += Decimal(payments[cursor]['amount'])
            cursor += 1
        point['dividend'] = str(received)
        value = Decimal(point['value']) if point['value'] is not None else None
        point['total_gain'] = str(value - Decimal(point['cost']) + Decimal(point.get('realised','0')) + received) if value is not None else None
        point['with_dividends'] = str(value + received) if value is not None else None
    return points

def portfolio_values(positions):
    currencies = sorted({p['currency'] for p in positions})
    result = []
    for currency in currencies:
        members = [p for p in positions if p['currency'] == currency]
        days = sorted({point['day'] for p in members for point in p['history']})
        by_position = [{point['day']: point for point in p['history']} for p in members]
        points = []
        for day in days:
            active = [history[day] for history in by_position if day in history]
            cost = sum((Decimal(p['cost']) for p in active), Decimal(0))
            income = sum((Decimal(p['dividend']) for p in active), Decimal(0))
            complete = all(p['value'] is not None for p in active)
            value = sum((Decimal(p['value']) for p in active), Decimal(0)) if complete else None
            points.append(dict(day=day, cost=str(cost), value=str(value) if complete else None,
                               dividend=str(income), with_dividends=str(value + income) if complete else None,
                               total_gain=str(value - cost + income+sum((Decimal(p.get('realised','0')) for p in active),Decimal(0))) if complete else None, price=None,
                               carried=any(p['carried'] for p in active)))
        result.append(dict(name='Portefeuille', currency=currency, history=points))
    return result
