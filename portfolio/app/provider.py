"""Best-effort Yahoo public endpoint, not an official supported API."""
import json
from urllib.request import urlopen, Request
from urllib.parse import quote, urlencode
from datetime import datetime, timezone
from functools import lru_cache
import time

EXCHANGES = {'AMS': ('AMSTERDAM', 'EUR'), 'NMS': ('NASDAQ', 'USD'),
             'NGM': ('NASDAQ', 'USD'), 'NCM': ('NASDAQ', 'USD'),
             'NASDAQ': ('NASDAQ', 'USD'), 'NYQ': ('NYSE', 'USD'), 'NYSE': ('NYSE', 'USD')}

def search_stocks(query):
    query = query.strip()
    if not 2 <= len(query) <= 80:
        raise ValueError('Gebruik 2 tot 80 tekens.')
    return _search_stocks(query.casefold(), int(time.time() // 60))

@lru_cache(maxsize=256)
def _search_stocks(query, minute):
    params = urlencode({'q': query, 'quotesCount': 50, 'newsCount': 0, 'listsCount': 0, 'enableFuzzyQuery': 'false'})
    request = Request('https://query1.finance.yahoo.com/v1/finance/search?' + params,
                      headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)
    matches, seen = [], set()
    for item in payload.get('quotes', []):
        market = EXCHANGES.get(item.get('exchange', '').upper())
        symbol = item.get('symbol')
        if not market or item.get('quoteType') != 'EQUITY' or not symbol or symbol in seen:
            continue
        seen.add(symbol)
        exchange, currency = market
        matches.append(dict(symbol=symbol, name=item.get('longname') or item.get('shortname') or symbol,
                            exchange=exchange, currency=currency))
    return matches

def fetch_quote(key, symbol, exchange, currency):
    request = Request('https://query1.finance.yahoo.com/v8/finance/chart/' + quote(symbol, safe='') + '?interval=1d&range=1d', headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=20) as response:
        result = json.load(response)['chart']['result'][0]['meta']
    if result.get('currency') != currency:
        raise ValueError('Koersvaluta wijkt af van de aankoop; koers niet opgeslagen.')
    allowed = {'AMSTERDAM': {'AMS'}, 'NASDAQ': {'NMS', 'NGM', 'NCM', 'NASDAQ'}, 'NYSE': {'NYQ', 'NYSE'}}
    if result.get('symbol', '').upper() != symbol or result.get('exchangeName', '').upper() not in allowed.get(exchange, set()):
        raise ValueError('Koersdienst retourneerde een ander symbool of andere beurs.')
    timestamp = datetime.fromtimestamp(int(result['regularMarketTime']), timezone.utc).isoformat()
    return result['regularMarketPrice'], timestamp
