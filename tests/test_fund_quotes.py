import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
import fund_quotes
from storage import Store
from valuations import save

STAMP='2026-10-30T10:00:00+00:00'
def html(price=111.2923,isin=fund_quotes.ISIN,currency='EUR',key_isin=fund_quotes.ISIN):
 payload={'queries':[{'queryKey':['/symbols',{'isin':key_isin,'quoteCurrency':'EUR'}],'state':{'data':{'isin':isin,'currency':currency,'price':price}}}]}
 return '<script>window.data=JSON.parse('+json.dumps(json.dumps(payload))+');</script>'

class ApolloQuoteTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.stock=dict(symbol=fund_quotes.ISIN,exchange='PRIVATE',currency='EUR',name='Apollo')
  self.store.add(dict(**self.stock,quantity='2',price='100',purchased_on='2026-10-01'))
 def test_exact_isin_currency_and_unknown_nav_date(self):
  result=fund_quotes.parse_quote(html(),STAMP)
  self.assertEqual(result['price'],'111.2923');self.assertEqual(result['observed_at'],STAMP)
  self.assertIsNone(result['price_date'])
  for document in (html(isin='LU3176111881'),html(key_isin='LU3176111881'),html(currency='USD'),html(price=None),html(price='NaN'),html(price=-1),'<html>111.29</html>'):
   with self.subTest(document=document),self.assertRaises(ValueError):fund_quotes.parse_quote(document,STAMP)
 def test_success_is_cached_and_failed_pages_are_not(self):
  with patch('fund_quotes.urlopen',return_value=io.BytesIO(html().encode())) as request:
   first=fund_quotes.fetch_quote(self.store);second=fund_quotes.fetch_quote(self.store)
  self.assertEqual(first,second);self.assertEqual(request.call_count,1)
  with self.store.connect() as db:db.execute('DELETE FROM api_cache')
  with patch('fund_quotes.urlopen',return_value=io.BytesIO(b'<html>Error</html>')),self.assertRaises(ValueError):fund_quotes.fetch_quote(self.store)
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM api_cache WHERE namespace='divvydiary-fund-v1'").fetchone()[0],0)
 def test_automatic_supported_only_for_this_private_share_class(self):
  save(self.store,{**self.stock,'automatic':True})
  with self.assertRaises(ValueError):save(self.store,{**self.stock,'symbol':'OTHER','automatic':True})
 def test_background_refresh_preserves_manual_override_and_previous_quote_on_failure(self):
  with patch.dict(os.environ,{'DATA_DIR':self.tmp.name}):
   import server
  from cache import StateCache
  with patch.object(server,'store',self.store),patch.object(server,'state_cache',StateCache(store=self.store)),patch.object(server,'enrich_categories',return_value=False):
   with patch('fund_quotes.fetch_quote',return_value=fund_quotes.parse_quote(html(),STAMP)):
    server.refresh()
   quote=self.store.state()['positions'][0]['quote'];self.assertEqual(quote['price'],'111.2923');self.assertIn('DivvyDiary',quote['source'])
   with patch('fund_quotes.fetch_quote',side_effect=ValueError('unavailable')):server.refresh()
   self.assertEqual(self.store.state()['positions'][0]['quote']['quoted_at'],STAMP)
   save(self.store,{**self.stock,'automatic':False,'price':'105.21','day':'2026-09-30'})
   with patch('fund_quotes.fetch_quote',side_effect=AssertionError('manual override wins')) as fetch:server.refresh();fetch.assert_not_called()
   self.assertEqual(self.store.state()['positions'][0]['quote']['price'],'105.21')
