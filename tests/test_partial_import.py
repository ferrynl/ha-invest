import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,open_preview
from imports.partial import commit_partial,list_issues,resolve_issue
from imports.registry import remember,edit,discover
from restore import restore_backup

HEADER='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total)\n'
BUY='Market buy,2026-10-01 10:00:00,NL0010273215,ASML,ASML,buy-ok,1,100,EUR,100,EUR\n'
MISSING='Market buy,2026-10-02 10:00:00,UNKNOWN00001,SAB,Unknown,buy-missing,1,10,EUR,10,EUR\n'
CAPITAL='Dividend (Return of capital manufactured payment),2026-10-03 10:00:00,NO0010921918,HSHP,Hafnia,capital-1,,,,5,USD\n'
SELL='Market sell,2026-10-04 10:00:00,NL0010273215,ASML,ASML,sell-bad,5,120,EUR,600,EUR\n'
STOCK=dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')
class PartialTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
 def batch(self,text):
  result=preview(self.store,2,'trading212','partial.csv',HEADER+text)
  for row in result['rows']:
   if row.get('ticker')=='ASML':remember(self.store,2,'trading212',row,STOCK)
  return result['batch_id']
 def test_valid_row_imports_and_errors_are_durable_and_idempotent(self):
  batch=self.batch(BUY+MISSING+CAPITAL+SELL);result=commit_partial(self.store,batch)
  self.assertEqual((result['imported'],result['pending']),(2,2))
  self.assertEqual(len(self.store.state()['purchases']),1)
  self.assertEqual(len(list_issues(Store(self.tmp.name))['issues']),2)
  again=commit_partial(Store(self.tmp.name),batch)
  self.assertEqual((again['imported'],again['pending']),(0,2))
  self.assertEqual(len(self.store.state()['purchases']),1)
 def test_capital_return_imports_automatically_and_never_becomes_dividend_profit(self):
  batch=self.batch(BUY+CAPITAL);result=commit_partial(self.store,batch)
  self.assertEqual((result['imported'],result['pending']),(2,0))
  self.assertEqual(self.store.state()['dividends'],[])
  returns=list_issues(self.store)['capital_returns'];self.assertEqual(returns[0]['amount'],'5')
  self.assertEqual(returns[0]['currency'],'USD')
  second=self.batch(CAPITAL)
  self.assertEqual(commit_partial(self.store,second)['imported'],0)
  self.assertEqual(len(list_issues(self.store)['capital_returns']),1)
 def test_missing_mapping_can_be_fixed_and_retried_without_reimporting_good_rows(self):
  batch=self.batch(BUY+MISSING);commit_partial(self.store,batch)
  issue=list_issues(self.store)['issues'][0]
  row=next(r for r in open_preview(self.store,batch)['rows'] if r['ticker']=='SAB')
  remember(self.store,2,'trading212',row,dict(symbol='SAB.MC',exchange='MADRID',currency='EUR',name='Sabadell'))
  result=resolve_issue(self.store,dict(id=issue['id'],decision='retry'))
  self.assertEqual((result['imported'],result['pending']),(1,0))
  self.assertEqual(len(self.store.state()['purchases']),2)
 def test_ignore_preserves_raw_and_does_not_create_financial_rows(self):
  batch=self.batch(CAPITAL.replace('Dividend (Return of capital manufactured payment)','Unknown action'));commit_partial(self.store,batch)
  issue=list_issues(self.store)['issues'][0]
  result=resolve_issue(self.store,dict(id=issue['id'],decision='IGNORE'))
  self.assertEqual(result['pending'],0)
  self.assertEqual(self.store.state()['dividends'],[])
  self.assertEqual(list_issues(self.store)['capital_returns'],[])
  self.assertEqual(list_issues(self.store)['issues'][0]['state'],'ignored')
  with self.store.connect() as db:raw=json.loads(db.execute('SELECT raw FROM import_records').fetchone()[0])
  self.assertEqual(raw['Action'],'Unknown action')
 def test_fx_failure_isolated_and_cannot_leave_half_booked_rows(self):
  batch=self.batch(BUY+MISSING)
  row=next(r for r in open_preview(self.store,batch)['rows'] if r['ticker']=='SAB')
  remember(self.store,2,'trading212',row,dict(symbol='OTHER',exchange='NYSE',currency='USD',name='Test'))
  with patch('imports.partial.prepare_rates',side_effect=ValueError('Geen dagkoers')):result=commit_partial(self.store,batch)
  self.assertEqual((result['imported'],result['pending']),(1,1))
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM import_records').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM import_fx').fetchone()[0],0)
 def test_pending_and_capital_data_survive_backup_restore(self):
  batch=self.batch(CAPITAL+MISSING);commit_partial(self.store,batch)
  restore_backup(self.store,self.store.backup().read_bytes())
  data=list_issues(self.store)
  self.assertEqual(len(data['capital_returns']),1)
  self.assertEqual(sum(i['state']=='pending' for i in data['issues']),1)
 def test_registry_correction_cannot_rewrite_already_booked_rows_in_partial_batch(self):
  batch=self.batch(BUY+MISSING);commit_partial(self.store,batch)
  entry=next(m for m in discover(self.store) if m['ticker']=='ASML')
  updated={**STOCK,'symbol':'ASML.DE','exchange':'XETRA'}
  with patch('imports.registry.listing',return_value=updated):edit(self.store,dict(id=entry['id'],**updated))
  with self.store.connect() as db:rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(batch,)).fetchone()[0])
  self.assertEqual(rows[0]['mapping']['symbol'],'ASML.AS')
  self.assertEqual(self.store.state()['purchases'][0]['symbol'],'ASML.AS')
 def test_same_source_id_conflict_is_quarantined_before_either_is_booked(self):
  batch=self.batch(BUY+BUY.replace(',100,EUR,100,',',200,EUR,200,'))
  result=commit_partial(self.store,batch)
  self.assertEqual((result['imported'],result['pending']),(0,2))
  self.assertEqual(self.store.state()['purchases'],[])

class ImportQuantityDiagnosticsTests(unittest.TestCase):
 setUp=PartialTests.setUp
 batch=PartialTests.batch
 def test_sell_rejection_logs_exact_quantities_and_summary(self):
  from diagnostics import read_logs
  batch=self.batch(BUY+SELL);commit_partial(self.store,batch)
  entries=read_logs(self.store)['entries']
  rejection=next(e for e in entries if e['event']=='import_row_rejected')
  self.assertEqual(rejection['details']['code'],'sell_exceeds_holdings')
  self.assertEqual(rejection['details']['held_quantity'],'1')
  self.assertEqual(rejection['details']['sell_quantity'],'5')
  self.assertEqual(rejection['details']['difference'],'4')
  self.assertEqual(rejection['details']['batch_id'],batch)
  summary=next(e for e in entries if e['event']=='import_summary')
  self.assertEqual(summary['details']['pending'],1)
  self.assertEqual(summary['details']['imported'],1)
  self.assertNotIn('raw',str(rejection['details']))
 def test_fractional_round_trip_returns_plain_zero_without_losing_shares(self):
  buy=BUY.replace(',1,100,',',0.26314172,100,')
  sell=SELL.replace(',5,120,',',0.26314172,120,')
  batch=self.batch(buy+sell);result=commit_partial(self.store,batch)
  self.assertEqual(result['pending'],0)
  self.assertEqual(self.store.state()['positions'][0]['quantity'],'0')
  self.assertEqual(self.store.state()['purchases'][0]['quantity'],'0.26314172')
