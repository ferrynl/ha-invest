import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from performance import overview,xirr,summarize,annual_points
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
 def test_sparse_year_boundaries_match_full_daily_report_with_dated_fx(self):
  from home_euro import build
  self.stock.update(currency='USD',exchange='NYSE')
  self.trade('10','10','2025-01-01');self.trade('2','15','2026-01-02',side='SELL')
  self.store.add_dividend(dict(**self.stock,amount='5',paid_on='2026-02-01'))
  self.store.save_history('TEST','NYSE','USD','2025-01-01',[dict(day='2025-12-31',price='12')])
  self.store.quote('TEST','NYSE','USD','20','2026-10-30T10:00:00+00:00','Test')
  rates=[]
  for day,rate in [('2025-01-01','2'),('2025-12-31','3'),('2026-01-02','3'),('2026-02-01','4'),('2026-10-30','5')]:
   rates.append(dict(base='EUR',quote='USD',day=day,rate=rate))
   with self.store.connect() as db:db.execute("INSERT INTO fx_rates VALUES('EUR','USD',?,?,'Test','2026-10-30T10:00:00+00:00')",(day,rate))
  snapshot=self.store.state();today=date(2026,10,30)
  full=build(snapshot,rates,today=today,skip_invalid=True)
  sparse=build({**snapshot,'positions':[{**p,'history':annual_points(p['history'])} for p in snapshot['positions']]},rates,today=today,skip_invalid=True,sparse_history=True)
  self.assertEqual(sparse['positions'][0]['history'],annual_points(full['positions'][0]['history']))
  converted=[{**t,'price':str(Decimal(t['price'])/Decimal('2' if t['side']=='BUY' else '3'))} for t in snapshot['purchases']]
  income=[{**d,'amount':str(Decimal(d['amount'])/4)} for d in snapshot['dividends']]
  expected=summarize(full['positions'],converted,income,today)
  actual=self.report()['groups'][0]
  for key,value in expected.items():
   if key=='years':
    for observed,wanted in zip(actual[key],value):
     self.assertEqual((observed['year'],observed['day']),(wanted['year'],wanted['day']))
     for field in ('gain','invested'):self.assertEqual(Decimal(observed[field]) if observed[field] is not None else None,Decimal(wanted[field]) if wanted[field] is not None else None)
   elif isinstance(value,str):self.assertEqual(Decimal(actual[key]),Decimal(value),key)
   else:self.assertEqual(actual[key],value,key)
 def test_neutral_split_does_not_require_an_fx_rate_on_split_day(self):
  self.stock.update(currency='USD',exchange='NYSE');self.trade('1','100','2026-01-01')
  with self.store.connect() as db:
   db.execute("INSERT INTO purchases(symbol,exchange,currency,name,quantity,price,purchased_on,created_at,split_before) VALUES('TEST','NYSE','USD','Test','2','1','2026-08-01','2026-08-01T00:00:00+00:00','1')")
   for day in ('2026-01-01','2026-10-30'):db.execute("INSERT INTO fx_rates VALUES('EUR','USD',?,'2','Test','2026-10-30T10:00:00+00:00')",(day,))
  self.store.quote('TEST','NYSE','USD','55','2026-10-30T10:00:00+00:00','Test')
  group=self.report()['groups'][0];self.assertTrue(group['complete']);self.assertEqual(Decimal(group['total']),5)

class PerformanceHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_unexpected_server_failure_returns_safe_diagnostic_reference(self):
  with patch('performance.overview',side_effect=RuntimeError('private provider response')):
   code,data=self.request('/api/reports/performance')
  self.assertEqual(code,500);self.assertIn('Log-ID',data['error']);self.assertNotIn('private',data['error'])
  with self.store.read() as db:log=db.execute("SELECT message,details FROM app_logs WHERE event='performance_failed'").fetchone()
  self.assertIsNotNone(log);self.assertNotIn('private',str(tuple(log)));self.assertIn('RuntimeError',log['details'])
 def test_report_is_read_only_authenticated_and_validates_filters(self):
  code,data=self.request('/api/reports/performance');self.assertEqual(code,200);self.assertTrue(data['groups'][0]['combined'])
  self.assertEqual(self.request('/api/reports/performance?account_id=999')[0],400)
  self.assertEqual(self.request('/api/reports/performance?instrument=invalid')[0],400)
  self.auth.enable('owner','Long-test-password-2026')
  self.assertEqual(self.request('/api/reports/performance')[0],401)
  token=self.auth.login('owner','Long-test-password-2026','test')
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/reports/performance',token=token)[0],200)
