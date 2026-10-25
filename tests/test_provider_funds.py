import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
import provider
import test_transactions as support

FUND={'symbol':'0P0001IV37.F','exchange':'FRANKFURT','currency':'EUR','name':'Hybrid Index Fund NL-I'}
SEARCH={'quotes':[{'symbol':FUND['symbol'],'exchange':'FRA','quoteType':'MUTUALFUND','longname':FUND['name']}]}
META={'symbol':FUND['symbol'],'exchangeName':'FRA','currency':'EUR','instrumentType':'MUTUALFUND','longName':FUND['name'],'regularMarketPrice':97.84,'regularMarketTime':1792612800}
CHART={'chart':{'result':[{'meta':META,'timestamp':[1792526400,1792612800],'indicators':{'quote':[{'close':[97.85,97.84]}]}}]}}

class FundProviderTests(unittest.TestCase):
    def setUp(self):provider._search_stocks.cache_clear()
    def tearDown(self):provider._search_stocks.cache_clear()

    def test_bare_fund_code_returns_full_supported_listing(self):
        quotes=SEARCH['quotes']*2+[
            {'symbol':'UNSUPPORTED','exchange':'UNKNOWN','quoteType':'MUTUALFUND'},
            {'symbol':'^INDEX','exchange':'FRA','quoteType':'INDEX'},
            {'symbol':'COIN','exchange':'FRA','quoteType':'CRYPTOCURRENCY'}]
        with patch('provider._payload',return_value={'quotes':quotes}):
            self.assertEqual(provider.search_stocks('0P0001IV37'),[FUND])

    def test_fund_listing_quote_and_history_keep_currency_guards(self):
        with patch('provider._payload',return_value=CHART):
            self.assertEqual(provider.listing(FUND['symbol']),FUND)
            self.assertEqual(provider.fetch_quote('',FUND['symbol'],FUND['exchange'],'EUR')[0],97.84)
            self.assertEqual([row['price'] for row in provider.fetch_history(FUND['symbol'],FUND['exchange'],'EUR','2026-10-01')],['97.85','97.84'])
            with self.assertRaises(ValueError):provider.fetch_quote('',FUND['symbol'],FUND['exchange'],'USD')
            with self.assertRaises(ValueError):provider.fetch_history(FUND['symbol'],'NASDAQ','EUR','2026-10-01')

class FundHttpTests(unittest.TestCase):
    setUp=support.TransactionHttpTests.setUp
    tearDown=support.TransactionHttpTests.tearDown
    request=support.TransactionHttpTests.request

    def test_search_select_and_add_fund_without_ticker_special_case(self):
        provider._search_stocks.cache_clear()
        self.addCleanup(provider._search_stocks.cache_clear)
        def payload(request,timeout,store,namespace,key,ttl):
            return SEARCH if namespace=='yahoo-search-v4' else CHART
        with patch('provider._payload',side_effect=payload):
            code,result=self.request('/api/search?q=0P0001IV37')
            self.assertEqual(code,200);self.assertEqual(result['results'],[FUND])
            code,listing=self.request('/api/listing?symbol='+result['results'][0]['symbol'])
            self.assertEqual(code,200);self.assertEqual(listing,FUND)
            self.assertEqual(self.request('/api/purchases',{**listing,'quantity':'2','price':'95','purchased_on':'2026-10-01'})[0],201)
        position=next(p for p in self.store.state()['positions'] if p['symbol']==FUND['symbol'])
        self.assertEqual(position['exchange'],'FRANKFURT');self.assertEqual(position['currency'],'EUR')
        self.assertEqual(position['quantity'],'2');self.assertEqual(position['cost'],'190')
