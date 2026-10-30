import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from performance import overview,xirr
from conversions import preview,commit
import test_transactions as support

class PerformanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.stock=dict(symbol='TEST',exchange='AMSTERDAM',currency='EUR',name='Test')
 def trade(self,quantity,price,day,**kw):self.store.add(dict(**self.stock,quantity=quantity,price=price,purchased_on=day,**kw))
 def report(self,**kw):return overview(self.store,self.store.state(),today=date(2026,10,30),**kw)
 def test_xirr_reference_irregular_schedule_and_ambiguous_roots(self):
  values=[('2008-01-01','-10000'),('2008-03-01','2750'),('2008-10-30','4250'),('2009-02-15','3250'),('2009-04-01','2750')]
  self.assertAlmostEqual(float(xirr(values)),37.3362535,places=6)
  self.assertIsNone(xirr([('2023-01-01','-100'),('2024-01-01','230'),('2024-12-31','-132')]))
  self.assertIsNone(xirr([('2026-01-01','-100'),('2026-01-01','120')]))
  self.assertAlmostEqual(float(xirr([('2025-01-01','-100'),('2026-01-01','80')])),-20,places=6)
 def test_sales_dividends_total_and_percentages(self):
  self.trade('10','10','2025-01-01');self.trade('2','15','2026-01-02',side='SELL')
  self.store.add_dividend(dict(**self.stock,amount='5',paid_on='2026-02-01'))
  self.store.quote('TEST','AMSTERDAM','EUR','20','2026-10-30T10:00:00+00:00','Test')
  group=self.report()['groups'][0]
  self.assertEqual(tuple(Decimal(group[k]) for k in ('invested','price_gain','realised','dividend','total')),(100,80,10,5,95))
  self.assertEqual(Decimal(group['total_percent']),95)
  self.assertIsNone(group['costs']);self.assertIsNone(group['taxes']);self.assertIsNone(group['twr'])
  self.assertIsNotNone(group['irr']);self.assertIsNone(group['years'][0]['gain'])
 def test_annual_profit_is_change_in_cumulative_profit_not_deposits(self):
  self.trade('10','10','2025-01-01');self.store.save_history('TEST','AMSTERDAM','EUR','2025-01-01',[dict(day='2025-12-31',price='12')])
  self.trade('10','12','2026-01-02');self.store.quote('TEST','AMSTERDAM','EUR','15','2026-10-30T10:00:00+00:00','Test')
  group=self.report()['groups'][0]
  self.assertEqual([Decimal(y['gain']) for y in group['years']],[20,60])
  self.assertEqual([Decimal(y['invested']) for y in group['years']],[100,120])
 def test_missing_quote_never_becomes_zero_profit_or_rate(self):
  self.trade('1','100','2026-01-01');group=self.report()['groups'][1]
  self.assertFalse(group['complete']);self.assertIsNone(group['total']);self.assertIsNone(group['irr']);self.assertIsNone(group['years'][0]['gain'])
 def test_combined_fx_missing_and_native_currency_scope(self):
  self.stock.update(currency='USD',exchange='NYSE');self.trade('1','100','2026-01-01')
  self.store.quote('TEST','NYSE','USD','110','2026-10-30T10:00:00+00:00','Test')
  groups=self.report()['groups'];self.assertFalse(groups[0]['complete']);self.assertEqual(groups[1]['total'],'10')
  with self.store.connect() as db:
   for day in ('2026-01-01','2026-10-30'):db.execute("INSERT INTO fx_rates VALUES('EUR','USD',?,'2','Test','2026-10-30T10:00:00+00:00')",(day,))
  groups=self.report()['groups'];self.assertTrue(groups[0]['complete']);self.assertEqual(Decimal(groups[0]['total']),5)
  self.assertEqual([g['currency'] for g in self.report(currency='USD')['groups']],['EUR','USD'])
 def test_internal_merger_does_not_double_capital_or_investment_cashflows(self):
  self.stock['symbol']='TMX.AS';self.trade('10','80','2025-09-01')
  commit(self.store,preview(self.store,dict(account_id=1,day='2025-10-02',quantity='')),'Test')
  self.store.quote('TDT.AS','AMSTERDAM','EUR','100','2026-10-30T10:00:00+00:00','Test')
  group=self.report()['groups'][0]
  self.assertEqual(Decimal(group['invested']),800);self.assertEqual(Decimal(group['total']),Decimal('137.6300'))
  self.assertIsNotNone(group['irr'])
  self.assertIsNone(self.report(instrument=['TDT.AS','AMSTERDAM','EUR'])['groups'][0]['irr'])
 def test_account_filter_rejects_unknown_accounts(self):
  with self.assertRaises(ValueError):self.report(account='999')

class PerformanceHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_report_is_read_only_authenticated_and_validates_filters(self):
  code,data=self.request('/api/reports/performance');self.assertEqual(code,200);self.assertTrue(data['groups'][0]['combined'])
  self.assertEqual(self.request('/api/reports/performance?account_id=999')[0],400)
  self.assertEqual(self.request('/api/reports/performance?instrument=invalid')[0],400)
  self.auth.enable('owner','Long-test-password-2026')
  self.assertEqual(self.request('/api/reports/performance')[0],401)
  token=self.auth.login('owner','Long-test-password-2026','test')
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/reports/performance',token=token)[0],200)
