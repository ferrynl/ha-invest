import sys,tempfile,unittest,json
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from imports.revolut import parse_csv
from imports.service import preview,open_preview
from imports.partial import commit_partial,list_issues,refresh_supported
from imports.registry import remember
from storage import Store

HEADER='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n'
def entry(action,ticker='TEST',quantity='',price='',amount='USD 0',currency='USD',day='2025-12-18'):
 return f'{day}T10:00:00Z,{ticker},{action},{quantity},{price},{amount},{currency}\n'

class RevolutActionTests(unittest.TestCase):
 def setUp(self):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.store=Store(folder.name)
  self.store.add_account(dict(name='Test',broker='Revolut'))
 def batch(self,text):return preview(self.store,2,'revolut','synthetic.csv',HEADER+text)
 def map(self,batch):
  for row in batch['rows']:
   if row.get('kind') in ('BUY','SELL','SPLIT','DIVIDEND'):
    remember(self.store,2,'revolut',row,dict(symbol=row['ticker'],name='Test',currency=row['currency'],exchange='NYSE'))
 def test_custody_and_exact_tax_correction_pair_are_skipped(self):
  text=entry('CUSTODY FEE',ticker='',amount='USD -0.02')+entry('DIVIDEND TAX (CORRECTION)',amount='USD -0.05')+entry('DIVIDEND TAX (CORRECTION)',amount='USD 0.05')
  batch=self.batch(text);self.assertEqual([r['kind'] for r in batch['rows']],['SKIP']*3)
  result=commit_partial(self.store,batch['batch_id']);self.assertEqual((result['imported'],result['pending']),(0,0))
  self.assertEqual(self.store.state()['dividends'],[])
 def test_unpaired_tax_mismatches_and_malformed_rows_stay_pending(self):
  for other in (None,dict(amount='USD 0.04'),dict(ticker='OTHER',amount='USD 0.05'),dict(currency='EUR',amount='EUR 0.05'),dict(day='2025-12-19',amount='USD 0.05')):
   text=entry('DIVIDEND TAX (CORRECTION)',amount='USD -0.05')+(entry('DIVIDEND TAX (CORRECTION)',**other) if other else '')
   self.assertTrue(all(r['error'] for r in parse_csv(HEADER+text)))
  malformed=HEADER+entry('DIVIDEND TAX (CORRECTION)',amount='USD -0.05').rstrip()+',extra\n'+entry('DIVIDEND TAX (CORRECTION)',amount='USD 0.05')
  self.assertTrue(all(r['error'] for r in parse_csv(malformed)))
 def test_return_of_capital_is_separate_from_dividend(self):
  batch=self.batch(entry('RETURN OF CAPITAL',amount='EUR 0.12',currency='EUR'))
  self.assertEqual(batch['rows'][0]['kind'],'CAPITAL_RETURN');self.assertEqual(batch['instruments'],[])
  result=commit_partial(self.store,batch['batch_id']);self.assertEqual((result['imported'],result['pending']),(1,0))
  self.assertEqual(self.store.state()['dividends'],[])
  self.assertEqual(list_issues(self.store)['capital_returns'][0]['amount'],'0.12')
  again=self.batch(entry('RETURN OF CAPITAL',amount='EUR 0.12',currency='EUR'))
  self.assertEqual(commit_partial(self.store,again['batch_id'])['imported'],0)
 def test_merger_keeps_cash_and_negative_stock_for_review(self):
  batch=self.batch(entry('MERGER - CASH',amount='USD 1.25')+entry('MERGER - STOCK',quantity='-3'))
  result=commit_partial(self.store,batch['batch_id']);self.assertEqual((result['imported'],result['pending']),(0,2))
  issues=list_issues(self.store)['issues'];self.assertEqual({r['action'] for r in issues},{'MERGER - CASH','MERGER - STOCK'})
  self.assertTrue(all('Fusie:' in r['reason'] for r in issues));self.assertEqual(self.store.state()['purchases'],[])
 def test_confirmed_split_preserves_cost_and_rejects_incomplete_holdings(self):
  buy=entry('BUY',ticker='NOW',quantity='0.1',price='USD 500',amount='USD 50',day='2025-12-01')
  batch=self.batch(buy+entry('STOCK SPLIT',ticker='NOW',quantity='0.4'))
  self.map(batch);result=commit_partial(self.store,batch['batch_id'])
  self.assertEqual((result['imported'],result['pending']),(2,0))
  position=self.store.state()['positions'][0]
  self.assertEqual(Decimal(position['quantity']),Decimal('.5'));self.assertEqual(Decimal(position['cost']),50)
  again=self.batch(buy+entry('STOCK SPLIT',ticker='NOW',quantity='0.4'))
  self.assertEqual(commit_partial(self.store,again['batch_id'])['imported'],0)
  mismatch=self.batch(entry('STOCK SPLIT',ticker='NOW',quantity='0.3'))
  self.assertEqual(commit_partial(self.store,mismatch['batch_id'])['pending'],1)
  self.assertEqual(Decimal(self.store.state()['positions'][0]['quantity']),Decimal('.5'))
 def test_split_without_holdings_and_unknown_split_are_not_guessed(self):
  batch=self.batch(entry('STOCK SPLIT',ticker='NOW',quantity='0.4'));self.map(batch)
  self.assertEqual(commit_partial(self.store,batch['batch_id'])['pending'],1)
  self.assertTrue(parse_csv(HEADER+entry('STOCK SPLIT',ticker='UNKNOWN',quantity='0.4'))[0]['error'])
 def test_old_failed_rows_refresh_but_explicit_decisions_are_preserved(self):
  rows=parse_csv(HEADER+entry('CUSTODY FEE',ticker='',amount='USD -0.02')+entry('RETURN OF CAPITAL',amount='USD 0.12'))
  original=[r['external_id'] for r in rows]
  for row in rows:row.update(kind=None,error='legacy')
  refresh_supported(rows,'revolut')
  self.assertEqual([r['kind'] for r in rows],['SKIP','CAPITAL_RETURN']);self.assertEqual([r['external_id'] for r in rows],original)
  rows[1].update(kind='SKIP',decision='IGNORE',error='manual')
  refresh_supported(rows,'revolut');self.assertEqual(rows[1]['decision'],'IGNORE');self.assertEqual(rows[1]['error'],'manual')
