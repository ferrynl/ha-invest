import sys,tempfile,unittest,json,threading
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from valuations import save
from instruments import details
from restore import restore_backup
from diagnostics import read_logs
STOCK=dict(symbol='TEST',exchange='NASDAQ',currency='USD',name='Test')
class ValuationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add(dict(**STOCK,quantity='2',price='100',purchased_on='2026-10-01'))
  self.store.add_dividend(dict(symbol='TEST',exchange='NASDAQ',currency='USD',amount='10',paid_on='2026-10-02'))
 def test_missing_quote_has_actionable_bounded_diagnostic(self):
  for _ in range(3):p=self.store.state()['positions'][0]
  self.assertIsNone(p['value']);self.assertIsNone(p['total_gain']);self.assertTrue(p['valuation_log_id'])
  rows=[r for r in read_logs(self.store)['entries'] if r['event']=='valuation_missing']
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['details']['symbol'],'TEST');self.assertEqual(rows[0]['details']['quantity'],'2');self.assertEqual(rows[0]['reference'],p['valuation_log_id'])
 def test_final_price_zero_overrides_newer_provider_data_and_survives_restore(self):
  self.store.quote('TEST','NASDAQ','USD','150','2026-10-20T12:00:00+00:00','test')
  self.store.save_history('TEST','NASDAQ','USD','2026-10-01',[dict(day='2026-10-21',price='200')])
  save(self.store,dict(**STOCK,automatic=False,price='0',day='2026-10-15'))
  p=self.store.state()['positions'][0];self.assertEqual(Decimal(p['value']),0);self.assertTrue(p['quote']['manual']);self.assertEqual(Decimal(p['total_gain']),-190);self.assertEqual(Decimal(p['history'][-1]['value']),0)
  d=details(self.store,STOCK);self.assertEqual(d['summary']['dividend_percent'],'5.00');self.assertEqual(d['quote']['price'],'0');self.assertEqual(d['prices'][-1],dict(day='2026-10-15',price='0'))
  backup=self.store.backup().read_bytes();save(self.store,dict(**STOCK,automatic=True));self.assertEqual(self.store.state()['positions'][0]['value'],'300')
  restore_backup(self.store,backup);self.assertEqual(self.store.state()['positions'][0]['quote']['price'],'0');self.assertEqual(Store(self.tmp.name).state()['positions'][0]['quote']['price'],'0')
 def test_final_price_is_shared_but_dividend_percentage_scoped(self):
  self.store.add_account(dict(name='Second',broker='Test'))
  self.store.add(dict(**STOCK,quantity='1',price='50',purchased_on='2026-10-02',account_id=2))
  save(self.store,dict(**STOCK,automatic=False,price='25',day='2026-10-03'))
  self.assertEqual([p['value'] for p in self.store.state()['positions']],['50','25'])
  self.assertEqual(Decimal(details(self.store,STOCK,'all')['summary']['dividend_percent']),4)
  self.assertEqual(Decimal(details(self.store,STOCK,'2')['summary']['dividend_percent']),0)
 def test_invalid_final_prices_are_atomic(self):
  for values in [dict(price='-1'),dict(price='NaN'),dict(price='1e16'),dict(day='2999-01-01'),dict(automatic='false'),dict(symbol='UNKNOWN')]:
   with self.subTest(values=values),self.assertRaises(ValueError):save(self.store,{**STOCK,'automatic':False,'price':'1','day':'2026-10-03',**values})
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM instrument_valuations').fetchone()[0],0)
 def test_background_never_requests_quote_or_history_for_final_price(self):
  import server
  save(self.store,dict(**STOCK,automatic=False,price='25',day='2026-10-03'))
  with patch.object(server,'store',self.store),patch.object(server,'fetch_quote') as quote,patch.object(server,'fetch_history') as history,patch.object(server,'enrich_categories',return_value=False):
   server.refresh();quote.assert_not_called();history.assert_not_called()
