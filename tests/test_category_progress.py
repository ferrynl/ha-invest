import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store,now
from instruments import category_overview,save_categories
from profiles import enrich_categories
import test_transactions as transaction_test_support

class CategoryOverviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  with self.store.connect() as db:
   records=[('ISRG','NASDAQ','USD'),('SMGB.L','LONDON','GBP')]+[('BENCH'+str(i),'NASDAQ','USD') for i in range(123)]
   db.executemany('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES(?,?,?,?,?,?,?,?)',[(symbol,market,symbol,'1','100',currency,'2026-10-01',now()) for symbol,market,currency in records])
 def test_125_positions_show_fresh_completed_partial_and_pending_without_history_or_api(self):
  def payload(symbol):return {'quoteSummary':{'result':[{'price':dict(symbol=symbol,exchange='NMS' if symbol=='ISRG' else 'LSE',currency='USD' if symbol=='ISRG' else 'GBP',quoteType='EQUITY' if symbol=='ISRG' else 'ETF'),'assetProfile':dict(sector='Healthcare',country='United States') if symbol=='ISRG' else {}}]}}
  with patch('profiles._download_profile',side_effect=payload):
   enrich_categories(self.store,('ISRG','NASDAQ','USD'));enrich_categories(self.store,('SMGB.L','LONDON','GBP'))
  with patch.object(self.store,'state',side_effect=AssertionError('No financial history rebuild')),patch('profiles._download_profile',side_effect=AssertionError('No external provider')):
   result=category_overview(self.store)
  self.assertEqual(result['counts'],dict(total=125,processed=2,complete=1,partial=1,pending=123,fetching=0,retry=0))
  items={r['symbol']:r for r in result['entries']}
  self.assertEqual(items['ISRG']['categories']['sector'],'Gezondheidszorg');self.assertEqual(items['ISRG']['sync']['status'],'complete')
  self.assertEqual(items['SMGB.L']['categories']['asset_type'],'ETF');self.assertEqual(items['SMGB.L']['sync']['status'],'partial');self.assertEqual(items['SMGB.L']['categories']['country'],'')
  self.assertEqual(items['BENCH0']['sync']['status'],'pending')
 def test_accounts_are_scoped_and_shared_listings_are_counted_once(self):
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
  self.store.add(dict(symbol='ISRG',exchange='NASDAQ',currency='USD',name='ISRG',account_id=2,quantity='1',price='100',purchased_on='2026-10-01'))
  self.assertEqual(category_overview(self.store)['counts']['total'],125)
  result=category_overview(self.store,'2');self.assertEqual(result['counts']['total'],1);self.assertEqual(result['entries'][0]['symbol'],'ISRG');self.assertEqual(result['account_id'],'2')
  with self.assertRaises(ValueError):category_overview(self.store,'999')

class CategoryOverviewHttpTests(unittest.TestCase):
 setUp=transaction_test_support.TransactionHttpTests.setUp
 tearDown=transaction_test_support.TransactionHttpTests.tearDown
 def get(self,path,token='',etag=None):
  connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
  try:
   headers={'Cookie':'homeinvest_session='+token}
   if etag:headers['If-None-Match']=etag
   connection.request('GET',path,headers=headers);response=connection.getresponse();raw=response.read()
   return response.status,json.loads(raw) if raw else None,dict(response.getheaders())
  finally:connection.close()
 def test_metadata_bypasses_old_financial_cache_and_etag_changes_when_saved(self):
  self.cache.get(self.store.state)
  with patch('profiles._download_profile',return_value={'quoteSummary':{'result':[{'price':dict(symbol='ASML.AS',exchange='AMS',currency='EUR',quoteType='EQUITY'),'assetProfile':dict(sector='Technology',country='Netherlands')}]}}):enrich_categories(self.store,('ASML.AS','AMSTERDAM','EUR'))
  path='/api/instruments/categories?account_id=all'
  with patch.object(self.store,'state',side_effect=AssertionError('Must not rebuild histories')),patch('profiles._download_profile',side_effect=AssertionError('Must not call provider')):
   code,result,headers=self.get(path)
   self.assertEqual(code,200);self.assertEqual(result['entries'][0]['categories']['sector'],'Technologie');self.assertEqual(headers['Cache-Control'],'no-store')
   self.assertEqual(self.get(path,etag=headers['ETag'])[0],304)
   self.assertEqual(self.get('/api/state')[1]['positions'][0]['categories'],{})
   save_categories(self.store,dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',sector='Mijn sector'))
   code,result,new_headers=self.get(path,etag=headers['ETag']);self.assertEqual(code,200);self.assertNotEqual(headers['ETag'],new_headers['ETag']);self.assertEqual(result['entries'][0]['categories']['sector'],'Mijn sector')
 def test_metadata_requires_login_and_is_available_to_basic_users(self):
  self.auth.enable('owner','Long-test-password-2026')
  path='/api/instruments/categories?account_id=all';self.assertEqual(self.get(path)[0],401)
  self.auth.save_user(dict(username='viewer',password='Long-test-password-2026',role='basic'))
  token=self.auth.login('viewer','Long-test-password-2026','test')
  self.assertEqual(self.get(path,token)[0],200);self.assertEqual(self.get('/api/instruments/categories?account_id=999',token)[0],400)
 def test_saved_categories_are_visible_while_next_profile_is_still_running(self):
  import server
  self.store.add(dict(symbol='IBM',exchange='NYSE',currency='USD',name='IBM',quantity='1',price='100',purchased_on='2026-10-01'))
  self.cache.get(self.store.state);waiting=threading.Event();release=threading.Event();finished=threading.Event()
  real_enrich=enrich_categories
  def enrich(store,key):
   if key[0]=='IBM':waiting.set();release.wait(5);return False
   return real_enrich(store,key)
  def run():
   try:server.refresh()
   finally:finished.set()
  with patch.object(server,'store',self.store),patch.object(server,'state_cache',self.cache),patch.object(server,'enrich_categories',side_effect=enrich),patch.object(server,'fetch_quote',return_value=('120','2026-10-22T10:00:00+00:00')),patch.object(server,'fetch_history',return_value=[dict(day='2026-10-01',price='100')]),patch('server.time.sleep'),patch('profiles._download_profile',return_value={'quoteSummary':{'result':[{'price':dict(symbol='ASML.AS',exchange='AMS',currency='EUR',quoteType='EQUITY'),'assetProfile':dict(sector='Technology',country='Netherlands')}]}}):
   worker=threading.Thread(target=run,daemon=True);worker.start()
   try:
    self.assertTrue(waiting.wait(3));self.assertFalse(finished.is_set())
    code,result,_=self.get('/api/instruments/categories?account_id=all');self.assertEqual(code,200)
    self.assertEqual(next(r for r in result['entries'] if r['symbol']=='ASML.AS')['categories']['sector'],'Technologie')
    self.assertFalse(finished.is_set());self.assertEqual(next(r for r in self.cache.get(self.store.state)['positions'] if r['symbol']=='ASML.AS')['categories']['sector'],'Technologie')
   finally:release.set();worker.join(5)
  self.assertFalse(worker.is_alive())
