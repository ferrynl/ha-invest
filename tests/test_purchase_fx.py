import sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from datetime import date
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from forex import save_rates,remember_coverage
from restore import restore_backup

class PurchaseFxTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.store=Store(self.folder.name)
  save_rates(self.store,[dict(base='EUR',quote='USD',date='2026-10-12',rate='1.2'),dict(base='EUR',quote='GBP',date='2026-10-12',rate='.8')],date(2026,10,12))
 def trade(self,**values):return dict(dict(symbol='TEST',exchange='NYSE',name='Test',currency='USD',quantity='2',price='12',price_eur='10',purchased_on='2026-10-12'),**values)
 def test_eur_price_is_verified_and_audited_without_costs(self):
  self.store.add(self.trade())
  self.assertEqual(self.store.state()['purchases'][0]['price'],'12.0')
  with self.store.connect() as db:
   row=db.execute('SELECT * FROM import_fx').fetchone();self.assertEqual((row['original_amount'],row['converted_amount'],row['source_currency'],row['target_currency']),('10','12.0','EUR','USD'))
   raw=json.loads(db.execute('SELECT raw FROM import_records').fetchone()[0]);self.assertEqual(raw['price_fx']['amount'],'10')
  restored=Store(Path(self.folder.name)/'restored');restore_backup(restored,self.store.backup().read_bytes())
  with restored.connect() as db:self.assertEqual(db.execute('SELECT original_amount FROM import_fx').fetchone()[0],'10')
 def test_pence_and_costs_share_one_atomic_source(self):
  self.store.add(self.trade(currency='GBX',exchange='LONDON',price='800',fee_amount='1',charge_currency='EUR'))
  with self.store.connect() as db:
   self.assertEqual(Decimal(db.execute('SELECT price FROM purchases').fetchone()[0]),800)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM import_batches').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM charges').fetchone()[0],1)
   self.assertEqual(Decimal(db.execute('SELECT rate FROM import_fx').fetchone()[0]),80)
 def test_missing_rate_mismatched_price_and_eur_listing_cannot_be_booked(self):
  for values in (dict(price='99'),dict(currency='EUR'),dict(price_eur='NaN'),dict(price_eur='-1'),dict(price_eur=0),dict(price=0)):
   with self.assertRaises(ValueError):self.store.add(self.trade(**values))
  with patch('forex.snapshot',side_effect=ValueError('missing rate')):
   with self.assertRaises(ValueError):self.store.add(self.trade(currency='CAD'))
  self.assertEqual(self.store.state()['purchases'],[])
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM import_fx').fetchone()[0],0)
 def test_quote_day_is_historical_and_not_a_future_rate(self):
  remember_coverage(self.store,['USD'],'2026-10-12','2026-10-13')
  self.store.add(self.trade(purchased_on='2026-10-13'))
  with self.store.connect() as db:
   row=db.execute('SELECT * FROM import_fx').fetchone();self.assertEqual(row['requested_on'],'2026-10-13');self.assertEqual(row['rate_on'],'2026-10-12')
 def test_failed_sale_leaves_no_price_audit_or_source_batch(self):
  with self.assertRaises(ValueError):self.store.add(self.trade(side='SELL',fee_amount='1'))
  with self.store.connect() as db:
   for table in ('purchases','import_fx','import_batches','charges','import_records'):self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
