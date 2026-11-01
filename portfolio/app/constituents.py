"""Read-only constituent pages, authorized through the actual owned parent fund."""
import re
from instruments import owned_key
from fund_holdings import saved
from persistent_cache import cached_json


def details(store, data, account='all'):
    parent = owned_key(store, data, account)
    fund = saved(store, parent)
    index = int(data.get('holding', '-1'))
    if not fund or not 0 <= index < len(fund['holdings']):
        raise ValueError('Onderliggende belegging niet gevonden.')
    if data.get('as_of') != fund['as_of']:
        raise ValueError('De ETF-samenstelling is gewijzigd. Open de belegging opnieuw vanuit de ETF.')
    holding = fund['holdings'][index]
    if any(data.get('holding_'+field, '') != holding[field] for field in ('name','isin','symbol')):
        raise ValueError('De ETF-samenstelling is gewijzigd. Open de belegging opnieuw vanuit de ETF.')
    with store.read() as db:
        row = db.execute('SELECT name FROM purchases WHERE symbol=? AND exchange=? AND currency=? LIMIT 1', parent).fetchone()
    return dict(holding=holding, parent=dict(zip(('symbol','exchange','currency'), parent)),
                parent_name=row['name'] if row else parent[0], as_of=fund['as_of'], source_url=fund['source_url'])


def name_key(name):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\b(inc|incorporated|corp|corporation|ltd|limited|plc|sa|nv|ag)\b', '', name.lower()))


def company(store, data, account='all'):
    holding = details(store, data, account)['holding']
    def load():
        from provider import search_stocks
        from profiles import fetch_company
        isin = holding['isin']
        with store.read() as db:
            mappings = db.execute("SELECT DISTINCT symbol,exchange,currency FROM instrument_mappings WHERE isin=? AND symbol<>''", (isin,)).fetchall() if isin else []
        if len(mappings) == 1:
            return fetch_company(store, tuple(mappings[0]))
        # Symbols alone are not globally unique. Only use exact names returned
        # by the search service; never guess a market from an ETF's venue.
        choices = search_stocks(isin or holding['name'][:80], store=store)
        choices = [r for r in choices if name_key(r['name']) == name_key(holding['name'])]
        if not choices and isin:
            choices = [r for r in search_stocks(holding['name'][:80], store=store) if name_key(r['name']) == name_key(holding['name'])]
        markets = {'US':('NASDAQ','NYSE','AMEX','NYSEARCA'), 'NL':('AMSTERDAM',), 'GB':('LONDON',), 'DE':('XETRA','FRANKFURT'),
                   'FR':('PARIS',), 'BE':('BRUSSELS',), 'CH':('SWISS',), 'ES':('MADRID',), 'IT':('MILAN',), 'JP':('TOKYO',),
                   'CA':('TORONTO',), 'AU':('ASX',), 'HK':('HONG KONG',), 'DK':('COPENHAGEN',), 'SE':('STOCKHOLM',)}
        from profiles import COUNTRIES
        aliases = {name_key(name):code for name,code in [('United States','US'),('Netherlands','NL'),('United Kingdom','GB'),('Germany','DE'),('France','FR'),('Belgium','BE'),('Switzerland','CH'),('Spain','ES'),('Italy','IT'),('Japan','JP'),('Canada','CA'),('Australia','AU'),('Hong Kong','HK'),('Denmark','DK'),('Sweden','SE')]}
        aliases.update({name_key(COUNTRIES.get(name,name)):code for name,code in [('United States','US'),('Netherlands','NL'),('United Kingdom','GB'),('Germany','DE'),('France','FR'),('Switzerland','CH')]})
        country=holding['country'].upper()
        country=country if country in markets else aliases.get(name_key(holding['country']))
        choices=[r for r in choices if r['exchange'] in markets.get(country, ()) and (not holding['currency'] or r['currency']==holding['currency'])]
        exact=[r for r in choices if r['symbol']==holding['symbol']]
        choices=exact or choices
        if len(choices)!=1:
            return dict(description='', domain='')
        return fetch_company(store, tuple(choices[0][k] for k in ('symbol','exchange','currency')))
    identity = holding['isin'] or '|'.join((holding['name'], holding['symbol'], holding['country']))
    def safe_load():
        try:return load()
        except Exception as error:
            from diagnostics import record
            record(store,'WARNING','market','constituent_company_failed','Bedrijfsinformatie ophalen mislukt.',{'error_type':type(error).__name__})
            return dict(description='',domain='',unavailable=True)
    return cached_json(store, 'fund-constituent-company-v1', identity, 900, safe_load)
