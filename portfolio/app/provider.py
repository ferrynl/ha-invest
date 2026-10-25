"""Best-effort Yahoo public endpoint, not an official supported API."""
import json
from urllib.request import urlopen, Request
from urllib.parse import quote, urlencode
from datetime import datetime, timezone, date, timedelta
from functools import lru_cache
import time
from urllib.error import HTTPError
from persistent_cache import cached_json
from forex import code as currency_code

class ProviderBusy(ValueError):
    pass

def _payload(request,timeout,store,namespace,key,ttl):
    def load():
        if store:
            with store.connect() as db:pause=db.execute("SELECT expires_at FROM api_cache WHERE namespace='provider-cooldown' AND cache_key='yahoo'").fetchone()
            if pause and pause[0]>time.time():raise ProviderBusy('Yahoo heeft tijdelijk een aanvraaglimiet. Automatisch koppelen is gepauzeerd; probeer over enkele minuten opnieuw. Opgeslagen koppelingen blijven bruikbaar.')
        try:
            with urlopen(request,timeout=timeout) as response:result=json.load(response)
        except HTTPError as error:
            if error.code not in (429,503):raise
            try:delay=min(3600,max(60,int(error.headers.get('Retry-After','120'))))
            except (ValueError,TypeError):delay=120
            if store:
                stamp=time.time()
                with store.connect() as db:db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',('provider-cooldown','yahoo','{}',stamp,stamp+delay))
            raise ProviderBusy('Yahoo heeft tijdelijk een aanvraaglimiet. Automatisch koppelen is gepauzeerd; probeer over enkele minuten opnieuw. Opgeslagen koppelingen blijven bruikbaar.') from error
        if result.get('status')=='error' or (isinstance(result.get('chart'),dict) and result['chart'].get('error')):raise ValueError('Koersdienst retourneerde een fout.')
        return result
    return cached_json(store,namespace,key,ttl,load)

EXCHANGES = {'AMS': ('AMSTERDAM', 'EUR'), 'BRU': ('BRUSSELS', 'EUR'), 'MCE': ('MADRID','EUR'), 'PNK': ('OTC','USD'), 'NMS': ('NASDAQ', 'USD'),
             'NGM': ('NASDAQ', 'USD'), 'NCM': ('NASDAQ', 'USD'),
             'NASDAQ': ('NASDAQ', 'USD'), 'NYQ': ('NYSE', 'USD'), 'NYSE': ('NYSE', 'USD'),
             'PCX': ('NYSEARCA','USD'), 'ASE': ('AMEX','USD'),
             'GER': ('XETRA','EUR'), 'PAR': ('PARIS','EUR'), 'MIL': ('MILAN','EUR'),
             'LSE': ('LONDON','GBP'), 'EBS': ('SWISS','CHF'), 'FRA': ('FRANKFURT','EUR'),
             'PRIVATE': ('PRIVATE','EUR')}

def search_stocks(query,store=None):
    query = query.strip()
    if not 2 <= len(query) <= 80:
        raise ValueError('Gebruik 2 tot 80 tekens.')
    return _search_stocks(query.casefold(), int(time.time() // 60),store)

@lru_cache(maxsize=256)
def _search_stocks(query, minute,store=None):
    params = urlencode({'q': query, 'quotesCount': 50, 'newsCount': 0, 'listsCount': 0, 'enableFuzzyQuery': 'false'})
    request = Request('https://query1.finance.yahoo.com/v1/finance/search?' + params,
                      headers={'User-Agent': 'Mozilla/5.0'})
    payload=_payload(request,10,store,'yahoo-search-v4',query,7*86400)
    matches, seen = [], set()
    for item in payload.get('quotes', []):
        market = EXCHANGES.get(item.get('exchange', '').upper())
        symbol = item.get('symbol')
        if not market or item.get('quoteType') not in ('EQUITY','ETF','MUTUALFUND') or not symbol or symbol in seen:
            continue
        seen.add(symbol)
        exchange, currency = market
        matches.append(dict(symbol=symbol, name=item.get('longname') or item.get('shortname') or symbol,
                            exchange=exchange, currency=currency))
    return matches

def listing(symbol,store=None):
    request=Request('https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?interval=1d&range=1d',headers={'User-Agent':'Mozilla/5.0'})
    meta=_payload(request,20,store,'yahoo-listing-v2',symbol,7*86400)['chart']['result'][0]['meta']
    market=EXCHANGES.get(meta.get('exchangeName','').upper())
    if not market or meta.get('symbol','').upper()!=symbol.upper():raise ValueError('Notering of beurs kon niet worden gecontroleerd.')
    return {'symbol':symbol.upper(),'exchange':market[0],'currency':currency_code(meta['currency']),'name':str(meta.get('longName') or meta.get('shortName') or symbol)[:100]}

def fetch_quote(key, symbol, exchange, currency,store=None,ttl=900):
    request = Request('https://query1.finance.yahoo.com/v8/finance/chart/' + quote(symbol, safe='') + '?interval=1d&range=1d', headers={'User-Agent': 'Mozilla/5.0'})
    result=_payload(request,20,store,'yahoo-quote','|'.join((symbol,exchange,currency)),ttl)['chart']['result'][0]['meta']
    if currency_code(result.get('currency','')) != currency_code(currency):
        raise ValueError('Koersvaluta wijkt af van de aankoop; koers niet opgeslagen.')
    market=EXCHANGES.get(result.get('exchangeName','').upper())
    if result.get('symbol', '').upper() != symbol or not market or market[0]!=exchange:
        raise ValueError('Koersdienst retourneerde een ander symbool of andere beurs.')
    timestamp = datetime.fromtimestamp(int(result['regularMarketTime']), timezone.utc).isoformat()
    return result['regularMarketPrice'], timestamp

def fetch_history(symbol, exchange, currency, start,store=None):
    # Include a preceding trading day so a weekend purchase has a reference price.
    first = datetime.combine(date.fromisoformat(start) - timedelta(days=10), datetime.min.time(), timezone.utc)
    params = urlencode({'interval': '1d', 'period1': int(first.timestamp()),
                        'period2': int(datetime.now(timezone.utc).timestamp()), 'events': 'history'})
    request = Request('https://query1.finance.yahoo.com/v8/finance/chart/' + quote(symbol, safe='') + '?' + params,
                      headers={'User-Agent': 'Mozilla/5.0'})
    result=_payload(request,30,store,'yahoo-history','|'.join((symbol,exchange,currency,start,date.today().isoformat())),86400)['chart']['result'][0]
    meta = result['meta']
    market = EXCHANGES.get(meta.get('exchangeName', '').upper())
    if meta.get('symbol', '').upper() != symbol or currency_code(meta.get('currency','')) != currency_code(currency) or not market or market[0] != exchange:
        raise ValueError('Historische notering of valuta wijkt af.')
    closes = result['indicators']['quote'][0]['close']
    rows = []
    for stamp, close in zip(result.get('timestamp', []), closes):
        if close is not None and close > 0:
            rows.append({'day': datetime.fromtimestamp(stamp, timezone.utc).date().isoformat(), 'price': str(close)})
    if not rows:
        raise ValueError('Geen historische dagkoersen beschikbaar.')
    return rows
