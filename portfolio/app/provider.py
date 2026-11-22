"""Best-effort Yahoo public endpoint, not an official supported API."""
import json
import math
from email.utils import parsedate_to_datetime
from urllib.request import urlopen, Request
from urllib.parse import quote, urlencode, urlsplit
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from functools import lru_cache
import time
from urllib.error import HTTPError, URLError
from persistent_cache import cached_json
from diagnostics import ActionError, record
from forex import code as currency_code

class ProviderBusy(ActionError):
    def __init__(self, message, retry_seconds=None, http_status=None):
        code = 'provider_rate_limited' if http_status == 429 else 'provider_unavailable' if http_status == 503 else 'provider_cooldown'
        details = {}
        if retry_seconds is not None:details['retry_seconds'] = retry_seconds
        if http_status is not None:details['http_status'] = http_status
        super().__init__(message, code, details)


def error_details(error):
    """Only application-authored reasons and fixed request metadata enter logs."""
    details = {'error_type': type(error).__name__, 'code': 'provider_failed',
               'reason': 'Actuele koers ophalen mislukt.'}
    if isinstance(error, ActionError):
        details.update(error.details, code=error.code, reason=str(error))
    elif isinstance(error, HTTPError):
        details.update(code='provider_http_error', http_status=error.code,
                       reason='Aanvraag kon niet worden verwerkt.')
    elif isinstance(error, (TimeoutError, URLError, OSError)):
        details.update(code='provider_connection_failed',
                       reason='Verbinding mislukt.')
        if isinstance(error, URLError):
            details['connection_error_type'] = type(error.reason).__name__
    elif isinstance(error, (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError)):
        details.update(code='provider_invalid_response',
                       reason='Koersdienst retourneerde een fout.')
    details.update(getattr(error, 'provider_details', {}))
    return details


def failure_key(event, instrument):
    symbol, exchange, currency = instrument
    return '|'.join((event, quote_symbol(symbol, exchange), exchange, currency_code(currency)))


def record_failure(store, event, message, instrument, error):
    details = error_details(error)
    shared_outage = details['code'] in (
        'provider_rate_limited', 'provider_unavailable', 'provider_cooldown',
        'provider_connection_failed', 'provider_http_error',
    ) and details.get('endpoint_host') in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com')
    once = 'yahoo-availability' if shared_outage else failure_key(event, instrument)
    return record(store, 'WARNING', 'market', event, message,
                  dict(zip(('symbol', 'exchange', 'currency'), instrument)) | details, once=once)


def clear_failure(store, key):
    if store is not None:
        with store.connect() as db:
            db.execute("DELETE FROM api_cache WHERE namespace='market-log-once' AND cache_key=?", (key,))


def _busy_message(http_status):
    return ('Bron tijdelijk niet beschikbaar. Probeer later opnieuw.'
            if http_status == 503 else
            'Yahoo heeft tijdelijk een aanvraaglimiet. Automatisch koppelen is gepauzeerd; probeer over enkele minuten opnieuw. Opgeslagen koppelingen blijven bruikbaar.')


def _retry_seconds(headers):
    raw = (headers or {}).get('Retry-After', '120')
    try:
        delay = int(raw)
    except (ValueError, TypeError):
        try:
            stamp = parsedate_to_datetime(raw)
            if stamp.tzinfo is None:stamp = stamp.replace(tzinfo=timezone.utc)
            delay = math.ceil(stamp.timestamp() - time.time())
        except (ValueError, TypeError, IndexError, OverflowError):
            delay = 120
    return max(60, delay)


def _payload(request,timeout,store,namespace,key,ttl):
    def load():
        started = time.monotonic()
        pause = None
        saved = {}
        try:
            if store:
                with store.connect() as db:
                    pause = db.execute("SELECT payload,fetched_at,expires_at FROM api_cache WHERE namespace='provider-cooldown' AND cache_key='yahoo'").fetchone()
                if pause:
                    try:
                        saved = json.loads(pause['payload'])
                        if not isinstance(saved, dict):saved = {}
                    except (ValueError, TypeError):
                        saved = {}
                    if pause['expires_at'] > time.time():
                        http_status = saved.get('http_status')
                        if http_status not in (429, 503):http_status = None
                        delay = max(1, math.ceil(pause['expires_at'] - time.time()))
                        raise ProviderBusy(_busy_message(http_status), delay, http_status)
            try:
                with urlopen(request,timeout=timeout) as response:result=json.load(response)
            except HTTPError as error:
                if error.code not in (429,503):raise
                http_status = error.code
                delay = _retry_seconds(error.headers)
                error.close()
                attempts = 0
                if http_status == 429:
                    previous_attempts = saved.get('attempts', 0)
                    if (not pause or pause['fetched_at'] < time.time() - 86400
                            or saved.get('http_status') != 429 or type(previous_attempts) is not int):
                        previous_attempts = 0
                    attempts = min(6, max(0, previous_attempts) + 1)
                    delay = max(delay, min(21600, 900 * 2 ** (attempts - 1)))
                if store:
                    stamp=time.time()
                    with store.connect() as db:
                        db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',
                                   ('provider-cooldown','yahoo',json.dumps({'http_status':http_status,'attempts':attempts}),stamp,stamp+delay))
                raise ProviderBusy(_busy_message(http_status), delay, http_status) from error
            if not isinstance(result, dict):
                raise ActionError('Koersdienst retourneerde een fout.', 'provider_invalid_response')
            if result.get('status')=='error' or (isinstance(result.get('chart'),dict) and result['chart'].get('error')):
                raise ActionError('Koersdienst retourneerde een fout.', 'provider_response_error')
            if store and pause:
                with store.connect() as db:
                    db.execute("DELETE FROM api_cache WHERE namespace='provider-cooldown' AND cache_key='yahoo' AND expires_at<=?", (time.time(),))
            clear_failure(store, 'yahoo-availability')
            return result
        except Exception as error:
            error.provider_details = {'endpoint_host': urlsplit(request.full_url).hostname,
                                      'stage': namespace, 'duration_ms': round((time.monotonic()-started)*1000)}
            raise
    return cached_json(store,namespace,key,ttl,load)

EXCHANGES = {'AMS': ('AMSTERDAM', 'EUR'), 'BRU': ('BRUSSELS', 'EUR'), 'ISE': ('DUBLIN', 'EUR'), 'MCE': ('MADRID','EUR'), 'PNK': ('OTC','USD'), 'OTCQX': ('OTC','USD'), 'OQX': ('OTC','USD'), 'NMS': ('NASDAQ', 'USD'),
             'NGM': ('NASDAQ', 'USD'), 'NCM': ('NASDAQ', 'USD'),
             'NASDAQ': ('NASDAQ', 'USD'), 'NYQ': ('NYSE', 'USD'), 'NYSE': ('NYSE', 'USD'),
             'PCX': ('NYSEARCA','USD'), 'ASE': ('AMEX','USD'),
             'GER': ('XETRA','EUR'), 'PAR': ('PARIS','EUR'), 'MIL': ('MILAN','EUR'),
             'LSE': ('LONDON','GBP'), 'EBS': ('SWISS','CHF'), 'FRA': ('FRANKFURT','EUR'),
             'JPX':('TOKYO','JPY'),'TOR':('TORONTO','CAD'),'ASX':('ASX','AUD'),'HKG':('HONG KONG','HKD'),'CPH':('COPENHAGEN','DKK'),'STO':('STOCKHOLM','SEK'),
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

# Resolve internal listing identifiers without changing booked transactions.
def quote_symbol(symbol,exchange):
    suffix={'AMSTERDAM':'.AS','BRUSSELS':'.BR','DUBLIN':'.IR','MADRID':'.MC','XETRA':'.DE','PARIS':'.PA','MILAN':'.MI','LONDON':'.L','SWISS':'.SW','TOKYO':'.T','TORONTO':'.TO','ASX':'.AX','HONG KONG':'.HK','COPENHAGEN':'.CO','STOCKHOLM':'.ST'}.get(exchange,'')
    if suffix and symbol.endswith(suffix):return symbol
    if exchange=='HONG KONG':symbol=symbol.lstrip('0').zfill(4)
    if exchange in ('COPENHAGEN','STOCKHOLM'):symbol=symbol.replace('.','-')
    if exchange=='LONDON' and symbol=='BA':symbol='BA.'
    return symbol if not suffix or symbol.endswith(suffix) else symbol+suffix

def fetch_quote(key, symbol, exchange, currency,store=None,ttl=900):
    request = Request('https://query1.finance.yahoo.com/v8/finance/chart/' + quote(quote_symbol(symbol,exchange), safe='') + '?interval=1d&range=1d', headers={'User-Agent': 'Mozilla/5.0'})
    result=_payload(request,20,store,'yahoo-quote-v2','|'.join((quote_symbol(symbol,exchange),exchange)),ttl)['chart']['result'][0]['meta']
    from decimal import Decimal
    source_currency=currency_code(result.get('currency',''))
    pence_to_pounds=source_currency=='GBX' and currency_code(currency)=='GBP'
    if source_currency != currency_code(currency) and not pence_to_pounds:
        raise ActionError('Koersvaluta wijkt af van de aankoop; koers niet opgeslagen.', 'quote_currency_mismatch', {'source_currency':source_currency,'expected_currency':currency_code(currency)})
    market=EXCHANGES.get(result.get('exchangeName','').upper())
    if result.get('symbol', '').upper() != quote_symbol(symbol,exchange).upper() or not market or market[0]!=exchange:
        raise ActionError('Koersdienst retourneerde een ander symbool of andere beurs.', 'quote_listing_mismatch')
    timestamp = datetime.fromtimestamp(int(result['regularMarketTime']), timezone.utc).isoformat()
    price = str(Decimal(str(result['regularMarketPrice']))*Decimal('.01')) if pence_to_pounds else result['regularMarketPrice']
    clear_failure(store, failure_key('quote_failed', (symbol,exchange,currency)))
    return price, timestamp

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
        raise ActionError('Historische notering of valuta wijkt af.', 'history_listing_mismatch')
    closes = result['indicators']['quote'][0]['close']
    rows = []
    for stamp, close in zip(result.get('timestamp', []), closes):
        if close is not None and close > 0:
            rows.append({'day': datetime.fromtimestamp(stamp, timezone.utc).date().isoformat(), 'price': str(close)})
    if not rows:
        raise ActionError('Geen historische dagkoersen beschikbaar.', 'history_empty')
    clear_failure(store, failure_key('history_failed', (symbol,exchange,currency)))
    return rows


def fetch_monthly_prices(symbol, exchange, currency, store):
    now = datetime.now(timezone.utc)
    start = datetime(now.year - 6, 12, 1, tzinfo=timezone.utc) - timedelta(days=7)
    ticker = quote_symbol(symbol, exchange)
    params = urlencode({'interval': '1mo', 'period1': int(start.timestamp()),
                        'period2': int(now.timestamp())})
    request = Request('https://query1.finance.yahoo.com/v8/finance/chart/' + quote(ticker, safe='') + '?' + params,
                      headers={'User-Agent': 'Mozilla/5.0'})
    key = '|'.join((ticker, exchange, currency, str(now.year)))
    result = _payload(request, 8, store, 'yahoo-monthly-prices', key, 6 * 3600)['chart']['result'][0]
    meta = result['meta']
    market = EXCHANGES.get(meta.get('exchangeName', '').upper())
    if meta.get('symbol', '').upper() != ticker.upper() or currency_code(meta.get('currency', '')) != currency_code(currency) or not market or market[0] != exchange:
        raise ActionError('Historische notering of valuta wijkt af.', 'history_listing_mismatch')
    closes = result['indicators']['quote'][0]['close']
    try:
        exchange_time = ZoneInfo(meta.get('exchangeTimezoneName') or 'UTC')
    except (ZoneInfoNotFoundError, ValueError):
        exchange_time = timezone(timedelta(seconds=int(meta.get('gmtoffset', 0))))
    return [
        {'day': datetime.fromtimestamp(stamp, exchange_time).date().replace(day=1).isoformat(),
         'price': str(close)}
        for stamp, close in zip(result.get('timestamp', []), closes)
        if isinstance(close, (int, float)) and math.isfinite(close) and close > 0
    ]
