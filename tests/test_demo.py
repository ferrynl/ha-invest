import sys,tempfile,unittest,http.client,json,threading,gzip
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from demo import ensure_demo
from storage import Store
from home_euro import overview
from cache import StateCache
from security import Auth
from web import make_handler
from http.server import ThreadingHTTPServer

class DemoTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.store=ensure_demo(Path(cls.tmp.name)/'demo');cls.snapshot=cls.store.state()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_ten_brokers_150_distinct_stocks_ten_currencies_and_target_value(self):
  snapshot=self.snapshot
  self.assertEqual(len(snapshot['accounts']),10);self.assertEqual(len(snapshot['positions']),150)
  self.assertEqual(len({(p['symbol'],p['exchange'],p['currency']) for p in snapshot['positions']}),150)
  self.assertEqual(len({p['currency'] for p in snapshot['positions']}),10)
  with patch('forex.load_json',side_effect=AssertionError('No live prices')):
   total=overview(self.store,snapshot,fetch_rates=False)
  self.assertEqual(total['excluded'],[])
  self.assertLess(abs(sum(Decimal(p['value']) for p in total['positions'])-150000),Decimal('.01'))
  self.assertGreater(len(snapshot['dividends']),1000)
 def test_reopening_is_idempotent_and_does_not_touch_a_personal_database(self):
  personal=Store(Path(self.tmp.name)/'personal');personal.add(dict(symbol='OWN',exchange='TEST',currency='EUR',name='Own',quantity='1',price='50',purchased_on=date.today().isoformat()))
  before=personal.state();again=ensure_demo(self.store.root)
  self.assertEqual(len(again.state()['positions']),150);self.assertEqual(personal.state(),before)
  self.assertNotEqual(personal.path,again.path)
 def test_seed_refuses_to_replace_unknown_data(self):
  unknown=Store(Path(self.tmp.name)/'unknown');unknown.add(dict(symbol='OWN',exchange='TEST',currency='EUR',name='Own',quantity='1',price='50',purchased_on=date.today().isoformat()))
  with self.assertRaises(ValueError):ensure_demo(unknown.root)
  self.assertEqual(len(unknown.state()['positions']),1)

class DemoHttpTests(unittest.TestCase):
 def test_profile_is_authenticated_offline_read_only_and_isolated(self):
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);auth=Auth(store);store.add(dict(symbol='OWN',exchange='TEST',currency='EUR',name='Own',quantity='1',price='50',purchased_on=date.today().isoformat()))
   auth.enable('owner','Long-test-password-2026');token=auth.login('owner','Long-test-password-2026','test')
   server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(store,auth,StateCache(),{},900,threading.Lock(),threading.Event()))
   worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
   def request(path,profile='demo',cookie=token,method='GET'):
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=40)
    try:
     connection.request(method,path,body='{}' if method=='POST' else None,headers={'X-HomeInvest-Profile':profile,'Cookie':'homeinvest_session='+cookie,'Content-Type':'application/json','X-Portfolio-Request':'1','Accept-Encoding':'gzip'})
     result=connection.getresponse();body=result.read();body=gzip.decompress(body) if result.getheader('Content-Encoding')=='gzip' else body;return result.status,json.loads(body)
    finally:connection.close()
   try:
    self.assertEqual(request('/api/state',cookie='')[0],401)
    with patch('forex.load_json',side_effect=AssertionError('No network')),patch('profiles.fetch_company',side_effect=AssertionError('No company provider')):
     status,data=request('/api/state?compact=1');self.assertEqual(status,200);self.assertEqual(len(data['positions']),150);self.assertEqual(len(data['accounts']),10)
     self.assertEqual(request('/api/instrument/company?symbol=ASML')[0],200)
     self.assertEqual(request('/api/fx')[0],200)
     self.assertEqual(request('/api/reports/combined')[0],200)
    for path in ['/api/purchases','/api/restore','/api/auth/disable','/api/portfolio/delete']:
     self.assertEqual(request(path,method='POST')[0],403)
    self.assertEqual(request('/api/backup')[0],403);self.assertEqual(request('/api/users')[0],403)
    status,own=request('/api/state?compact=1',profile='personal');self.assertEqual(status,200);self.assertEqual([p['symbol'] for p in own['positions']],['OWN'])
    self.assertEqual(request('/api/state',profile='../../other')[0],400)
    self.assertEqual(len(store.state()['purchases']),1);self.assertTrue((Path(folder)/'demo'/'portfolio.sqlite3').exists())
   finally:server.shutdown();server.server_close();worker.join()

import test_transactions as compression_support
class ProfileResponseTests(unittest.TestCase):
 setUp=compression_support.TransactionHttpTests.setUp
 tearDown=compression_support.TransactionHttpTests.tearDown
 def test_compressed_assets_and_financial_views_keep_correct_cache_and_auth_headers(self):
  import gzip
  def fetch(path,headers):
   connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
   try:
    connection.request('GET',path,headers=headers);response=connection.getresponse();return response.status,dict(response.getheaders()),response.read()
   finally:connection.close()
  status,headers,body=fetch('/translations.js',{'Accept-Encoding':'gzip'})
  self.assertEqual(status,200);self.assertEqual(headers.get('Content-Encoding'),'gzip');self.assertIn(b'const UI_TRANSLATIONS',gzip.decompress(body));self.assertEqual(headers.get('Vary'),'Accept-Encoding')
  self.assertEqual(fetch('/translations.js',{'Accept-Encoding':'gzip','If-None-Match':headers['ETag']})[0],304)
  status,headers,body=fetch('/api/state?compact=1',{'Accept-Encoding':'gzip'})
  self.assertEqual(status,200);self.assertEqual(headers.get('Cache-Control'),'no-store');self.assertTrue(json.loads(gzip.decompress(body))['compact'])
  status,headers,body=fetch('/api/session',{'Accept-Encoding':'gzip'})
  self.assertEqual(status,200);self.assertNotIn('Content-Encoding',headers);self.assertEqual(headers.get('Cache-Control'),'no-store')
