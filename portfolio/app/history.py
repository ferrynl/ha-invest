"""Daily valuation, preserving unknown prices instead of inventing market data."""
from datetime import date, timedelta
from decimal import Decimal

def daily_values(purchases, daily, quotes, today=None):
    end = today or date.today()
    start = date.fromisoformat(min(p['purchased_on'] for p in purchases))
    prices = {r['day']: r['price'] for r in daily}
    # Prefer historical daily closes to old intraday observations on past days.
    quote_days = {q['quoted_at'][:10]: q['price'] for q in sorted(quotes, key=lambda q: q['quoted_at'])}
    for key, quote_price in quote_days.items():
        if key not in prices or key == end.isoformat():
            prices[key] = quote_price
    previous = [day for day in prices if day < start.isoformat()]
    price = prices[max(previous)] if previous else None
    lots = sorted(purchases, key=lambda p: p['purchased_on'])
    quantity, cost, cursor = Decimal(0), Decimal(0), 0
    points = []
    day = start
    while day <= end:
        key = day.isoformat()
        while cursor < len(lots) and lots[cursor]['purchased_on'] <= key:
            lot = lots[cursor]
            quantity += Decimal(lot['quantity'])
            cost += Decimal(lot['quantity']) * Decimal(lot['price'])
            cursor += 1
        observed = key in prices
        if observed:
            price = prices[key]
        points.append(dict(day=key, cost=str(cost), value=str(quantity * Decimal(price)) if price is not None else None,
                           price=price, carried=not observed))
        day += timedelta(days=1)
    return points
