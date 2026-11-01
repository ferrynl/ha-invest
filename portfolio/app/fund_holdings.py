"""Dated fund constituents, shared by listing and read without network in reports."""
import csv
import io
import json
import re
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from html.parser import HTMLParser

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 20000
ISSUERS = {'dng-api.invesco.com', 'www.ishares.com', 'www.blackrock.com', 'www.vaneck.com',
           'fund-docs.vanguard.com', 'www.vanguard.co.uk', 'www.ssga.com',
           'etf.dws.com', 'www.amundietf.com', 'www.invesco.com', 'www.spdrgoldshares.com'}
KNOWN = {
    ('EXV1.DE', 'XETRA', 'EUR'): 'https://www.ishares.com/uk/individual/en/products/251934/ishares-stoxx-europe-600-banks-ucits-etf-de-fund',
    ('IWDA.AS', 'AMSTERDAM', 'EUR'): 'https://www.ishares.com/uk/individual/en/products/251882/ishares-core-msci-world-ucits-etf',
}
_lock = threading.RLock()


def source_url(value):
    if value == '':
        return ''
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError('Kies een officiële HTTPS-bron van de fondsaanbieder.')
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.hostname not in ISSUERS or parts.port not in (None, 443)
            or parts.username or parts.password or parts.fragment
            or any(ord(c) < 33 for c in value)):
        raise ValueError('Kies een officiële HTTPS-bron van de fondsaanbieder.')
    return value


def text(value, limit=200):
    if not isinstance(value, str) or len(value) > limit or any(not c.isprintable() for c in value):
        raise ValueError('Ongeldige fondsregel.')
    return value.strip()


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('holdings'), list) or not 0 < len(payload['holdings']) <= MAX_ROWS:
        raise ValueError('De samenstelling moet minimaal één en maximaal 20.000 regels bevatten.')
    try:
        stamp = date.fromisoformat(payload['as_of'])
    except (KeyError,TypeError,ValueError):
        raise ValueError('Vul de samenstellingsdatum van de bron in.') from None
    if stamp > date.today():
        raise ValueError('De samenstellingsdatum ligt in de toekomst.')
    rows = []
    total = Decimal(0)
    for item in payload['holdings']:
        if not isinstance(item, dict):
            raise ValueError('Ongeldige fondsregel.')
        row = {k: text(item.get(k, ''), 200 if k == 'name' else 80)
               for k in ('name', 'symbol', 'isin', 'sector', 'country', 'asset_type', 'category', 'exchange', 'currency')}
        if not row['name']:
            raise ValueError('Iedere fondsregel moet een naam hebben.')
        try:
            if isinstance(item.get('weight'), bool):
                raise ValueError()
            weight = Decimal(str(item['weight']))
            if not weight.is_finite() or weight < -1000 or weight > 1000:
                raise ValueError()
        except (InvalidOperation, ValueError, KeyError):
            raise ValueError('Ongeldige of niet-eindige fondsweging.') from None
        row['weight'] = str(weight)
        total += weight
        rows.append(row)
    # Rounded issuer percentages may sum slightly above 100. Never scale a partial
    # portfolio up to 100; a genuine missing portion remains explicitly unknown.
    if not 0 < total <= Decimal('100.5'):
        raise ValueError('De som van de wegingen is ongeldig of groter dan 100,5%.')
    return dict(as_of=stamp.isoformat(), holdings=rows, coverage=str(min(total, Decimal(100))),
                rounding_excess=str(max(Decimal(0), total - 100)),signed=any(Decimal(row['weight'])<0 for row in rows))


HEADERS = {
    'name': ('name', 'naam', 'holding', 'security name', 'security description'),
    'symbol': ('ticker', 'symbol', 'symbool', 'emittententicker'),
    'isin': ('isin',),
    'weight': ('weight (%)', 'weight', 'weging (%)', 'weging', '% of net assets', '% of fund', 'gewichtung (%)'),
    'sector': ('sector', 'industry', 'gics sector', 'sektor'),
    'exchange': ('exchange', 'beurs', 'börse'),
    'currency': ('market currency', 'currency', 'valuta', 'marktwährung'),
    'country': ('location', 'country', 'land', 'country of risk', 'standort'),
    'asset_type': ('asset class', 'type', 'asset type', 'anlageklasse'),
    'category': ('category', 'categorie'),
}

GERMAN_SECTORS = dict(zip(('IT','Financials','Gesundheitsversorgung','Industrie','Zyklische Konsumgüter','Nichtzyklische Konsumgüter','Kommunikation','Energie','Materialien','Versorger','Immobilien'),
                         ('Technology','Financials','Healthcare','Industrials','Consumer Cyclical','Consumer Defensive','Communication Services','Energy','Basic Materials','Utilities','Real Estate')))
GERMAN_SECTORS.update({'Finanzwesen':'Financials','Barmittel & Derivate':'Cash and/or Derivatives'})
GERMAN_COUNTRIES = dict(zip(('Vereinigte Staaten','Vereinigtes Königreich','Deutschland','Frankreich','Niederlande','Schweiz','Spanien','Italien','Belgien','Österreich','Finnland','Schweden','Norwegen','Dänemark','Irland','Portugal','Japan','China','Taiwan','Korea','Südkorea','Hongkong','Australien','Kanada','Brasilien','Indien','Südafrika','Mexiko','Israel','Singapur','Neuseeland','Luxemburg','Europäische Union','Saudi-Arabien','Griechenland','Polen','Türkei','Thailand','Indonesien','Malaysia','Philippinen'),
                           ('US','GB','DE','FR','NL','CH','ES','IT','BE','AT','FI','SE','NO','DK','IE','PT','JP','CN','TW','KR','KR','HK','AU','CA','BR','IN','ZA','MX','IL','SG','NZ','LU','EU','SA','GR','PL','TR','TH','ID','MY','PH')))


def parse_csv(content, as_of=''):
    if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Kies een CSV-bestand van maximaal 8 MB.')
    content = content.lstrip('\ufeff')
    lines = content.splitlines()
    # Issuer files often start with metadata, not the column header.
    header = None
    delimiter = ','
    fields = {}
    for i, line in enumerate(lines[:100]):
        for separator in (',', ';', '\t'):
            cells = next(csv.reader([line], delimiter=separator))
            normalized = [c.strip().lower() for c in cells]
            found = {key: next((n for n, c in enumerate(normalized) if c in aliases), None)
                     for key, aliases in HEADERS.items()}
            if found['name'] is not None and found['weight'] is not None:
                header, delimiter, fields = i, separator, found
                break
        if header is not None:
            break
    if header is None:
        raise ValueError('CSV mist de kolommen Naam en Weging (%).')
    german = 'gewichtung (%)' in lines[header].lower()
    if not as_of:
        match = re.search(r'(?:Fund Holdings as of|Holdings as of|Fondsposition per)[,;\t]"?([^"\r\n]+)', content[:10000], re.I)
        if match:
            raw = match[1].strip()
            for local, english in (('Okt','Oct'),('Mär','Mar'),('Mai','May'),('Dez','Dec'),('Sept','Sep')):
                raw = raw.replace(local, english)
            for fmt in ('%d/%b/%Y', '%d-%b-%Y', '%Y-%m-%d', '%d.%b.%Y'):
                try:
                    as_of = datetime.strptime(raw, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
    if not as_of:
        raise ValueError('Vul de samenstellingsdatum van de bron in.')
    rows = []
    for cells in csv.reader(io.StringIO('\n'.join(lines[header + 1:])), delimiter=delimiter):
        if not cells or all(not c.strip() for c in cells):
            continue
        def field(key):
            n = fields[key]
            return cells[n].strip() if n is not None and n < len(cells) else ''
        name, raw = field('name'), field('weight')
        # A footer may contain a disclaimer; a malformed actual data row must fail.
        if not name and not raw:
            continue
        row = {key: field(key) for key in HEADERS}
        row['weight'] = raw.replace('%', '').replace('\u00a0', '').replace(' ', '')
        if german:
            row['weight'] = row['weight'].replace('.', '').replace(',', '.')
            row['sector'] = GERMAN_SECTORS.get(row['sector'], row['sector'])
            row['country'] = GERMAN_COUNTRIES.get(row['country'], row['country'])
            row['asset_type'] = {'Aktien':'Equity','Obligationen':'Fixed Income','Geldmarkt':'Cash','Cash und/oder Derivate':'Cash and/or Derivatives'}.get(row['asset_type'], row['asset_type'])
        elif delimiter in (';', '\t'):
            row['weight'] = row['weight'].replace(',', '.')
        rows.append(row)
        if len(rows) > MAX_ROWS:
            raise ValueError('Te veel fondsregels.')
    return validate(dict(as_of=as_of, holdings=rows))


class IssuerRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        source_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(url):
    source_url(url)
    with build_opener(IssuerRedirect()).open(Request(url, headers={'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/csv,text/html;q=0.8', 'Accept-Language': 'en-GB,en;q=0.9'}), timeout=20) as response:
        source_url(response.url)
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Bronbestand te groot.')
        return data.decode('utf-8-sig')


class HoldingsLink(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href', '')
        if 'latest-holdings.csv' in href or ('fileType=csv' in href and 'dataType=fund' in href):
            self.links.append(href)


def retrieve(url, as_of=''):
    from urllib.parse import urljoin
    from fund_providers import retrieve_invesco,retrieve_vaneck,retrieve_vanguard
    if urlsplit(url).hostname=='dng-api.invesco.com':return retrieve_invesco(url)
    if '/Main/HoldingsBlock/' in url:return retrieve_vaneck(url)
    if urlsplit(url).hostname=='www.vanguard.co.uk' and '/product/etf/' in url:return retrieve_vanguard(url)
    content = download(url)
    if '<html' in content[:10000].lower() or '<!doctype' in content[:1000].lower():
        parser = HoldingsLink()
        parser.feed(content)
        links = {urljoin(url, link) for link in parser.links}
        if len(links) != 1:
            raise ValueError('Geen eenduidige volledige CSV-bron gevonden. Importeer het bronbestand.')
        content = download(links.pop())
    return parse_csv(content, as_of)


def saved(store, key):
    with store.read() as db:
        row = db.execute('SELECT * FROM fund_compositions WHERE symbol=? AND exchange=? AND currency=?', key).fetchone()
    if not row:
        return None
    row = dict(row)
    payload = validate(json.loads(row.pop('payload')))
    return {**row, **payload, 'stale': (date.today() - date.fromisoformat(payload['as_of'])).days > 14}


def all_saved(db):
    result = []
    for row in db.execute('SELECT * FROM fund_compositions'):
        row = dict(row)
        payload = validate(json.loads(row.pop('payload')))
        result.append({**row, **payload, 'stale': (date.today() - date.fromisoformat(payload['as_of'])).days > 14})
    return result


def save(store, key, payload, url=''):
    from instruments import identity
    identity(dict(zip(('symbol', 'exchange', 'currency'), key)))
    url = source_url(url)
    payload = validate(payload)
    previous = saved(store, key)
    if previous and payload['as_of'] < previous['as_of']:
        raise ValueError('Een oudere samenstelling mag een nieuwere niet vervangen.')
    stamp = datetime.now(timezone.utc).isoformat()
    with store.connect() as db:
        db.execute('INSERT INTO fund_compositions VALUES(?,?,?,?,?,?,?) ON CONFLICT(symbol,exchange,currency) DO UPDATE SET source_url=excluded.source_url,as_of=excluded.as_of,fetched_at=excluded.fetched_at,payload=excluded.payload',
                   (*key, url, payload['as_of'], stamp, json.dumps(payload)))
    return saved(store, key)


def refresh(store, key, url=None, as_of='', content=None):
    with _lock:
        previous = saved(store, key)
        url = source_url(url if url is not None else previous['source_url'] if previous else KNOWN.get(tuple(key), ''))
        cache_key = json.dumps([*key,url])
        if content is not None:
            payload = parse_csv(content, as_of)
        else:
            if not url:
                raise ValueError('Koppel de officiële bron of importeer de volledige CSV-samenstelling.')
            with store.read() as db:
                pause = db.execute("SELECT expires_at FROM api_cache WHERE namespace='fund-refresh' AND cache_key=?", (cache_key,)).fetchone()
            if pause and pause[0] > time.time():
                if previous:
                    return previous
                raise ValueError('Bron tijdelijk niet beschikbaar. Probeer later opnieuw.')
            # Persist cooldown before the request, including when the provider fails.
            with store.connect() as db:
                stamp = time.time()
                db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)', ('fund-refresh', cache_key, '{}', stamp, stamp + 3600))
            payload = retrieve(url, as_of)
        return save(store, key, payload, url)


def background_refresh(store, key, is_etf=False):
    previous = saved(store, key)
    if not is_etf and tuple(key) not in KNOWN:
        return False
    if previous and (not previous['source_url'] or (datetime.now(timezone.utc) - datetime.fromisoformat(previous['fetched_at'])).total_seconds() < 86400):
        return False
    if not previous and tuple(key) not in KNOWN:
        return False
    try:
        result=refresh(store, key)
        return not previous or result['fetched_at']!=previous['fetched_at']
    except Exception as error:
        from diagnostics import record
        record(store, 'WARNING', 'market', 'fund_holdings_failed', 'ETF-samenstelling ophalen mislukt.', {'symbol': key[0], 'error_type': type(error).__name__})
        return False
