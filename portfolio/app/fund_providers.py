"""Free issuer website data. Catalog discovery is only called by an explicit task."""
import json
import re
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar
from persistent_cache import cached_json
from fund_holdings import source_url, IssuerRedirect, validate, MAX_BYTES, MAX_ROWS

VANGUARD = 'https://www.vanguard.co.uk/gpx/graphql'
INVESCO = 'https://dng-api.invesco.com'
VANECK = 'https://www.vaneck.com'
VG_FIELDS = 'issuerName securityLongDescription gicsSectorDescription icbSectorDescription marketValuePercentage ticker securityType effectiveDate bloombergIsoCountry'


def request(url, data=None, form=False, opener=None, consumer=False):
    source_url(url)
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json,text/html;q=0.8',
               'Accept-Language': 'en-GB,en;q=0.9'}
    if consumer:
        # Public website identifier, from Vanguard's shipped client configuration.
        headers['X-Consumer-ID'] = 'uk2'
    body = None
    if data is not None:
        body = (urlencode(data) if form else json.dumps(data)).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
    opener = opener or build_opener(IssuerRedirect(), HTTPCookieProcessor(CookieJar()))
    with opener.open(Request(url, data=body, headers=headers), timeout=25) as response:
        source_url(response.url)
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('Bronbestand te groot.')
        return content.decode('utf-8-sig')


def graphql(query, variables):
    result = json.loads(request(VANGUARD, {'query': query, 'variables': variables}, consumer=True))
    if result.get('errors') or not isinstance(result.get('data'), dict):
        raise ValueError('De fondsaanbieder retourneerde geen geldige gegevens.')
    return result['data']


def token(value):
    return re.sub(r'[^a-z0-9]', '', str(value).lower())


def issuer_name(name):
    value = token(name)
    for issuer in ('invesco', 'vaneck', 'vanguard', 'ishares'):
        if issuer in value:
            return issuer
    return ''


def invesco_catalog():
    params = dict(q='*:*', fq=['countryCode:"GB"', 'language:"en_uk"',
                  'accountType:"ETF"', 'contentType:"Product"'], rows=2000, start=0,
                  fl='isin,ticker,shareClassFullName,title,bloombergTicker')
    result = json.loads(request(INVESCO + '/product/search?' + urlencode(params, doseq=True)))['response']
    if result['numFound'] > len(result['docs']):
        raise ValueError('De fondscatalogus is onvolledig.')
    rows = []
    for p in result['docs']:
        isin = p.get('isin', '')
        if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', isin):
            continue
        rows.append(dict(issuer='invesco', isin=isin, name=p.get('shareClassFullName') or p.get('title', ''),
                         symbols=[p.get('ticker', ''), p.get('bloombergTicker', '').split(' ')[0]],
                         url=INVESCO + '/cache/v1/accounts/en_GB/shareclasses/' + isin + '/holdings/fund?idType=isin'))
    return rows


def vanguard_catalog():
    page = request('https://www.vanguard.co.uk/professional/product')
    match = re.search(r'<script id="serverApp-state" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError('De fondscatalogus is onvolledig.')
    state = json.loads(match[1])
    config = state['_angular_initial_state'][':items']['root'][':items']['site-config']
    ids = config['portIds'].split(',')
    if len(ids) > 2000:
        raise ValueError('De fondscatalogus is onvolledig.')
    query = 'query($portIds:[String!]){funds(portIds:$portIds){portId profile{fundFullName fundCurrency polarisPdtTypeIndicator identifiers{altId altIdValue}}}}'
    funds = graphql(query, {'portIds': ids})['funds']
    result = []
    for p in funds:
        profile = p['profile']
        if profile.get('polarisPdtTypeIndicator') != 'ETF':
            continue
        identifiers = profile.get('identifiers') or []
        isin = next((r['altIdValue'] for r in identifiers if r['altId'] == 'ISIN'), '')
        if not isin:
            continue
        # The product id is used by Vanguard independently of the selected venue.
        slug=re.sub(r'[^a-z0-9]+','-',profile['fundFullName'].lower().removeprefix('vanguard ')).strip('-')
        url = 'https://www.vanguard.co.uk/professional/product/etf/equity/' + p['portId'] + '/' + slug
        result.append(dict(issuer='vanguard', isin=isin, name=profile['fundFullName'],
                           symbols=[r['altIdValue'] for r in identifiers if r['altId'] in ('Reuters', 'Bloomberg', 'Ticker')], url=url))
    return result


def vaneck_catalog():
    opener = build_opener(IssuerRedirect(), HTTPCookieProcessor(CookieJar()))
    page = request(VANECK + '/nl/en/fundlisting/overview/etfs/', opener=opener)
    match = re.search(r'currentPageId\s*=\s*(\d+)', page)
    if not match:
        raise ValueError('De fondscatalogus is onvolledig.')
    params = dict(InvType='all', AssetClass=[], Funds=[], ShareClass=[], TableType='search',
                  CurrentPageId=match[1], CountryIso='NL', LanguageIso='en', InvestorType='')
    result = json.loads(request(VANECK + '/Main/FundListingUcits/GetFundData/',
                               {'filterJson': json.dumps(params)}, form=True, opener=opener))
    if not result.get('Success'):
        raise ValueError('De fondscatalogus is onvolledig.')
    rows = []
    for p in result['Result']['FundSet']:
        if p.get('TickerGroup', '').upper() not in ('ETF', 'ETN'):
            continue
        ticker = p['FundID']
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,30}', ticker):
            continue
        # HoldingsBlock is VanEck's public full-list renderer. Its explicit ticker
        # parameter is checked against the returned identity before accepting data.
        url = VANECK + '/Main/HoldingsBlock/GetContent/?' + urlencode(dict(blockid='194733', pageid='233165', ticker=ticker))
        rows.append(dict(issuer='vaneck', isin=p['ISIN'], name=p['FundName'], symbols=[ticker], url=url))
    return rows


def catalog(store, issuer):
    loaders = dict(invesco=invesco_catalog, vaneck=vaneck_catalog, vanguard=vanguard_catalog)
    return cached_json(store, 'fund-issuer-catalog-v1', issuer, 86400, loaders[issuer])


def discover(store, listing):
    """Match exact ISIN first, then exact symbol/name within an identified issuer."""
    issuer = issuer_name(listing.get('name', ''))
    order = [issuer] if issuer in ('invesco', 'vaneck', 'vanguard') else ['invesco', 'vaneck', 'vanguard']
    isin = listing.get('isin', '')
    symbol = listing['symbol'].upper()
    base = symbol.rsplit('.', 1)[0]
    unavailable = False
    for name in order:
        try:
            entries = catalog(store, name)
        except Exception:
            if len(order) == 1:
                raise
            unavailable = True
            continue
        matches = [r for r in entries if isin and r['isin'] == isin]
        if not matches and not isin and issuer == name:
            matches = [r for r in entries if any(s and (s.upper() == symbol or s.upper() == base) for s in r['symbols'])]
            if not matches:
                matches = [r for r in entries if token(r['name']) == token(listing.get('name', ''))]
            if not matches and name=='vanguard':
                def core(value):return token(re.sub(r'\b(vanguard|ucits|etf|usd|eur|gbp|accumulating|distributing|acc|dist)\b','',value,flags=re.I))
                possible=[r for r in entries if core(r['name'])==core(listing.get('name',''))]
                if len(possible)<=8:
                    for candidate in possible:
                        def load_page(candidate=candidate):return request(candidate['url'])
                        page=cached_json(store,'fund-vanguard-identity',candidate['isin'],86400*7,load_page)
                        symbols=re.findall(r'data-search-id="(?:bitk|ric)"[^>]*>([^<]+)',page,re.I)
                        if any(v.strip().upper() in (symbol,base) for v in symbols):matches.append(candidate)
        unique = {r['isin']: r for r in matches}
        if len(unique) == 1:
            return next(iter(unique.values()))
        if len(unique) > 1:
            raise ValueError('Meerdere fondsen gevonden. Controleer de ISIN-koppeling.')
    if unavailable:
        raise ValueError('Bron tijdelijk niet beschikbaar. Probeer later opnieuw.')
    raise ValueError('Geen eenduidige gratis fondsbron gevonden.')


def retrieve_invesco(url):
    result = json.loads(request(url))
    items = result.get('holdings')
    if not isinstance(items,list) or not isinstance(result.get('numberOfHoldings'),int) or not items or len(items)<result['numberOfHoldings']:
        raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
    rows = [dict(name=r.get('name') or '', isin=r.get('isin') or '', weight=str(r['weight']),
                 sector=r.get('sector') or '', country=r.get('country') or '',
                 currency=r.get('currency') or '', asset_type=r.get('assetType') or '') for r in items]
    return validate(dict(as_of=result['effectiveDate'][:10], holdings=rows))


def retrieve_vaneck(url):
    result = json.loads(request(url))['data']
    from urllib.parse import parse_qs, urlsplit
    ticker = parse_qs(urlsplit(url).query)['ticker'][0]
    if result['Ticker'] != ticker or result.get('IsTopTen'):
        raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
    items = result.get('Holdings', [])
    expected = result.get('TotalAmount')
    if expected and int(str(expected).replace(',', '')) > len(items):
        raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
    rows = [dict(name=r.get('HoldingName') or '', symbol=r.get('Label') or '', isin=r.get('ISIN') or '',
                 weight=r['Weight'], sector=r.get('Sector') or '', country=r.get('Country') or '',
                 currency=r.get('CurrencyCode') or '', asset_type=r.get('AssetClass') or '') for r in items]
    day = datetime.strptime(result['AsOfDate'], '%m/%d/%Y').date().isoformat()
    return validate(dict(as_of=day, holdings=rows))


def retrieve_vanguard(url):
    match = re.search(r'/product/etf/[^/]+/([A-Za-z0-9]+)/', url)
    if not match:
        raise ValueError('Geen eenduidige gratis fondsbron gevonden.')
    query = ('query($portIds:[String!],$lastItemKey:String){borHoldings(portIds:$portIds){'
             'holdings(limit:1500,lastItemKey:$lastItemKey){items{' + VG_FIELDS + '}totalHoldings lastItemKey}}}')
    rows, days, seen = [], set(), set()
    cursor, expected = None, None
    while True:
        result = graphql(query, dict(portIds=[match[1]], lastItemKey=cursor))['borHoldings'][0]['holdings']
        items = result['items']
        if expected is not None and expected != result['totalHoldings']:
            raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
        expected = result['totalHoldings']
        if not items or len(rows) + len(items) > MAX_ROWS:
            raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
        for r in items:
            days.add(r['effectiveDate'])
            rows.append(dict(name=r.get('issuerName') or r.get('securityLongDescription', ''),
                             symbol=r.get('ticker') or '', weight=str(r['marketValuePercentage']),
                             sector=r.get('gicsSectorDescription') or r.get('icbSectorDescription') or '',
                             country=r.get('bloombergIsoCountry') or '', asset_type=r.get('securityType') or ''))
        cursor = result.get('lastItemKey')
        if not cursor:
            if len(rows) != result['totalHoldings'] or len(days) != 1:
                raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
            break
        if cursor in seen:
            raise ValueError('De fondsaanbieder leverde geen volledige samenstelling.')
        seen.add(cursor)
    return validate(dict(as_of=next(iter(days))[:10], holdings=rows))
