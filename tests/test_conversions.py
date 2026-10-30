import sys
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
import sqlite3
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from conversions import preview,commit,SOURCE,TARGET,validate_pairs
from restore import restore_backup
from migrations import MIGRATIONS,SCHEMA_VERSION,migrate
import test_transactions as support

class ConversionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  for name in ('First','Second'):self.store.add_account(dict(name=name,broker='Trading 212'))
  for owner in (2,3):
   self.store.add(dict(account_id=owner,symbol=SOURCE[0],exchange=SOURCE[1],currency='EUR',name='TMX',quantity='10',price='80',purchased_on='2025-09-01'))
  self.data=dict(account_id=2,day='2025-10-02',quantity='')
 def save(self):return commit(self.store,preview(self.store,self.data),'tester')
 def test_transfer_preserves_original_history_cost_income_and_total_investment(self):
  self.store.add_dividend(dict(account_id=2,symbol=SOURCE[0],exchange=SOURCE[1],currency='EUR',amount='15',paid_on='2025-09-20'))
  original=self.store.state()['purchases']
  result=self.save();self.assertEqual(result['quantity'],'9.376300')
  state=self.store.state();old=next(p for p in state['positions'] if p['symbol']==SOURCE[0] and p['account_id']==2);new=next(p for p in state['positions'] if p['symbol']==TARGET[0])
  self.assertEqual((old['quantity'],old['cost'],old['dividend']),('0','0','15'))
  self.assertEqual((new['quantity'],new['cost'],new['realised']),('9.376300','800','0'))
  self.assertEqual(sum(Decimal(p['history'][-1]['invested']) for p in state['positions'] if p['account_id']==2),800)
  self.assertEqual([r for r in state['purchases'] if not r['transfer_id']],original)
  self.assertEqual(next(p for p in state['positions'] if p['account_id']==3)['quantity'],'10')
  self.assertTrue((self.store.root/'backups/conversions'/result['backup_name']).is_file())
  self.assertEqual(next(p for p in old['history'] if p['day']=='2025-09-15')['cost'],'800')
 def test_custom_quantity_existing_target_sales_and_idempotency(self):
  self.store.add(dict(account_id=2,symbol=TARGET[0],exchange=TARGET[1],currency='EUR',name='TDT',quantity='2',price='90',purchased_on='2025-09-01'))
  self.data['quantity']='9.37';self.save()
  self.store.add(dict(account_id=2,symbol=TARGET[0],exchange=TARGET[1],currency='EUR',name='TDT',quantity='1',price='100',purchased_on='2025-10-03',side='SELL'))
  position=next(p for p in self.store.state()['positions'] if p['symbol']==TARGET[0])
  self.assertEqual(position['quantity'],'10.37')
  with self.assertRaises(ValueError):self.save()
 def test_stale_preview_invalid_date_and_nonfinite_quantity_are_rejected(self):
  review=preview(self.store,self.data)
  self.store.add(dict(account_id=2,symbol=SOURCE[0],exchange=SOURCE[1],currency='EUR',name='TMX',quantity='1',price='80',purchased_on='2025-09-15'))
  with self.assertRaises(ValueError):commit(self.store,review,'tester')
  for change in (dict(day='2025-09-01'),dict(day='2099-01-01'),dict(quantity='NaN'),dict(account_id='all'),dict(account_id=999)):
   with self.subTest(change=change),self.assertRaises((ValueError,TypeError)):preview(self.store,{**self.data,**change})
 def test_failed_target_validation_rolls_back_both_legs(self):
  # Directly create an invalid later sale to test atomic transfer validation.
  with self.store.connect() as db:db.execute("INSERT INTO purchases(symbol,exchange,currency,name,quantity,price,purchased_on,created_at,account_id,side) VALUES('TDT.AS','AMSTERDAM','EUR','TDT','100','100','2025-10-03','2025-10-03T00:00:00+00:00',2,'SELL')")
  with self.assertRaises(ValueError):self.save()
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM purchases WHERE transfer_id<>''").fetchone()[0],0)
 def test_backup_restore_pair_validation_and_safety_backup(self):
  result=self.save();content=self.store.backup().read_bytes();restore_backup(self.store,content)
  self.assertEqual(len([p for p in self.store.state()['purchases'] if p['transfer_id']]),2)
  for bad in ('NaN','oops','-1','Infinity'):
   rows=[dict(p) for p in self.store.state()['purchases']]
   next(p for p in rows if p['transfer_id'])['transfer_cost']=bad
   with self.subTest(bad=bad),self.assertRaises(ValueError):validate_pairs(rows)
  with self.store.connect() as db:db.execute("DELETE FROM purchases WHERE transfer_id<>'' AND side='BUY'")
  with self.assertRaises(ValueError):restore_backup(self.store,self.store.backup().read_bytes())
  restore_backup(self.store,(self.store.root/'backups/conversions'/result['backup_name']).read_bytes())
  self.assertFalse(any(p['transfer_id'] for p in self.store.state()['purchases']))
 def test_schema_eighteen_upgrade_repeat_and_rollback(self):
  for failed in (True,False):
   with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'portfolio.sqlite3'
    with closing(sqlite3.connect(path)) as db,db:
     for version in range(1,19):
      for statement in MIGRATIONS[version]:db.execute(statement)
     db.execute('PRAGMA user_version=18')
     db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES('TMX.AS','AMSTERDAM','TMX','10','80','EUR','2025-09-01','2025-09-01T00:00:00+00:00')")
     db.execute("INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at) VALUES('TMX.AS','AMSTERDAM','EUR','5','2025-09-02','','2025-09-02T00:00:00+00:00')")
     db.execute("INSERT INTO daily_prices VALUES('TMX.AS','AMSTERDAM','EUR','2025-09-01','81')")
    if failed:
     with patch.dict(MIGRATIONS,{19:MIGRATIONS[19]+('INVALID SQL',)}),self.assertRaises(sqlite3.Error):migrate(path)
    else:migrate(path);migrate(path)
    with closing(sqlite3.connect(path)) as db:
     self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],18 if failed else SCHEMA_VERSION)
     self.assertEqual(db.execute('SELECT quantity,price FROM purchases').fetchone(),('10','80'))
     self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5')
     self.assertEqual(db.execute('SELECT price FROM daily_prices').fetchone()[0],'81')
    self.assertEqual(len(list((Path(folder)/'backups/migrations').glob('*.sqlite3'))),1)

class ConversionHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_admin_scoped_preview_commit_backup_and_ledger(self):
  self.store.add(dict(symbol=SOURCE[0],exchange=SOURCE[1],currency='EUR',name='TMX',quantity='10',price='80',purchased_on='2025-09-01'))
  code,review=self.request('/api/portfolio/conversion-preview',dict(account_id=1,day='2025-10-02',quantity=''))
  self.assertEqual(code,200)
  code,result=self.request('/api/portfolio/conversion',review);self.assertEqual(code,200)
  self.assertEqual(self.request('/api/portfolio/conversions')[0],200)
  code,ledger=self.request('/api/transactions');self.assertEqual(code,200)
  transfer=next(t for t in ledger['transactions'] if t['type']=='TRANSFER')
  self.assertEqual(self.request('/api/transactions/edit',dict(kind='trade',id=transfer['id'],revision=transfer['revision']))[0],400)
  self.auth.enable('administrator','long-password-123')
  self.assertEqual(self.request('/api/portfolio/conversions')[0],401)
  self.assertEqual(self.request('/api/portfolio/conversion-preview',dict(account_id=1,day='2025-10-02'))[0],401)
  token=self.auth.login('administrator','long-password-123','test');csrf=self.auth.user(token)['csrf']
  self.assertEqual(self.request('/api/portfolio/conversion',{},token)[0],403)
  code,body=self.request('/api/portfolio/conversion-backup?name='+result['backup_name'],token=token)
  self.assertEqual(code,200);self.assertTrue(body.startswith(b'SQLite format 3'))
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  for path in ('/api/portfolio/conversions','/api/portfolio/conversion-backup?name='+result['backup_name']):self.assertEqual(self.request(path,token=token)[0],403)
  for path in ('/api/portfolio/conversion','/api/portfolio/conversion-preview'):self.assertEqual(self.request(path,{},token,csrf)[0],403)
