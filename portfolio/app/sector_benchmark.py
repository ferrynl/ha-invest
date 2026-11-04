"""Compare today's sector basket against a public sector ETF on shared EUR dates."""
from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import unicodedata

from forex import prepare_rates, unit
from provider import fetch_history

BENCHMARKS = {
    'XLK': ('technology', 'technologie', 'tecnologia'),
    'XLV': ('healthcare', 'health care', 'gezondheidszorg', 'salud'),
    'XLF': ('financial services', 'financials', 'financiele diensten', 'financien', 'servicios financieros'),
    'XLE': ('energy', 'energie', 'energia'),
    'XLI': ('industrials', 'industrie', 'industria'),
    'XLRE': ('real estate', 'vastgoed', 'inmobiliario', 'bienes raices'),
    'XLY': ('consumer cyclical', 'consumer discretionary', 'cyclische consumentengoederen', 'consument cyclisch', 'consumo ciclico'),
    'XLP': ('consumer defensive', 'consumer staples', 'consumentengoederen', 'defensieve consumentengoederen', 'consumo defensivo'),
    'XLC': ('communication services', 'communicatiediensten', 'servicios de comunicacion'),
    'XLU': ('utilities', 'nutsbedrijven', 'servicios publicos'),
    'XLB': ('basic materials', 'materials', 'basismaterialen', 'materiales basicos'),
}


def sector_key(name):
    return ''.join(c for c in unicodedata.normalize('NFD', name.casefold().strip()) if not unicodedata.combining(c))


def price_series(rows, field='price'):
    result = {}
    for row in rows:
        try:
            day = date.fromisoformat(row['day'])
            value = Decimal(row[field])
            if value.is_finite() and value > 0:
                result[day] = value
        except (ArithmeticError, ValueError, TypeError):
            continue
    return result


def compare(store, positions, name, today=None):
    today = today or date.today()
    start = today - timedelta(days=365)
    key = sector_key(name)
    ticker = next((ticker for ticker, aliases in BENCHMARKS.items() if key in aliases), None)
    if not ticker:
        return {'status': 'unsupported'}
    holdings = [p for p in positions if sector_key(p['categories'].get('sector') or '') == key
                and p['quantity'] is not None and Decimal(p['quantity']) > 0]
    if not holdings:
        return {'status': 'unavailable', 'ticker': ticker}
    inputs = []
    with store.read() as db:
        db.execute('BEGIN')
        for p in holdings:
            prices = price_series(db.execute(
                'SELECT day,price FROM daily_prices WHERE symbol=? AND exchange=? AND currency=? AND day BETWEEN ? AND ?',
                (p['symbol'], p['exchange'], p['currency'], start.isoformat(), today.isoformat())))
            inputs.append((p['currency'], Decimal(p['quantity']), prices))
    common = set.intersection(*(set(prices) for _, _, prices in inputs))
    if len(common) < 2 or max(common) < today - timedelta(days=7):
        return {'status': 'unavailable', 'ticker': ticker}
    try:
        benchmark = price_series(fetch_history(ticker, 'NYSEARCA', 'USD', start.isoformat(), store=store))
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return {'status': 'provider', 'ticker': ticker}
    common_days = sorted(common & benchmark.keys())
    if len(common_days) < 2 or common_days[-1] < today - timedelta(days=7):
        return {'status': 'unavailable', 'ticker': ticker}
    currencies = {row[0] for row in inputs} | {'USD'}

    def read_rates():
        fx_rows = defaultdict(list)
        with store.read() as db:
            for row in db.execute("SELECT quote,day,rate FROM fx_rates WHERE base='EUR' AND day BETWEEN ? AND ? ORDER BY day",
                                  ((start-timedelta(days=7)).isoformat(), today.isoformat())):
                fx_rows[row['quote']].append(row)
        rates = {currency: price_series(rows, 'rate') for currency, rows in fx_rows.items()}
        return rates, {currency: sorted(rows) for currency, rows in rates.items()}

    rates, dates = read_rates()

    def euros(currency, day):
        base, scale = unit(currency)
        if base == 'EUR':
            return scale
        days = dates.get(base, [])
        i = bisect_right(days, day) - 1
        if i < 0 or (day-days[i]).days > 7:
            return None
        return scale / rates[base][days[i]]

    missing = [(currency, 'EUR', day.isoformat()) for day in (common_days[0], common_days[-1])
               for currency in currencies if euros(currency, day) is None]
    if missing:
        try:
            prepare_rates(store, missing)
        except (OSError, ValueError):
            pass
        rates, dates = read_rates()

    points = []
    for day in common_days:
        factors = {currency: euros(currency, day) for currency in currencies}
        if any(value is None for value in factors.values()):
            continue
        basket = sum(quantity * prices[day] * factors[currency] for currency, quantity, prices in inputs)
        points.append((day, basket, benchmark[day] * factors['USD']))
    if len(points) < 2 or points[-1][0] < today - timedelta(days=7):
        return {'status': 'unavailable', 'ticker': ticker}
    first, last = points[0], points[-1]
    portfolio = (last[1]/first[1]-1)*100
    reference = (last[2]/first[2]-1)*100
    return dict(status='ready', ticker=ticker, start=first[0].isoformat(), end=last[0].isoformat(),
                portfolio=str(portfolio), benchmark=str(reference), difference=str(portfolio-reference))
