import sys, tempfile, unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from reports import combined

class CombinedReportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  for symbol,currency,price in [('EURO','EUR','50'),('DOLLAR','USD','100'),('PENCE','GBX','100')]:
   self.store.add(dict(symbol=symbol,exchange='TEST',currency=currency,name=symbol,quantity='2',price=price,purchased_on='2026-10-01'))
   self.store.quote(symbol,'TEST',currency,price,'2026-10-03T10:00:00+00:00','test')
   self.store.add_dividend(dict(symbol=symbol,exchange='TEST',currency=currency,amount='10',paid_on='2026-10-02'))
  with self.store.connect() as db:
   db.executemany('INSERT INTO fx_rates VALUES(?,?,?,?,?,?)',[('EUR','USD','2026-10-01','2','test','now'),('EUR','USD','2026-10-02','4','test','now'),('EUR','USD','2026-10-03','1','test','now'),('EUR','GBP','2026-10-01','.8','test','now')])
 def build(self,**kwargs):return combined(self.store,self.store.state(),today=date(2026,10,3),**kwargs)
 def test_market_and_income_use_different_dated_rates_and_pence(self):
  before=deepcopy(self.store.state());result=self.build(include_history=True)
  self.assertEqual(sum(Decimal(p['value']) for p in result['positions']),Decimal('302.5'))
  self.assertEqual(sum(Decimal(d['amount']) for d in result['dividends']),Decimal('12.625'))
  self.assertEqual({p['currency'] for p in result['positions']},{'EUR'})
  self.assertEqual({p['native_currency'] for p in result['positions']},{'EUR','USD','GBX'})
  self.assertIsNotNone(result['history']);self.assertEqual(result['excluded'],[])
  self.assertEqual(self.store.state(),before)
 def test_filters_and_invalid_account(self):
  result=self.build(instrument=['DOLLAR','TEST','USD'],currency='USD')
  self.assertEqual(len(result['positions']),1);self.assertEqual(len(result['dividends']),1)
  self.assertNotIn('history',result)
  with self.assertRaises(ValueError):self.build(account='999')
 def test_future_fx_is_never_used_and_income_remains_independent(self):
  with self.store.connect() as db:db.execute("DELETE FROM fx_rates WHERE quote='USD' AND day='2026-10-01'")
  result=self.build()
  self.assertIn('DOLLAR',[p['symbol'] for p in result['excluded']])
  self.assertIn('DOLLAR',[p['symbol'] for p in result['dividends']])
  with self.store.connect() as db:db.execute("DELETE FROM fx_rates WHERE quote='USD' AND day<='2026-10-02'")
  result=self.build();self.assertIn('DOLLAR',[p['symbol'] for p in result['missing_dividends']])
import test_transactions as report_http_support
class CombinedReportHttpTests(unittest.TestCase):
 setUp=report_http_support.TransactionHttpTests.setUp
 tearDown=report_http_support.TransactionHttpTests.tearDown
 request=report_http_support.TransactionHttpTests.request
 def test_combined_endpoint_cache_and_account_validation(self):
  status,result=self.request('/api/reports/combined?history=1')
  self.assertEqual(status,200);self.assertEqual(result['positions'][0]['currency'],'EUR')
  self.assertIn('history',result);self.assertIn('data_revision',result)
  self.assertEqual(self.request('/api/reports/combined?account_id=999')[0],400)
  self.assertEqual(self.request('/api/reports/combined?instrument=%5B1%5D')[0],400)
