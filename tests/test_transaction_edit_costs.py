import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
import transactions,charges
from storage import Store
from restore import restore_backup
from migrations import MIGRATIONS,migrate
from test_transactions import STOCK
import test_transactions as support_module

class EditCostTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name)
  self.store.add_account(dict(name='Other',broker='Revolut'))
 def add(self,**fields):
  self.store.add(dict(**STOCK,quantity='2',price='100',purchased_on='2026-10-01',fee_amount='1',vat_amount='.21',**fields))
  return next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
 def save(self,row,**fields):
  return transactions.edit(self.store,{**dict(kind=row['kind'],id=row['id'],revision=row['revision'],day=row['day'],quantity=row.get('quantity'),price=row.get('price')),**fields},'owner')
 def test_move_broker_costs_and_date_atomic_audit_and_restore(self):
  row=self.add();self.assertEqual(len(row['charges']),2)
  items=[dict(c,amount='2' if c['category']=='COMMISSION' else '.42') for c in row['charges']]
  with self.store.connect() as db:original=[tuple(r) for r in db.execute('SELECT * FROM import_records')]
  self.save(row,account_id=2,charges=items,day='2026-10-02')
  result=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
  self.assertEqual(result['account_id'],2);self.assertEqual(result['day'],'2026-10-02')
  self.assertEqual({(c['account_id'],c['paid_on']) for c in result['charges']},{(2,'2026-10-02')})
  self.assertEqual(charges.report(self.store,2)['total']['total'],'2.42')
  with self.store.connect() as db:self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM import_records')],original)
  restored=Store(Path(self.temp.name)/'restored');restore_backup(restored,self.store.backup().read_bytes())
  self.assertEqual(transactions.ledger(restored),transactions.ledger(self.store))
  self.assertEqual(len(transactions.changes(restored,'trade',row['id'])['changes']),1)
 def test_add_tax_and_zero_removed_source_fee_prevents_reimport(self):
  row=self.add();tax=dict(category='OTHER_TAX',amount='-.5',currency='EUR',included_in_net=0)
  self.save(row,charges=[row['charges'][1],tax])
  result=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
  self.assertEqual(charges.report(self.store)['total']['total'],'-0.29')
  fee=next(c for c in result['charges'] if c['category']=='COMMISSION');self.assertEqual(fee['amount'],'0')
  with self.store.connect() as db:
   source=dict(external_id=fee['external_id'],day='2026-10-01',ticker='ASML.AS',charges=[dict(fee,amount='1')])
   self.assertFalse(charges.pending(db,1,'charges',source));self.assertEqual(charges.book(db,fee['batch_id'],1,'charges',source),0)
  self.assertEqual(charges.report(self.store)['total']['total'],'-0.29')
 def test_stale_parent_after_child_edit_and_linked_broker_guard(self):
  parent=self.add();child=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='charge')
  self.save(child,amount='2',currency='USD',category='VAT',included_in_net=1)
  with self.assertRaises(ValueError):self.save(parent,charges=parent['charges'])
  child=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='charge')
  with self.assertRaises(ValueError):self.save(child,account_id=2,amount='3',currency='EUR',category='VAT',included_in_net=0)
 def test_explicit_link_of_old_import_fee_requires_current_revision(self):
  parent=self.add()
  with self.store.connect() as db:
   db.execute('DELETE FROM transaction_charge_links')
  parent=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
  child=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='charge')
  with self.assertRaises(ValueError):self.save(parent,charges=[dict(child,revision='stale')])
  self.save(parent,charges=[dict(child,amount='.5')])
  parent=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
  self.assertEqual([c['id'] for c in parent['charges']],[child['id']])
  self.assertEqual(parent['charges'][0]['amount'],'0.5')
 def test_standalone_charge_broker_move_keeps_original_source_dedup(self):
  self.add()
  with self.store.connect() as db:db.execute('DELETE FROM transaction_charge_links')
  child=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='charge')
  self.save(child,account_id=2,amount='3',currency='USD',category='OTHER_TAX',included_in_net=1)
  with self.store.connect() as db:
   row,moved=charges.source_charge(db,1,child['provider'],child['external_id'],child['component'])
   self.assertTrue(moved);self.assertEqual(row['amount'],'3');self.assertEqual(row['account_id'],2)
  restored=Store(Path(self.temp.name)/'restored');restore_backup(restored,self.store.backup().read_bytes())
  self.assertEqual(len(transactions.changes(restored,'charge',child['id'])['changes']),1)
 def test_invalid_components_and_oversold_original_account_roll_back(self):
  row=self.add()
  for items in ([dict(row['charges'][0],amount='NaN')],[dict(row['charges'][0],id=999)],'invalid'):
   with self.assertRaises(ValueError):self.save(row,account_id=2,charges=items)
   self.assertEqual(transactions.ledger(self.store)['transactions'][-1]['account_id'],1)
  self.store.add(dict(**STOCK,quantity='1',price='110',purchased_on='2026-10-02',side='SELL'))
  with self.assertRaises(ValueError):self.save(row,account_id=2,charges=row['charges'])
  self.assertEqual(charges.report(self.store)['total']['total'],'1.21')
  self.assertEqual(transactions.changes(self.store,'trade',row['id'])['changes'],[])
 def test_imported_trade_move_preserves_deduplication(self):
  with self.store.connect() as db:db.execute("UPDATE broker_accounts SET broker='Trading 212' WHERE id=1")
  support=support_module.TransactionTests();support.store=self.store;support.imported(1)
  row=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade')
  self.save(row,account_id=2,charges=[dict(category='VAT',amount='.3',currency='EUR',included_in_net=0)])
  support.imported(1)
  self.assertEqual(len(self.store.state()['purchases']),1);self.assertEqual(self.store.state()['purchases'][0]['account_id'],2)
 def test_migration_twenty_rollback_repeat_and_old_backup_restore(self):
  old=Path(self.temp.name)/'old.sqlite3'
  with closing(sqlite3.connect(old)) as db,db:
   for version in range(1,21):
    for statement in MIGRATIONS[version]:db.execute(statement)
   db.execute('PRAGMA user_version=20')
   db.execute("INSERT INTO purchases(id,symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES(1,'TEST','NYSE','Test','2','10','EUR','2026-10-01','2026-10-01T00:00:00+00:00')")
   db.execute("INSERT INTO import_batches(id,account_id,provider,filename,digest,payload,status,created_at) VALUES(1,1,'charges','manual-trade-1','digest','[{\"trade_id\":1}]','imported','2026-10-01T00:00:00+00:00')")
   db.execute("INSERT INTO charges VALUES(1,1,1,'charges','manual-trade:1','fee_amount','COMMISSION','TEST','1','EUR','2026-10-01',0,'Test','2026-10-01T00:00:00+00:00')")
  old_bytes=old.read_bytes()
  with patch.dict(MIGRATIONS,{21:MIGRATIONS[21]+('INVALID SQL',)}),self.assertRaises(sqlite3.Error):migrate(old)
  with closing(sqlite3.connect(old)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],20)
  migrate(old);migrate(old)
  with closing(sqlite3.connect(old)) as db:self.assertEqual(db.execute('SELECT * FROM transaction_charge_links').fetchall(),[(1,'trade',1)])
  restore_backup(self.store,old_bytes)
  row=next(r for r in transactions.ledger(self.store)['transactions'] if r['kind']=='trade');self.assertEqual(len(row['charges']),1)
  with self.store.connect() as db:db.execute("UPDATE transaction_charge_links SET record_id=999")
  with self.assertRaises(ValueError):restore_backup(Store(Path(self.temp.name)/'bad'),self.store.backup().read_bytes())
