import sys,tempfile,unittest
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from stocks_dashboard import overview
from instruments import save_categories,details
STOCK=dict(symbol='TEST',exchange='NYSE',currency='USD',name='Testbedrijf')
class StocksDashboardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Second',broker='Other'))
  for owner,quantity in [(1,'2'),(2,'3')]:self.store.add(dict(**STOCK,account_id=owner,quantity=quantity,price='100',purchased_on='2026-10-01'))
  self.store.add_dividend(dict(symbol='TEST',exchange='NYSE',currency='USD',account_id=2,amount='10',paid_on='2026-10-02'))
  self.store.quote('TEST','NYSE','USD','120','2026-10-22T10:00:00+00:00','test')
 def test_one_listing_sums_all_accounts_and_uses_fresh_categories(self):
  snapshot=self.store.state();save_categories(self.store,dict(**STOCK,sector='Technologie',country='Verenigde Staten',asset_type='Aandeel'))
  result=overview(self.store,snapshot);self.assertEqual(len(result['positions']),1);p=result['positions'][0]
  self.assertEqual(Decimal(p['quantity']),5);self.assertEqual(Decimal(p['value']),600);self.assertEqual(Decimal(p['cost']),500);self.assertEqual(Decimal(p['dividend']),10);self.assertEqual(Decimal(p['total_gain']),110);self.assertEqual(p['broker_count'],2);self.assertEqual(p['categories']['sector'],'Technologie');self.assertEqual(result['accounts'],2)
  self.assertEqual({event['account_id'] for event in details(self.store,STOCK)['events']},{1,2})
 def test_different_exchange_or_currency_stays_distinct_and_unknown_quote_is_not_zero(self):
  self.store.add(dict(**{**STOCK,'exchange':'AMSTERDAM','currency':'EUR'},quantity='1',price='50',purchased_on='2026-10-01'))
  result=overview(self.store,self.store.state());self.assertEqual(len(result['positions']),2)
  p=next(p for p in result['positions'] if p['currency']=='EUR');self.assertIsNone(p['value']);self.assertIsNone(p['total_gain'])
 def test_broker_scope_filters_money_quantity_dividend_and_categories_without_mutating_snapshot(self):
  snapshot=self.store.state()
  for account,quantity,value,cost,dividend,gain in [(1,'2','240','200','0','40'),(2,'3','360','300','10','70')]:
   result=overview(self.store,snapshot,str(account));p=result['positions'][0]
   self.assertEqual(result['account_id'],str(account));self.assertEqual(result['accounts'],1)
   self.assertEqual((p['quantity'],p['value'],p['cost'],p['dividend'],p['total_gain']),(quantity,value,cost,dividend,gain))
   self.assertEqual(p['broker_count'],1)
  self.assertEqual(len(snapshot['positions']),2)
  self.assertEqual(overview(self.store,snapshot)['positions'][0]['quantity'],'5')
  with self.assertRaises(ValueError):overview(self.store,snapshot,'999')
  with self.assertRaises(ValueError):overview(self.store,snapshot,'not-an-account')

import test_transactions as transaction_test_support
class StocksDashboardHttpTests(unittest.TestCase):
 setUp=transaction_test_support.TransactionHttpTests.setUp
 tearDown=transaction_test_support.TransactionHttpTests.tearDown
 request=transaction_test_support.TransactionHttpTests.request
 def test_read_endpoint_requires_login_and_validates_broker_filter(self):
  self.assertEqual(self.request('/api/stocks?account_id=999')[0],400)
  self.assertEqual(self.request('/api/stocks?account_id=bad')[0],400)
  self.assertEqual(self.request('/api/stocks?account_id=1')[1]['account_id'],'1')
  self.auth.enable('owner','Long-test-password-2026');self.assertEqual(self.request('/api/stocks')[0],401)
 def test_same_broker_scope_is_applied_to_home_stocks_and_dividend(self):
  self.store.add_account(dict(name='Other broker',broker='Trading 212'))
  self.store.add(dict(symbol='OTHER',exchange='AMSTERDAM',currency='EUR',name='Other stock',account_id=2,quantity='4',price='50',purchased_on='2026-10-01'))
  self.store.add_dividend(dict(symbol='OTHER',exchange='AMSTERDAM',currency='EUR',account_id=2,amount='12',paid_on='2026-10-02'))
  for account,symbol,received in [('1','ASML.AS','0'),('2','OTHER','12')]:
   home=self.request('/api/state?account_id='+account)[1]
   stocks=self.request('/api/stocks?account_id='+account)[1]
   dividends=self.request('/api/dividends/overview?account_id='+account)[1]
   self.assertEqual({p['symbol'] for p in home['positions']},{symbol})
   self.assertEqual({p['symbol'] for p in stocks['positions']},{symbol})
   self.assertEqual(dividends['account_id'],account)
   self.assertEqual(dividends['currencies'][0]['total'],received)
