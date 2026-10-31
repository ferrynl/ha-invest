import sys,tempfile,unittest,json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from charges import entries,report
from restore import restore_backup
from performance import overview
from datetime import date
import test_transactions as support

class ManualChargeTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.store=Store(self.folder.name)
 def trade(self,**values):
  return dict(symbol='TEST',exchange='NYSE',name='Test',currency='EUR',quantity='2',price='10',purchased_on='2026-01-05',account_id=1,**values)
 def test_manual_purchase_keeps_fees_and_vat_with_same_account_date_and_source(self):
  self.store.add(self.trade(fee_amount='1',vat_amount='.21'))
  rows=entries(self.store);self.assertEqual([(r['category'],r['amount'],r['currency'],r['paid_on']) for r in rows],[('COMMISSION','1','EUR','2026-01-05'),('VAT','0.21','EUR','2026-01-05')])
  trade=self.store.state()['purchases'][0];self.assertEqual(trade['price'],'10');self.assertEqual(trade['quantity'],'2')
  with self.store.connect() as db:
   batch=db.execute('SELECT payload FROM import_batches').fetchone();self.assertEqual(json.loads(batch['payload'])[0]['trade_id'],trade['id'])
  self.store.quote('TEST','NYSE','EUR','12','2026-10-31T10:00:00+00:00','Test')
  result=overview(self.store,self.store.state(),today=date(2026,10,31))['groups'][0]
  self.assertEqual(Decimal(result['total']),Decimal('2.79'))
 def test_optional_zero_fields_preserve_existing_behaviour_without_empty_batches(self):
  self.store.add(self.trade());self.store.add(self.trade(fee_amount='',vat_amount='0'));self.store.add(self.trade(fee_amount=None,vat_amount=None,charge_currency=None))
  self.assertEqual(entries(self.store),[])
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM import_batches').fetchone()[0],0)
 def test_foreign_charge_currency_and_vat_without_fee_are_explicit(self):
  self.store.add(self.trade(fee_amount='1',vat_amount='.20',charge_currency='usd'))
  self.assertEqual({r['currency'] for r in entries(self.store)},{'USD'});self.assertEqual(self.store.state()['purchases'][0]['currency'],'EUR')
  self.assertFalse(report(self.store)['complete'])
 def test_bad_fee_or_vat_cannot_leave_a_purchase_or_cost_behind(self):
  for values in (dict(fee_amount='-1'),dict(vat_amount='-1'),dict(fee_amount='NaN'),dict(vat_amount='Infinity'),dict(fee_amount='1e99999999'),dict(fee_amount='1',charge_currency='EURO')):
   with self.assertRaises(ValueError):self.store.add(self.trade(**values))
  self.assertEqual(self.store.state()['purchases'],[]);self.assertEqual(entries(self.store),[])
 def test_sale_and_costs_are_atomic(self):
  self.store.add(self.trade())
  self.store.add(self.trade(side='SELL',fee_amount='.5',vat_amount='.1'))
  self.assertEqual(len(entries(self.store)),2)
  with self.assertRaises(ValueError):self.store.add(self.trade(side='SELL',fee_amount='99'))
  self.assertEqual(len(self.store.state()['purchases']),2);self.assertEqual(len(entries(self.store)),2)
 def test_cost_book_failure_rolls_back_trade_provenance_and_revision(self):
  with self.store.connect() as db:before=db.execute('SELECT revision FROM dashboard_revision').fetchone()[0]
  with patch('charges.book',side_effect=ValueError('test')):
   with self.assertRaises(ValueError):self.store.add(self.trade(fee_amount='1'))
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT revision FROM dashboard_revision').fetchone()[0],before)
   for table in ('purchases','charges','import_batches','import_records'):self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
 def test_manual_trade_and_costs_survive_backup_restore(self):
  self.store.add(self.trade(fee_amount='1',vat_amount='.21'))
  restored=Store(Path(self.folder.name)/'restored');restore_backup(restored,self.store.backup().read_bytes())
  self.assertEqual(len(restored.state()['purchases']),1);self.assertEqual(len(entries(restored)),2)

class ManualChargeHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def data(self):return dict(symbol='TEST',exchange='NYSE',name='Test',currency='EUR',quantity='2',price='10',purchased_on='2026-01-05',fee_amount='1',vat_amount='.21',account_id=1)
 def test_admin_csrf_cache_and_basic_role(self):
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
  self.assertEqual(self.request('/api/purchases',self.data())[0],401)
  self.assertEqual(self.request('/api/purchases',self.data(),token)[0],403)
  self.cache.get(self.store.state)
  self.assertEqual(self.request('/api/purchases',self.data(),token,csrf)[0],201)
  self.assertEqual(len(entries(self.store)),2);self.assertEqual(len(self.cache.get(self.store.state)['charges']),2)
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/purchases',self.data(),token,csrf)[0],403)
  self.assertEqual(len(entries(self.store)),2)
