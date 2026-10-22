from contextlib import closing
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,commit
from imports.partial import commit_partial,list_issues,resolve_issue
from imports.registry import remember
from imports.trading212 import parse_csv
from migrations import MIGRATIONS,migrate
from restore import restore_backup

HEADER='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total)\n'
BUY='Market buy,2026-10-01 10:00:00,NL0010273215,ASML,ASML,buy,2,100,EUR,200,EUR\n'
CLOSE='Stock split close,2026-10-02 10:00:00,NL0010273215,ASML,ASML,close,2,0,EUR,0,EUR\n'
OPEN='Stock split open,2026-10-02 10:00:00,NL0010273215,ASML,ASML,open,4,0,EUR,0,EUR\n'
CAPITAL='Dividend (Return of capital manufactured payment),2026-10-03 10:00:00,NL0010273215,ASML,ASML,capital,,,,5,USD\n'
STOCK=dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')

class CorporateActionsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.store=Store(self.tmp.name);self.store.add_account(dict(name='Broker',broker='Trading 212'))
 def batch(self,text):
  result=preview(self.store,2,'trading212','actions.csv',HEADER+text)
  for row in result['rows']:
   if row.get('currency'):remember(self.store,2,'trading212',row,STOCK)
  return result['batch_id']
 def test_split_preserves_cost_investment_and_realised_profit_after_sale(self):
  sell='Market sell,2026-10-03 10:00:00,NL0010273215,ASML,ASML,sell,1,75,EUR,75,EUR\n'
  result=commit_partial(self.store,self.batch(BUY+CLOSE+OPEN+sell))
  self.assertEqual(result['pending'],0)
  point=self.store.state()['positions'][0]['history'][-1]
  self.assertEqual(tuple(float(point[k]) for k in ('quantity','cost','invested','realised')),(3,150,200,25))
  self.assertEqual(len(self.store.state()['purchases']),3)
  self.assertEqual(commit_partial(self.store,self.batch(BUY+CLOSE+OPEN+sell))['imported'],0)
 def test_reverse_split_and_open_without_close(self):
  result=commit_partial(self.store,self.batch(BUY+OPEN.replace(',4,0,',',1,0,')))
  self.assertEqual(result['pending'],0)
  point=self.store.state()['positions'][0]['history'][-1]
  self.assertEqual((float(point['quantity']),float(point['cost'])),(1,200))
 def test_missing_holdings_and_mismatched_close_leave_no_half_booking(self):
  for text in (OPEN,BUY+CLOSE.replace(',2,0,',',3,0,')+OPEN):
   with self.subTest(text=text):
    batch=self.batch(text);result=commit_partial(self.store,batch)
    self.assertEqual(result['pending'],1)
    self.assertFalse(any(p['split_before'] for p in self.store.state()['purchases']))
    with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM import_records WHERE external_id='id:open:UNCLASSIFIED'").fetchone()[0],0)
 def test_capital_has_no_fx_requirement_and_survives_restore_with_split(self):
  with patch('imports.partial.prepare_rates',side_effect=AssertionError('No FX needed')):
   result=commit_partial(self.store,self.batch(BUY+CLOSE+OPEN+CAPITAL))
  self.assertEqual(result['pending'],0)
  restore_backup(self.store,self.store.backup().read_bytes())
  self.assertEqual(self.store.state()['dividends'],[])
  self.assertEqual(list_issues(self.store)['capital_returns'][0]['currency'],'USD')
  self.assertEqual(float(self.store.state()['positions'][0]['quantity']),4)
 def test_atomic_import_supports_capital_and_split(self):
  result=commit(self.store,self.batch(BUY+CLOSE+OPEN+CAPITAL),{})
  self.assertEqual(result['imported'],3)
  self.assertEqual(float(self.store.state()['positions'][0]['cost']),200)
 def test_existing_manual_classification_is_not_rebooked_as_capital(self):
  batch=self.batch(CAPITAL.replace("USD","EUR"))
  with self.store.connect() as db:
   row=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(batch,)).fetchone()[0])[0]
   row.update(kind=None,error='Onbekend',decision='retry')
   db.execute('UPDATE import_batches SET payload=?,status=? WHERE id=?',(json.dumps([row]),'partial',batch))
   db.execute("INSERT INTO import_issues(batch_id,line,state,reason,payload,updated_at) VALUES(?,?,'pending','Onbekend',?,'2026-10-03T00:00:00+00:00')",(batch,row['line'],json.dumps(row)))
   issue_id=db.execute('SELECT id FROM import_issues').fetchone()[0]
  resolve_issue(self.store,dict(id=issue_id,decision='DIVIDEND'))
  result=commit_partial(self.store,self.batch(CAPITAL.replace("USD","EUR")))
  self.assertEqual(result['imported'],0)
  self.assertEqual(len(self.store.state()['dividends']),1)
  self.assertEqual(list_issues(self.store)['capital_returns'],[])
 def test_split_cannot_use_holdings_from_another_broker_account(self):
  self.store.add(dict(account_id=1,**STOCK,quantity='2',price='100',purchased_on='2026-10-01'))
  result=commit_partial(self.store,self.batch(OPEN))
  self.assertEqual(result['pending'],1)
  self.assertEqual(len(self.store.state()['purchases']),1)
 def test_legacy_rejected_rows_retry_and_keep_identity(self):
  batch=self.batch(BUY+CLOSE+OPEN+CAPITAL)
  with self.store.connect() as db:
   rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(batch,)).fetchone()[0])
   for row in rows[1:]:row.update(kind=None,error='Dit transactietype wordt nog niet ondersteund')
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch))
  result=commit_partial(self.store,batch)
  self.assertEqual(result['pending'],0)
  self.assertEqual(commit_partial(self.store,self.batch(CAPITAL))['imported'],0)
 def test_malformed_and_ambiguous_pairs_remain_reviewable(self):
  for text in (CLOSE,CLOSE+OPEN+OPEN.replace(',open,',',open-2,'),CLOSE.replace(',2,0,',',NaN,0,')+OPEN):
   self.assertTrue(any(r['error'] for r in parse_csv(HEADER+text)))
 def test_capital_conflicts_and_identical_payments_without_id_stay_reviewable(self):
  capital=CAPITAL.replace(',capital,',',,')
  result=commit_partial(self.store,self.batch(capital+capital))
  self.assertEqual(result['pending'],1)
  result=commit_partial(self.store,self.batch(CAPITAL+CAPITAL.replace(',5,USD',',6,USD')))
  self.assertEqual(result['pending'],2)
 def test_schema_ten_upgrade_preserves_rows_and_rolls_back_failures(self):
  for failed in (True,False):
   with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'portfolio.sqlite3'
    with closing(sqlite3.connect(path)) as db, db:
     for version in range(1,11):
      for statement in MIGRATIONS[version]:db.execute(statement)
     db.execute('PRAGMA user_version=10')
     db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES('ASML.AS','AMSTERDAM','ASML','2','100','EUR','2026-10-01','2026-10-01T00:00:00+00:00')")
    if failed:
     with patch.dict(MIGRATIONS,{11:MIGRATIONS[11]+('INVALID SQL',)}),self.assertRaises(sqlite3.Error):migrate(path)
    else:migrate(path);migrate(path)
    with closing(sqlite3.connect(path)) as db, db:
     self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],10 if failed else 11)
     self.assertEqual(db.execute('SELECT quantity,price FROM purchases').fetchone(),('2','100'))
    self.assertEqual(len(list((Path(folder)/'backups'/'migrations').glob('*.sqlite3'))),1)
