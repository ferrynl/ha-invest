import http.client
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
import transactions
from storage import Store
from imports.service import preview
from imports.registry import remember
from imports.partial import commit_partial,list_issues
from migrations import MIGRATIONS,SCHEMA_VERSION,migrate
from restore import restore_backup
from security import Auth
from cache import StateCache
from web import make_handler
from http.server import ThreadingHTTPServer

HEADER='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total)\n'
SOURCE='Market buy,2026-10-01 10:00:00,NL0010273215,ASML,ASML,buy,2,100,EUR,200,EUR\nDividend (Return of capital manufactured payment),2026-10-02 10:00:00,NL0010273215,ASML,ASML,capital,,,,5,EUR\nUnknown,2026-10-03 10:00:00,,BAD,Bad,error,,,,1,EUR\n'
STOCK=dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')

class TransactionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Broker A',broker='Trading 212'));self.store.add_account(dict(name='Broker B',broker='Trading 212'))
 def imported(self,account=2):
  result=preview(self.store,account,'trading212','source.csv',HEADER+SOURCE)
  for row in result['rows']:
   if row.get('currency'):remember(self.store,account,'trading212',row,STOCK)
  commit_partial(self.store,result['batch_id'])
  return result['batch_id']
 def trade(self,account=2):
  self.store.add(dict(**STOCK,account_id=account,quantity='2',price='100',purchased_on='2026-10-01'))
  return transactions.ledger(self.store,account)['transactions'][0]
 def save(self,row,**fields):
  data=dict(kind=row['kind'],id=row['id'],revision=row['revision'],day=row['day'],quantity=row.get('quantity'),price=row.get('price'),amount=row.get('amount'))
  return transactions.edit(self.store,{**data,**fields},'owner')
 def test_trade_edit_recalculates_and_audits_without_rewriting_source(self):
  self.imported();row=next(r for r in transactions.ledger(self.store,2)['transactions'] if r['kind']=='trade')
  with self.store.connect() as db:original=[tuple(r) for r in db.execute('SELECT * FROM import_records')]
  self.save(row,quantity='3',price='110')
  self.assertEqual(float(self.store.state()['positions'][0]['cost']),330)
  self.assertEqual(len(transactions.changes(self.store,'trade',row['id'])['changes']),1)
  with self.store.connect() as db:self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM import_records')],original)
  self.imported();self.assertEqual(len(self.store.state()['purchases']),1)
 def test_invalid_history_and_stale_revision_roll_back(self):
  row=self.trade();self.store.add(dict(**STOCK,account_id=2,quantity='1',price='120',purchased_on='2026-10-02',side='SELL'))
  with self.assertRaises(ValueError):self.save(row,quantity='0.5')
  self.assertEqual(transactions.changes(self.store,'trade',row['id'])['changes'],[])
  self.save(row,price='101')
  with self.assertRaises(ValueError):self.save(row,price='102')
  self.assertEqual(float(self.store.state()['purchases'][0]['price']),101)
 def test_dividend_capital_and_split_are_editable(self):
  self.imported();self.store.add_dividend(dict(**STOCK,account_id=2,amount='5',paid_on='2026-10-03'))
  for row in transactions.ledger(self.store,2)['transactions']:
   if row['kind']!='trade':self.save(row,amount='7',day='2026-10-04')
  self.assertEqual(self.store.state()['dividends'][0]['amount'],'7')
  self.assertEqual(list_issues(self.store)['capital_returns'][0]['amount'],'7')
  with self.store.connect() as db:
   db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time,split_before) VALUES('ASML.AS','AMSTERDAM','ASML','4','50','EUR','2026-10-05','2026-10-05T00:00:00+00:00',2,'BUY','2026-10-05T10:00:00','2')")
  split=next(r for r in transactions.ledger(self.store,2)['transactions'] if r['type']=='SPLIT')
  self.save(split,quantity='6')
  self.assertEqual(float(self.store.state()['positions'][0]['quantity']),6)
  self.assertEqual(float(self.store.state()['positions'][0]['cost']),200)
 def test_invalid_amount_date_and_identity_rejected(self):
  row=self.trade()
  for fields in (dict(price='NaN'),dict(quantity='0'),dict(day='2099-01-01'),dict(account_id=3),dict(symbol='OTHER')):
   with self.subTest(fields=fields),self.assertRaises(ValueError):self.save(row,**fields)
  self.assertEqual(transactions.changes(self.store,'trade',row['id'])['changes'],[])
 def test_scoped_reset_keeps_other_broker_and_allows_reimport(self):
  self.imported(2);self.imported(3)
  self.store.quote('ASML.AS','AMSTERDAM','EUR','120','2026-10-03T10:00:00+00:00','test')
  row=next(r for r in transactions.ledger(self.store,2)['transactions'] if r['kind']=='trade');self.save(row,price='110')
  snapshot=transactions.reset_preview(self.store,2)
  result=transactions.reset(self.store,dict(account_id=2,revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  state=self.store.state();self.assertEqual([r['account_id'] for r in state['purchases']],[3]);self.assertEqual(len(state['quotes']),1)
  self.assertEqual(len(state['accounts']),3)
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM import_records WHERE account_id=2').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM transaction_edits').fetchone()[0],0)
  backup=transactions.deletion_backup(self.store,result['backup_name'])
  self.assertTrue(backup.is_file());self.imported(2);self.assertEqual(len(self.store.state()['purchases']),2)
  restore_backup(self.store,backup.read_bytes());self.assertEqual(float(self.store.state()['purchases'][0]['price']),110)
  self.assertEqual(len(transactions.changes(self.store,'trade',row['id'])['changes']),1)
 def test_all_reset_preserves_accounts_settings_users_and_fx(self):
  self.imported(2);self.imported(3);self.store.save_settings(dict(default_range='1Y'))
  auth=Auth(self.store);auth.enable('owner','Long-test-password-2026')
  with self.store.connect() as db:db.execute("INSERT INTO fx_rates VALUES('USD','EUR','2026-10-01','0.9','test','2026-10-01T00:00:00+00:00')")
  snapshot=transactions.reset_preview(self.store,'all');transactions.reset(self.store,dict(account_id='all',revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  self.assertEqual(self.store.state()['purchases'],[]);self.assertEqual(self.store.state()['dividends'],[])
  self.assertEqual(self.store.settings()['default_range'],'1Y');self.assertTrue(auth.enabled())
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM fx_rates').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM import_batches').fetchone()[0],0)
 def test_reset_requires_confirmation_current_preview_and_working_backup(self):
  self.trade();snapshot=transactions.reset_preview(self.store,2)
  with self.assertRaises(ValueError):transactions.reset(self.store,dict(account_id=2,revision=snapshot['revision'],confirmation='yes'))
  self.trade()
  with self.assertRaises(ValueError):transactions.reset(self.store,dict(account_id=2,revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  snapshot=transactions.reset_preview(self.store,2)
  with patch.object(self.store,'backup',side_effect=OSError('No space')),self.assertRaises(OSError):transactions.reset(self.store,dict(account_id=2,revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  self.assertEqual(len(self.store.state()['purchases']),2)
 def test_backup_download_rejects_path_traversal(self):
  with self.assertRaises(ValueError):transactions.deletion_backup(self.store,'../../portfolio.sqlite3')
 def test_schema_eleven_upgrade_rollback_and_old_backup_restore(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'old.sqlite3'
   with closing(sqlite3.connect(path)) as db,db:
    for version in range(1,12):
     for statement in MIGRATIONS[version]:db.execute(statement)
    db.execute('PRAGMA user_version=11')
    db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES('ASML.AS','AMSTERDAM','ASML','2','100','EUR','2026-10-01','2026-10-01T00:00:00+00:00')")
   restore_backup(self.store,path.read_bytes());self.assertEqual(len(self.store.state()['purchases']),1)
   with patch.dict(MIGRATIONS,{12:MIGRATIONS[12]+('INVALID SQL',)}),self.assertRaises(sqlite3.Error):migrate(path)
   with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],11)
   migrate(path);migrate(path)
   with closing(sqlite3.connect(path)) as db:
    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
    self.assertEqual(db.execute('SELECT quantity FROM purchases').fetchone()[0],'2')

class TransactionHttpTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name);self.auth=Auth(self.store);self.cache=StateCache()
  self.store.add(dict(**STOCK,quantity='2',price='100',purchased_on='2026-10-01'))
  self.http=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.store,self.auth,self.cache,{},900,threading.Lock(),threading.Event()))
  self.worker=threading.Thread(target=self.http.serve_forever,daemon=True);self.worker.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.worker.join()
 def request(self,path,data=None,token='',csrf=''):
  connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
  try:
   headers={'Content-Type':'application/json','X-Portfolio-Request':'1','Cookie':'homeinvest_session='+token,'X-CSRF-Token':csrf}
   connection.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers)
   response=connection.getresponse();body=response.read();return response.status,json.loads(body) if response.getheader('Content-Type')=='application/json' else body
  finally:connection.close()
 def test_edits_invalidate_state_cache_and_backup_download_is_admin_only(self):
  _,rows=self.request('/api/transactions');row=rows['transactions'][0];self.cache.get(self.store.state)
  code,_=self.request('/api/transactions/edit',dict(kind='trade',id=row['id'],revision=row['revision'],day=row['day'],quantity='3',price='110'))
  self.assertEqual(code,200);self.assertEqual(self.request('/api/state')[1]['positions'][0]['cost'],'330')
  _,snapshot=self.request('/api/portfolio/delete-preview?account_id=all')
  code,result=self.request('/api/portfolio/delete',dict(account_id='all',revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  self.assertEqual(code,200);self.assertEqual(self.request('/api/state')[1]['purchases'],[])
  code,body=self.request('/api/portfolio/deletion-backup?name='+result['backup_name']);self.assertEqual(code,200);self.assertTrue(body.startswith(b'SQLite format 3'))
 def test_roles_authentication_and_csrf_are_enforced_on_server(self):
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
  self.assertEqual(self.request('/api/transactions')[0],401)
  self.assertEqual(self.request('/api/transactions/edit',{},token)[0],403)
  self.assertEqual(self.request('/api/portfolio/delete',{},token)[0],403)
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/transactions',token=token)[0],200)
  self.assertEqual(self.request('/api/transactions/edit',{},token,csrf)[0],403)
  for path in ('/api/portfolio/delete-preview','/api/portfolio/deletion-backup'):
   self.assertEqual(self.request(path,token=token)[0],403)
  self.assertEqual(self.request('/api/portfolio/delete',{},token,csrf)[0],403)
