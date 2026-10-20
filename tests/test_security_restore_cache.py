import sys
import tempfile
import unittest
import sqlite3
import json
import http.client
import threading
from pathlib import Path
from contextlib import closing
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from security import Auth,verify_password
from cache import StateCache
from restore import restore_backup
from web import make_handler
from http.server import ThreadingHTTPServer

class AccessTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.store=Store(self.temp.name);self.auth=Auth(self.store);self.cache=StateCache()
  self.password='Long-test-password-2026'
  handler=make_handler(self.store,self.auth,self.cache,{},900,threading.Lock(),threading.Event())
  self.http=ThreadingHTTPServer(('127.0.0.1',0),handler)
  self.worker=threading.Thread(target=self.http.serve_forever,daemon=True);self.worker.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.worker.join()
 def request(self,method,path,data=None,token='',csrf=None,extra=None):
  headers={'Content-Type':'application/json','X-Portfolio-Request':'1'}
  if token:headers['Cookie']='homeinvest_session='+token
  if csrf:headers['X-CSRF-Token']=csrf
  headers.update(extra or {})
  body=data if isinstance(data,bytes) else json.dumps(data).encode() if data is not None else None
  connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=20)
  try:
   connection.request(method,path,body,headers);r=connection.getresponse();return r.status,r.read(),dict(r.getheaders())
  finally:connection.close()
 def activate(self):
  code,_,headers=self.request('POST','/api/auth/enable',{'username':'owner','password':self.password})
  self.assertEqual(code,200)
  cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
  token=cookie.split(';')[0].split('=',1)[1]
  return token,self.auth.user(token)['csrf']
 def test_logs_are_admin_only_with_filters_and_safe_export(self):
  from diagnostics import record
  self.assertEqual(self.request('GET','/api/logs')[0],403)
  token,csrf=self.activate()
  reference=record(self.store,'ERROR','trading212','http_error','Test fout',{'http_status':400})
  code,body,headers=self.request('GET','/api/logs?level=ERROR&q='+reference,token=token)
  self.assertEqual(code,200);self.assertEqual(json.loads(body)['entries'][0]['reference'],reference);self.assertEqual(headers['Cache-Control'],'no-store')
  code,body,headers=self.request('GET','/api/logs?download=1',token=token)
  self.assertEqual(code,200);self.assertIn('home-invest-logs.json',headers['Content-Disposition'])
  self.assertEqual(self.request('GET','/api/logs?before=bad',token=token)[0],400)
  self.assertEqual(self.request('GET','/api/logs?level=bad',token=token)[0],400)
  self.auth.save_user({'username':'viewer','password':self.password,'role':'basic'})
  basic=self.auth.login('viewer',self.password,'test')
  self.assertEqual(self.request('GET','/api/logs',token=basic)[0],403)
  self.assertEqual(self.request('GET','/api/logs?download=1',token=basic)[0],403)
 def test_mapping_registry_is_admin_only_and_csrf_protected(self):
  admin,csrf=self.activate()
  self.auth.save_user({'username':'mappingviewer','password':self.password,'role':'basic'})
  basic=self.auth.login('mappingviewer',self.password,'test')
  self.assertEqual(self.request('GET','/api/imports/mappings')[0],401)
  self.assertEqual(self.request('GET','/api/imports/mappings',token=basic)[0],403)
  self.assertEqual(self.request('GET','/api/imports/mappings',token=admin)[0],200)
  with patch('web.mapping_edit',return_value={'ok':True}) as edit:
   self.assertEqual(self.request('POST','/api/imports/mappings',{},basic,self.auth.user(basic)['csrf'])[0],403)
   self.assertEqual(self.request('POST','/api/imports/mappings',{},admin)[0],403)
   edit.assert_not_called()
   self.assertEqual(self.request('POST','/api/imports/mappings',{},admin,csrf)[0],200)
 def test_currency_page_api_is_available_to_authenticated_basic_with_csrf(self):
  admin,csrf=self.activate()
  self.auth.save_user({'username':'currencyreader','password':self.password,'role':'basic'})
  basic=self.auth.login('currencyreader',self.password,'test');token=self.auth.user(basic)['csrf']
  with patch('web.fx_overview',return_value={'currencies':[],'history':[],'conversions':[]}):
   self.assertEqual(self.request('GET','/api/fx?day=2026-10-12')[0],401)
   self.assertEqual(self.request('GET','/api/fx?day=2026-10-12',token=basic)[0],200)
  data={'amount':'10','from':'USD','to':'EUR','day':'2026-10-12'}
  with patch('web.fx_convert',return_value={'converted':'9','rate':'0.9'}):
   self.assertEqual(self.request('POST','/api/fx/convert',data,basic)[0],403)
   self.assertEqual(self.request('POST','/api/fx/convert',data,basic,token)[0],200)
 def test_api_connection_requires_login_security_and_csrf_and_never_returns_secrets(self):
  self.store.add_account({'name':'API broker','broker':'Trading 212'})
  data={'account_id':2,'environment':'demo','key':'private-key','secret':'private-secret'}
  self.assertEqual(self.request('POST','/api/imports/trading212/save',data)[0],400)
  token,csrf=self.activate()
  self.assertEqual(self.request('POST','/api/imports/trading212/save',data,token)[0],403)
  code,body,_=self.request('POST','/api/imports/trading212/save',data,token,csrf)
  self.assertEqual(code,200);self.assertNotIn(b'private',body)
  code,body,_=self.request('POST','/api/imports/trading212/status',{'account_id':2},token,csrf)
  self.assertEqual(code,200);self.assertTrue(json.loads(body)['saved']);self.assertNotIn(b'private',body)
  self.assertEqual(self.request('POST','/api/imports/trading212/forget',{'account_id':2},token,csrf)[0],200)
 def test_roles_csrf_direct_access_and_last_admin(self):
  admin,csrf=self.activate()
  self.assertEqual(self.request('GET','/api/state')[0],401)
  self.assertEqual(self.request('GET','/api/backup')[0],401)
  self.assertEqual(self.request('POST','/api/settings',{'default_range':'1Y'},admin)[0],403)
  self.assertEqual(self.request('POST','/api/users',{'username':'reader','password':self.password,'role':'basic'},admin,csrf)[0],200)
  basic=self.auth.login('reader',self.password,'test');basic_csrf=self.auth.user(basic)['csrf']
  for path in ('/api/users','/api/backup','/api/imports'):self.assertEqual(self.request('GET',path,token=basic)[0],403)
  for path in ('/api/settings','/api/users','/api/restore','/api/accounts','/api/imports/commit','/api/imports/resolve','/api/imports/open','/api/updates','/api/imports/trading212/save','/api/imports/trading212/status','/api/imports/trading212/start','/api/imports/trading212/poll','/api/imports/trading212/forget','/api/imports/trading212/cancel'):
   self.assertEqual(self.request('POST',path,{},basic,basic_csrf,{'Content-Type':'application/octet-stream'} if path.endswith('restore') else None)[0],403)
  self.assertEqual(self.request('GET','/api/state',token=basic)[0],200)
  self.assertEqual(self.request('POST','/api/users',{'id':1,'role':'basic','active':True},admin,csrf)[0],400)
  self.assertTrue(self.auth.user(admin))
  self.assertEqual(self.request('POST','/api/auth/logout',{},basic,basic_csrf)[0],200)
  self.assertEqual(self.request('GET','/api/state',token=basic)[0],401)
 def test_password_hash_rate_limit_expiry_and_revocation(self):
  token,csrf=self.activate()
  with self.store.connect() as db:encoded=db.execute('SELECT password_hash FROM users').fetchone()[0]
  self.assertNotIn(self.password,encoded);self.assertTrue(verify_password(self.password,encoded))
  with patch('security.time.monotonic',return_value=10**12):self.assertIsNone(self.auth.user(token))
  token=self.auth.login('owner',self.password,'test')
  self.auth.change_password(1,self.password,'Another-long-password-2026')
  self.assertIsNone(self.auth.user(token))
  with patch('security.verify_password',return_value=False):
   for _ in range(10):
    with self.assertRaises(ValueError):self.auth.login('missing','wrong','one-peer')
   with self.assertRaises(PermissionError):self.auth.login('missing','wrong','one-peer')
 def test_own_account_name_change_keeps_password_and_role(self):
  token,csrf=self.activate()
  code,_,_=self.request('POST','/api/auth/password',{'current':self.password,'password':'','username':'newowner','role':'basic'},token,csrf)
  self.assertEqual(code,200);self.assertIsNone(self.auth.user(token))
  fresh=self.auth.login('newowner',self.password,'test')
  self.assertEqual(self.auth.user(fresh)['role'],'admin')
  self.auth.save_user(dict(username='otheruser',password=self.password,role='basic'))
  with self.assertRaises(ValueError):self.auth.change_password(1,self.password,'','otheruser')
 def test_cache_etag_and_invalidation(self):
  loader=Mock(return_value={'one':1});cache=StateCache(30)
  cache.get(loader);cache.get(loader);loader.assert_called_once();cache.invalidate();cache.get(loader);self.assertEqual(loader.call_count,2)
  code,_,headers=self.request('GET','/api/state');self.assertEqual(code,200)
  self.assertEqual(self.request('GET','/api/state',extra={'If-None-Match':headers['ETag']})[0],304)
  self.request('POST','/api/settings',{'default_range':'1Y'})
  self.assertEqual(self.request('GET','/api/state',extra={'If-None-Match':headers['ETag']})[0],200)
 def test_broker_filter_keeps_financial_rows_in_the_correct_account(self):
  self.assertEqual(self.request('POST','/api/accounts',{'name':'Tweede rekening','broker':'Trading 212'})[0],201)
  lot=dict(name='Apple',symbol='AAPL',exchange='NASDAQ',currency='USD',quantity='1',price='100',purchased_on='2026-10-12')
  self.request('POST','/api/purchases',{**lot,'account_id':1})
  self.request('POST','/api/purchases',{**lot,'quantity':'2','account_id':2})
  code,data,_=self.request('GET','/api/state?account_id=2');self.assertEqual(code,200)
  state=json.loads(data);self.assertEqual(len(state['positions']),1);self.assertEqual(state['positions'][0]['quantity'],'2')
  self.assertEqual(state['purchases'][0]['account_id'],2)
  self.assertEqual(self.request('GET','/api/state?account_id=999')[0],404)
 def test_recent_quotes_and_daily_history_are_not_refetched(self):
  import server
  from datetime import date
  self.store.add(dict(name='Apple',symbol='AAPL',exchange='NASDAQ',currency='USD',quantity='1',price='100',purchased_on='2026-01-01'))
  self.store.quote('AAPL','NASDAQ','USD','120','2026-10-16T20:00:00+00:00','test')
  self.store.save_history('AAPL','NASDAQ','USD','2026-01-01',[dict(day=date.today().isoformat(),price='120')])
  with patch.object(server,'store',self.store),patch.object(server,'fetch_quote') as quote,patch.object(server,'fetch_history') as history,patch('server.time.sleep'):
   server.refresh();server.refresh()
   quote.assert_not_called();history.assert_not_called()
 def test_restore_preserves_live_users_and_rejects_bad_files(self):
  token,csrf=self.activate()
  lot=dict(name='Apple',symbol='AAPL',exchange='NASDAQ',currency='USD',quantity='2',price='100',purchased_on='2026-01-01')
  self.store.add(lot);self.store.add_dividend(dict(symbol='AAPL',exchange='NASDAQ',currency='USD',amount='3',paid_on='2026-02-01'))
  content=self.store.backup().read_bytes()
  self.store.add({**lot,'quantity':'3'})
  before=self.store.state()['positions'][0]['quantity']
  with self.assertRaises(ValueError):restore_backup(self.store,b'invalid')
  self.assertEqual(self.store.state()['positions'][0]['quantity'],before)
  code,_,_=self.request('POST','/api/restore',content,token,csrf,{'Content-Type':'application/octet-stream','X-Confirm-Restore':'yes'})
  self.assertEqual(code,200)
  self.assertEqual(self.store.state()['positions'][0]['quantity'],'2')
  self.assertEqual(self.store.state()['positions'][0]['dividend'],'3')
  self.assertTrue(self.auth.enabled());self.assertEqual(self.auth.list_users()[0]['username'],'owner')
  self.assertIsNone(self.auth.user(token))
  self.assertEqual(len(list((self.store.root/'backups'/'restores').glob('*.sqlite3'))),1)
 def test_restore_older_database_never_imports_triggers(self):
  self.auth.enable('owner',self.password)
  with tempfile.TemporaryDirectory() as temp:
   old=Store(temp);old.add(dict(name='Apple',symbol='AAPL',exchange='NASDAQ',currency='USD',quantity='1',price='100',purchased_on='2026-01-01'))
   with old.connect() as db:
    db.execute("CREATE TRIGGER malicious AFTER INSERT ON purchases BEGIN DELETE FROM users; END")
    db.execute('DROP TABLE users');db.execute("DELETE FROM app_settings WHERE key='auth_enabled'");db.execute('PRAGMA user_version=4')
   restore_backup(self.store,old.backup().read_bytes())
  self.assertTrue(self.auth.enabled());self.assertEqual(len(self.auth.list_users()),1)
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0],0)
 def test_restore_transaction_failure_keeps_original_portfolio(self):
  lot=dict(name='Apple',symbol='AAPL',exchange='NASDAQ',currency='USD',quantity='2',price='100',purchased_on='2026-01-01')
  self.store.add(lot)
  with tempfile.TemporaryDirectory() as temp:
   corrupt=Store(temp);corrupt.add({**lot,'quantity':'99'})
   with corrupt.connect() as db:
    db.execute('ALTER TABLE purchases RENAME TO original')
    db.execute('CREATE TABLE purchases AS SELECT * FROM original')
    db.execute('INSERT INTO purchases SELECT * FROM original')
   with self.assertRaises(sqlite3.IntegrityError):restore_backup(self.store,corrupt.backup().read_bytes())
  self.assertEqual(self.store.state()['positions'][0]['quantity'],'2')
