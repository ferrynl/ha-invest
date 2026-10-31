import json
import sys
import tempfile
import time
import unittest
import threading
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
import fundamentals
import instruments
from storage import Store

KEY=('AAPL','NASDAQ','USD')
ROWS=[('2025-09-30','total_revenue','1000'),('2025-09-30','net_income','125'),('2025-09-30','free_cash_flow','0'),('2024-09-30','net_income','-20')]

class FundamentalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)

    def test_exact_listing_gate_never_calls_provider_for_europe_or_funds(self):
        with patch.object(fundamentals,'load') as load:
            for key in [('AAPL','FRANKFURT','EUR'),('AAPL','NASDAQ','EUR'),('ASML.AS','AMSTERDAM','EUR'),('LU3170240538','PRIVATE','EUR'),('AAPL;DROP','NASDAQ','USD')]:
                self.assertEqual(fundamentals.fetch(self.store,key)['status'],'unsupported')
            load.assert_not_called()

    def test_years_are_not_mixed_zero_losses_and_reporting_currency_survive(self):
        periods=fundamentals.normalize(ROWS,'EUR')
        self.assertEqual(periods[0],dict(day='2025-09-30',currency='EUR',revenue='1000',net_income='125',free_cash_flow='0',operating_cash_flow=None,net_margin='12.500'))
        self.assertIsNone(periods[1]['revenue']);self.assertIsNone(periods[1]['net_margin'])
        self.assertEqual(periods[1]['net_income'],'-20')
        self.assertEqual(len(fundamentals.normalize([(f'{year}-09-30','total_revenue','1') for year in range(2010,2026)],'USD')),4)

    def test_catalog_currency_and_source_update_date_are_returned(self):
        with patch.object(fundamentals,'read_json',side_effect=[{'0':dict(ticker='AAPL',title='Apple',financial_currency='EUR')},{'files':{'US/stock_statement.parquet':'2026-10-31T04:59:08Z'}}]),patch.object(fundamentals,'query_rows',return_value=ROWS):
            result=fundamentals.load('AAPL')
        self.assertEqual(result['currency'],'EUR');self.assertEqual(result['periods'][0]['currency'],'EUR')
        self.assertEqual(result['dataset_updated_at'],'2026-10-31T04:59:08Z')

    def test_unknown_symbol_and_missing_reporting_currency_are_not_guessed(self):
        with patch.object(fundamentals,'read_json',return_value={'0':dict(ticker='MSFT')}),patch.object(fundamentals,'query_rows') as query:
            self.assertEqual(fundamentals.load('AAPL')['status'],'no_data');query.assert_not_called()
        with patch.object(fundamentals,'read_json',return_value={'0':dict(ticker='AAPL')}):
            with self.assertRaises(ValueError):fundamentals.load('AAPL')

    def test_success_cache_survives_restart_failure_keeps_previous_and_backs_off(self):
        result=dict(status='ok',periods=fundamentals.normalize(ROWS,'USD'),source=fundamentals.SOURCE)
        with patch.object(fundamentals,'load',return_value=result) as load:
            self.assertEqual(fundamentals.fetch(self.store,KEY),result)
            self.assertEqual(fundamentals.fetch(Store(self.tmp.name),KEY),result);self.assertEqual(load.call_count,1)
        with self.store.connect() as db:db.execute('UPDATE api_cache SET expires_at=0')
        with patch.object(fundamentals,'load',side_effect=RuntimeError('private transport detail')) as load:
            stale=fundamentals.fetch(self.store,KEY);self.assertTrue(stale['stale']);self.assertEqual(stale['periods'],result['periods'])
            fundamentals.fetch(self.store,KEY);self.assertEqual(load.call_count,1)
        with self.store.read() as db:
            self.assertNotIn('private transport detail',str([dict(row) for row in db.execute('SELECT * FROM api_cache')]))

    def test_initial_failure_and_busy_reader_return_available_status_without_wait(self):
        with patch.object(fundamentals,'load',side_effect=TimeoutError):
            self.assertEqual(fundamentals.fetch(self.store,KEY)['status'],'unavailable')
        with fundamentals._query_lock,patch.object(fundamentals,'load') as load:
            self.assertEqual(fundamentals.fetch(self.store,('MSFT','NASDAQ','USD'))['status'],'unavailable');load.assert_not_called()

    def test_ownership_checked_before_external_call_and_cache_is_shared_only_by_listing(self):
        stock=dict(symbol='AAPL',exchange='NASDAQ',currency='USD',name='Apple',quantity='1',price='100',purchased_on='2026-10-01')
        self.store.add(stock);self.store.add_account(dict(name='Other',broker='Revolut'))
        with patch.object(fundamentals,'fetch',return_value={'status':'ok'}) as fetch:
            self.assertEqual(instruments.fundamentals(self.store,stock,'1'),{'status':'ok'})
            fetch.assert_called_once_with(self.store,KEY)
            with self.assertRaises(ValueError):instruments.fundamentals(self.store,stock,'2')
            with self.assertRaises(ValueError):instruments.fundamentals(self.store,dict(symbol='MSFT',exchange='NASDAQ',currency='USD'))
            self.assertEqual(fetch.call_count,1)

    def test_http_endpoint_requires_session_allows_basic_and_rejects_unknown_listing(self):
        from security import Auth
        from cache import StateCache
        from web import make_handler
        from http.server import ThreadingHTTPServer
        self.store.add(dict(symbol='AAPL',exchange='NASDAQ',currency='USD',name='Apple',quantity='1',price='100',purchased_on='2026-10-01'))
        auth=Auth(self.store);password='Long-test-password-2026'
        auth.enable('owner',password);auth.save_user(dict(username='viewer',password=password,role='basic'))
        token=auth.login('viewer',password,'test')
        handler=make_handler(self.store,auth,StateCache(),{},900,threading.Lock(),threading.Event(),enable_demo=False)
        http=ThreadingHTTPServer(('127.0.0.1',0),handler);worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
        def request(symbol='AAPL',cookie=''):
            conn=HTTPConnection('127.0.0.1',http.server_port,timeout=5)
            try:
                conn.request('GET',f'/api/instrument/fundamentals?symbol={symbol}&exchange=NASDAQ&currency=USD',headers={'Cookie':'homeinvest_session='+cookie})
                response=conn.getresponse();return response.status,json.loads(response.read()),response.getheader('Cache-Control')
            finally:conn.close()
        try:
            with patch.object(fundamentals,'fetch',return_value=dict(status='ok',periods=[])) as fetch:
                self.assertEqual(request()[0],401);fetch.assert_not_called()
                code,data,control=request(cookie=token);self.assertEqual(code,200);self.assertEqual(data['status'],'ok');self.assertEqual(control,'no-store')
                self.assertEqual(request('MSFT',token)[0],400);self.assertEqual(fetch.call_count,1)
        finally:http.shutdown();http.server_close();worker.join()

    def test_details_expose_eligibility_by_listing_not_company_country(self):
        for symbol,exchange,currency,eligible in [('AAPL','NASDAQ','USD',True),('ASML','NASDAQ','USD',True),('ASML.AS','AMSTERDAM','EUR',False),('AAPL','FRANKFURT','EUR',False),('AAPL','NASDAQ','EUR',False)]:
            stock=dict(symbol=symbol,exchange=exchange,currency=currency,name=symbol,quantity='1',price='100',purchased_on='2026-10-01')
            self.store.add(stock)
            with patch.object(fundamentals,'load') as load:
                result=instruments.details(self.store,stock)
                self.assertEqual(result['fundamentals_supported'],eligible)
                load.assert_not_called()

if __name__=='__main__':unittest.main()
