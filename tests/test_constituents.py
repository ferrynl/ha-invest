import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from fund_holdings import save
import constituents

PARENT=dict(symbol='TEST.DE',exchange='XETRA',currency='EUR')
ROW=dict(name='MICROSOFT CORP',symbol='MSFT',isin='US5949181045',weight='100',country='US',sector='Technology',asset_type='Equity',currency='USD')
QUERY=dict(**PARENT,holding='0',as_of='2026-10-30',holding_name=ROW['name'],holding_isin=ROW['isin'],holding_symbol=ROW['symbol'])

class ConstituentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.store.add(dict(**PARENT,name='Example ETF',quantity='1',price='100',purchased_on='2026-10-01'))
        save(self.store,tuple(PARENT.values()),dict(as_of='2026-10-30',holdings=[ROW]))

    def test_page_is_read_only_and_shows_actual_parent_and_weight(self):
        before=self.store.state()
        result=constituents.details(self.store,QUERY)
        self.assertEqual(result['holding']['weight'],'100');self.assertEqual(result['parent'],PARENT)
        self.assertEqual(self.store.state()['purchases'],before['purchases'])
        self.assertEqual(len(self.store.state()['positions']),1)

    def test_foreign_parent_wrong_index_and_stale_identity_are_rejected(self):
        for changes in [dict(symbol='OTHER'),dict(holding='-1'),dict(holding='1'),dict(as_of='2026-10-29'),dict(holding_name='Other'),dict(holding_isin=''),dict(holding_symbol='WRONG')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):constituents.details(self.store,{**QUERY,**changes})

    def test_company_uses_exact_name_market_and_currency_and_caches(self):
        listing=dict(symbol='MSFT',exchange='NASDAQ',currency='USD',name='Microsoft Corporation')
        with patch('provider.search_stocks',return_value=[listing]) as search,patch('profiles.fetch_company',return_value=dict(description='Software company.',domain='microsoft.com')) as profile:
            result=constituents.company(self.store,QUERY);self.assertEqual(result['domain'],'microsoft.com')
            self.assertEqual(constituents.company(self.store,QUERY),result);search.assert_called_once();profile.assert_called_once_with(self.store,('MSFT','NASDAQ','USD'))

    def test_unowned_parent_never_requests_company(self):
        with patch('provider.search_stocks') as search:
            with self.assertRaises(ValueError):constituents.company(self.store,{**QUERY,'symbol':'OTHER'})
            search.assert_not_called()

    def test_same_ticker_different_company_market_or_currency_is_not_guessed(self):
        for name,market,currency in [('Other Company','NASDAQ','USD'),('Microsoft Corporation','XETRA','USD'),('Microsoft Corporation','NASDAQ','EUR')]:
            with self.store.connect() as db:db.execute("DELETE FROM api_cache WHERE namespace='fund-constituent-company-v1'")
            with patch('provider.search_stocks',return_value=[dict(symbol='MSFT',name=name,exchange=market,currency=currency)]),patch('profiles.fetch_company') as profile:
                self.assertFalse(constituents.company(self.store,QUERY)['domain']);profile.assert_not_called()

    def test_broker_scope_is_checked_before_constituent_read(self):
        self.store.add_account(dict(name='Other broker',broker='Other'))
        account=self.store.state()['accounts'][-1]['id']
        with self.assertRaises(ValueError):constituents.details(self.store,QUERY,account)


import test_transactions as support
class ConstituentHttpTests(unittest.TestCase):
    setUp=support.TransactionHttpTests.setUp
    tearDown=support.TransactionHttpTests.tearDown
    request=support.TransactionHttpTests.request

    def test_parent_authorization_and_snapshot_identity_apply_to_http(self):
        identity=dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR')
        save(self.store,tuple(identity.values()),dict(as_of='2026-10-30',holdings=[ROW]))
        query={**QUERY,**identity}
        self.assertEqual(self.request('/api/fund/constituent?'+urlencode(query))[0],200)
        with patch('provider.search_stocks') as search:
            self.assertEqual(self.request('/api/fund/constituent/company?'+urlencode({**query,'symbol':'OTHER'}))[0],400);search.assert_not_called()
