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
 def test_summary_matches_history_without_expanding_calendar_days(self):
  from unittest.mock import patch
  from history import daily_values
  self.store.add(dict(symbol='DOLLAR',exchange='TEST',currency='USD',name='DOLLAR',quantity='1',price='120',purchased_on='2026-10-02',side='SELL'))
  full=self.build(include_history=True)
  with patch('home_euro.daily_values',wraps=daily_values) as daily:
   summary=self.build()
  self.assertTrue(all(call.kwargs.get('summary_only') for call in daily.call_args_list))
  for result in (summary,full):
   self.assertEqual(result['dividends'],full['dividends'])
   self.assertEqual([{k:p[k] for k in ('symbol','cost','value','realised','dividend')} for p in result['positions']], [{k:p[k] for k in ('symbol','cost','value','realised','dividend')} for p in full['positions']])
 def test_summary_replays_sales_and_splits_with_the_same_cost_basis(self):
  from history import daily_values
  lots=[dict(purchased_on='2016-01-01',quantity='2',price='100',side='BUY',split_before=''),
        dict(purchased_on='2026-10-01',quantity='4',price='1',side='BUY',split_before='2'),
        dict(purchased_on='2026-10-02',quantity='1',price='120',side='SELL',split_before='')]
  full=daily_values(lots,[],[],date(2026,10,3))
  summary=daily_values(lots,[],[],date(2026,10,3),summary_only=True)
  self.assertEqual(summary,[full[-1]]);self.assertEqual(summary[0]['cost'],'150');self.assertEqual(summary[0]['realised'],'70')
 def test_summary_does_not_wait_for_the_provider_writer_lock(self):
  import threading
  snapshot=self.store.state();held=threading.Event();release=threading.Event();done=threading.Event();errors=[]
  def provider():
   with self.store.lock:held.set();release.wait(3)
  def reader():
   try:combined(self.store,snapshot,today=date(2026,10,3))
   except Exception as error:errors.append(error)
   finally:done.set()
  writer=threading.Thread(target=provider);writer.start();self.assertTrue(held.wait(1));request=threading.Thread(target=reader);request.start()
  try:self.assertTrue(done.wait(1),'The report waited for the provider writer lock')
  finally:release.set();writer.join();request.join()
  self.assertEqual(errors,[])
 def test_invalid_source_positions_are_excluded_without_changing_good_rows(self):
  for field,bad in [('value',None),('cost','NaN'),('realised','Infinity'),('dividend','bad'),('quantity','')]:
   for full in (False,True):
    snapshot=self.store.state();snapshot['positions'][0][field]=bad;before=deepcopy(snapshot)
    result=combined(self.store,snapshot,today=date(2026,10,3),include_history=full)
    self.assertEqual(len(result['positions']),2,(field,full));self.assertEqual(result['excluded'][0]['symbol'],snapshot['positions'][0]['symbol'])
    self.assertEqual(len(result['dividends']),3);self.assertEqual(snapshot,before)
 def test_bad_trade_or_history_does_not_abort_the_other_positions(self):
  for kind in ('trade','history'):
   snapshot=self.store.state();symbol=snapshot['positions'][0]['symbol']
   if kind=='trade':
    next(row for row in snapshot['purchases'] if row['symbol']==symbol)['price']='NaN'
   else:snapshot['positions'][0]['history']=[]
   result=combined(self.store,snapshot,today=date(2026,10,3))
   self.assertEqual(len(result['positions']),2);self.assertEqual(result['excluded'][0]['symbol'],symbol)
 def test_invalid_dividend_rows_are_excluded_independently(self):
  for field,bad in [('amount','NaN'),('amount','Infinity'),('amount','bad'),('paid_on','2026-99-01')]:
   snapshot=self.store.state();snapshot['dividends'][0][field]=bad
   result=combined(self.store,snapshot,today=date(2026,10,3))
   self.assertEqual(len(result['dividends']),2);self.assertEqual(len(result['missing_dividends']),1)
   self.assertEqual(len(result['positions']),2)
import test_transactions as report_http_support
class CombinedReportHttpTests(unittest.TestCase):
 setUp=report_http_support.TransactionHttpTests.setUp
 tearDown=report_http_support.TransactionHttpTests.tearDown
 request=report_http_support.TransactionHttpTests.request
 def test_combined_endpoint_cache_and_account_validation(self):
  status,result=self.request('/api/reports/combined?history=1')
  self.assertEqual(status,200);self.assertEqual(result['positions'],[]);self.assertEqual(len(result['excluded']),1)
  self.assertIn('history',result);self.assertIn('data_revision',result)
  self.assertEqual(self.request('/api/reports/combined?account_id=999')[0],400)
  self.assertEqual(self.request('/api/reports/combined?instrument=%5B1%5D')[0],400)

 def test_primary_stylesheet_contains_report_layout(self):
  status,css=self.request('/style.css?v=test')
  self.assertEqual(status,200);self.assertIn(b'.report-metric-heading{grid-column:1/-1',css)
  self.assertIn(b'.payment-grid',css)
