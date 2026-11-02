import sys,tempfile,unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from home_euro import build,overview
class HomeEuroTests(unittest.TestCase):
 def test_237_positions_reuse_daily_fx_and_keep_only_selected_position_points(self):
  import home_euro
  from datetime import timedelta
  end=date(2026,11,2);start=end-timedelta(days=730)
  days=[(start+timedelta(days=i)).isoformat() for i in range(731)]
  points=[dict(day=day,cost='100',invested='100',quantity='1',realised='0',dividend='0',value='110',price='110',total_gain='10',carried=False) for day in days]
  snapshot=dict(accounts=[dict(id=1)],positions=[],purchases=[],dividends=[])
  for i in range(237):
   currency=['EUR','USD','GBP'][i%3];key=dict(account_id=1,symbol='LOAD'+str(i),exchange='TEST',currency=currency)
   history=points if i<236 else [dict(p,value=None,price=None,total_gain=None) for p in points]
   snapshot['positions'].append(dict(**key,name='Test',account_name='Test',quantity='1',cost='100',value='110' if i<236 else None,realised='0',dividend='0',history=history))
   snapshot['purchases'].append(dict(**key,purchased_on=days[0],price='100',quantity='1',split_before='',side='BUY'))
  rates=[dict(base='EUR',quote=currency,day=day,rate=rate) for currency,rate in [('USD','1.1'),('GBP','0.8')] for day in days]
  with patch('home_euro.unit',wraps=home_euro.unit) as conversions:
   result=build(snapshot,rates,today=end,retain_history=False)
  self.assertLessEqual(conversions.call_count,3*len(days))
  self.assertEqual(len(result['positions']),237);self.assertTrue(all(len(p['history'])==1 for p in result['positions']))
  self.assertEqual(len(result['portfolios'][0]['history']),731);self.assertEqual(result['portfolios'][0]['history'][-1]['missing'],1)
  summary=build(snapshot,rates,today=end,include_history=False)
  for actual,expected in zip(summary['positions'],result['positions']):
   for field in ('value','cost','total_gain','dividend'):self.assertEqual(actual[field],expected[field])
 def test_summary_does_not_replay_daily_history_and_matches_full_totals(self):
  import home_euro
  original=home_euro.daily_values;snapshot=self.store.state()
  full=build(snapshot,self.rates,today=date(2026,10,3))
  with patch('home_euro.daily_values',wraps=original) as replay:
   summary=build(snapshot,self.rates,today=date(2026,10,3),include_history=False)
  self.assertTrue(all(call.kwargs.get('summary_only') for call in replay.call_args_list))
  self.assertEqual(len(summary['portfolios'][0]['history']),1)
  for field in ('value','cost','total_gain','dividend','realised'):
   self.assertEqual(Decimal(summary['positions'][0][field]),Decimal(full['positions'][0][field]))
 def test_streamed_chart_matches_full_history_without_retaining_position_days(self):
  snapshot=self.store.state()
  full=build(snapshot,self.rates,today=date(2026,10,3))
  chart=build(snapshot,self.rates,today=date(2026,10,3),retain_history=False)
  self.assertEqual(chart['portfolios'],full['portfolios'])
  self.assertEqual(len(chart['positions'][0]['history']),1)
  self.assertGreater(len(full['positions'][0]['history']),1)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.stock=dict(symbol='TEST',exchange='NYSE',currency='USD',name='Test')
  self.store.add(dict(**self.stock,quantity='2',price='100',purchased_on='2026-10-01'))
  self.store.add(dict(**self.stock,quantity='1',price='120',purchased_on='2026-10-02',side='SELL'))
  self.store.add_dividend(dict(symbol='TEST',exchange='NYSE',currency='USD',amount='10',paid_on='2026-10-02'))
  self.store.quote('TEST','NYSE','USD','150','2026-10-03T10:00:00+00:00','test')
  self.rates=[dict(base='EUR',quote='USD',day=day,rate=rate) for day,rate in [('2026-10-01','2'),('2026-10-02','4'),('2026-10-03','1')]]
 def test_cashflows_use_their_own_dates_not_current_rate(self):
  original=self.store.state();result=build(original,self.rates,today=date(2026,10,3));p=result['positions'][0]
  self.assertEqual(Decimal(p['cost']),50);self.assertEqual(Decimal(p['realised']),-20);self.assertEqual(Decimal(p['dividend']),Decimal('2.5'));self.assertEqual(Decimal(p['value']),150);self.assertEqual(Decimal(p['total_gain']),Decimal('82.5'))
  self.assertEqual(p['currency'],'EUR');self.assertEqual(p['native_currency'],'USD');self.assertEqual(original['positions'][0]['currency'],'USD');self.assertEqual(Decimal(p['history'][-1]['invested']),100)
  self.assertEqual(Decimal(result['portfolios'][0]['history'][-1]['invested']),100)
 def test_missing_fx_is_excluded_and_future_rates_never_used(self):
  result=build(self.store.state(),[dict(base='EUR',quote='USD',day='2026-10-04',rate='1')],today=date(2026,10,3))
  self.assertEqual(result['positions'],[]);self.assertEqual(result['excluded'][0]['symbol'],'TEST');self.assertIn('2026-10-01',result['excluded'][0]['dates'])
 def test_eur_and_pence_share_total_without_one_to_one_fallback(self):
  self.store.add(dict(symbol='EUR',exchange='AMSTERDAM',currency='EUR',name='Euro',quantity='1',price='50',purchased_on='2026-10-01'))
  self.store.quote('EUR','AMSTERDAM','EUR','60','2026-10-03T10:00:00+00:00','test')
  self.store.add(dict(symbol='GBX',exchange='LONDON',currency='GBX',name='Pence',quantity='10',price='100',purchased_on='2026-10-01'))
  self.store.quote('GBX','LONDON','GBX','200','2026-10-03T10:00:00+00:00','test')
  rates=self.rates+[dict(base='EUR',quote='GBP',day='2026-10-01',rate='.8')]
  result=build(self.store.state(),rates,today=date(2026,10,3));p=next(p for p in result['positions'] if p['symbol']=='GBX')
  self.assertEqual(Decimal(p['value']),25);self.assertEqual(Decimal(p['cost']),Decimal('12.5'));self.assertEqual(Decimal(result['portfolios'][0]['history'][-1]['value']),235)
 def test_scope_and_fx_failure_preserve_available_amounts(self):
  self.store.add_account(dict(name='Other',broker='Test'))
  self.store.add(dict(symbol='EUR',exchange='AMSTERDAM',currency='EUR',name='Euro',quantity='1',price='50',purchased_on='2026-10-01',account_id=2))
  result=build(self.store.state(),self.rates,'2',date(2026,10,3));self.assertEqual([p['symbol'] for p in result['positions']],['EUR'])
  for account in ['bad','999']:
   with self.assertRaises(ValueError):build(self.store.state(),self.rates,account)
  with patch('home_euro.prepare_rates',side_effect=ValueError('unavailable')):
   result=overview(self.store,self.store.state())
  self.assertEqual(len(result['positions']),1);self.assertEqual(result['excluded'][0]['currency'],'USD')
 def test_missing_quote_does_not_erase_other_market_values(self):
  self.store.add(dict(symbol='EUR',exchange='AMSTERDAM',currency='EUR',name='Euro',quantity='1',price='50',purchased_on='2026-10-01'))
  result=build(self.store.state(),self.rates,today=date(2026,10,3));self.assertEqual(Decimal(result['portfolios'][0]['history'][-1]['value']),150);self.assertEqual(result['portfolios'][0]['history'][-1]['missing'],1)
  point=result['portfolios'][0]['history'][-1]
  self.assertEqual(Decimal(point['invested']),150)
  self.assertEqual(Decimal(point['return_invested']),100)
  self.assertEqual(Decimal(point['return_gain']),Decimal('82.5'))
 def test_all_missing_returns_no_fabricated_profit(self):
  snapshot=self.store.state()
  for p in snapshot['positions']:
   p['value']=None
   for day in p['history']:day.update(value=None,total_gain=None)
  result=build(snapshot,self.rates,today=date(2026,10,3))
  point=result['portfolios'][0]['history'][-1]
  self.assertIsNone(point['return_gain']);self.assertEqual(Decimal(point['return_invested']),0)
 def test_missing_usd_quote_keeps_eur_profit_visible(self):
  self.store.add(dict(symbol='EUR',exchange='AMSTERDAM',currency='EUR',name='Euro',quantity='1',price='50',purchased_on='2026-10-01'))
  self.store.quote('EUR','AMSTERDAM','EUR','60','2026-10-03T10:00:00+00:00','test')
  snapshot=self.store.state();usd=next(p for p in snapshot['positions'] if p['currency']=='USD');usd['value']=None
  for day in usd['history']:day.update(value=None,total_gain=None)
  point=build(snapshot,self.rates,today=date(2026,10,3))['portfolios'][0]['history'][-1]
  self.assertEqual(point['missing'],1);self.assertEqual(Decimal(point['return_gain']),10);self.assertEqual(Decimal(point['return_invested']),50)
 def test_native_partial_profit_keeps_matching_denominator(self):
  from history import portfolio_values
  day=dict(day='2026-10-03',cost='50',invested='100',value='120',dividend='5',realised='10',total_gain='85',carried=False)
  missing=dict(day,cost='200',invested='300',value=None,total_gain=None)
  group=portfolio_values([dict(currency='EUR',history=[day]),dict(currency='EUR',history=[missing])])[0]
  point=group['history'][0]
  self.assertIsNone(point['total_gain']);self.assertEqual(point['missing'],1)
  self.assertEqual(Decimal(point['return_invested']),100);self.assertEqual(Decimal(point['return_gain']),85)

import test_transactions as transaction_test_support
class HomeEuroHttpTests(unittest.TestCase):
 setUp=transaction_test_support.TransactionHttpTests.setUp
 tearDown=transaction_test_support.TransactionHttpTests.tearDown
 request=transaction_test_support.TransactionHttpTests.request
 def test_authentication_and_invalid_scope_are_enforced(self):
  with patch('home_euro.prepare_rates') as rates:
   self.assertEqual(self.request('/api/home/euro?account_id=all')[0],200)
   rates.reset_mock();self.assertEqual(self.request('/api/home/euro?account_id=999')[0],400);rates.assert_not_called()
  self.auth.enable('owner','Long-test-password-2026');self.assertEqual(self.request('/api/home/euro')[0],401)
