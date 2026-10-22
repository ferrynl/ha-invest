import sys,tempfile,unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from home_euro import build,overview
class HomeEuroTests(unittest.TestCase):
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
