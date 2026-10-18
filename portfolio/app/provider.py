"""Best-effort Yahoo public endpoint, not an official supported API."""
import json
from urllib.request import urlopen, Request
from urllib.parse import quote
from datetime import datetime, timezone

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
