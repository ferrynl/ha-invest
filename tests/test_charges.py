import sys,tempfile,unittest,io,csv,sqlite3,json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
from charges import report,entries
from imports.service import preview
from imports.partial import commit_partial
from imports.registry import remember
from restore import restore_backup
from migrations import MIGRATIONS,SCHEMA_VERSION,migrate
from transactions import reset_preview,reset,ledger

HEADER='date,reference,category,amount,currency,ticker,included_in_net,description\n'
def costs(reference='invoice',category='COMMISSION',amount='1.25',currency='EUR',net='0',day='2025-12-18',ticker=''):
 stream=io.StringIO();writer=csv.writer(stream);writer.writerow([day,reference,category,amount,currency,ticker,net,'Synthetic test']);return stream.getvalue()

class ChargeTests(unittest.TestCase):
 def setUp(self):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.store=Store(folder.name);self.store.add_account(dict(name='Broker',broker='Revolut'))
 def book(self,text,provider='charges',account=2):
  batch=preview(self.store,account,provider,'synthetic.csv',text)
  for row in batch['rows']:
   if row.get('kind') in ('BUY','SELL','DIVIDEND') and not row.get('error'):remember(self.store,account,provider,row,dict(symbol=row['ticker'],exchange='NYSE',name='Test',currency=row['currency']))
  return batch,commit_partial(self.store,batch['batch_id'])
 def test_expenses_refunds_vat_and_net_inclusions_are_separate_and_deduplicated(self):
  text=HEADER+costs()+costs(category='VAT',amount='.25')+costs(reference='refund',amount='-.50')+costs(reference='dividend',category='WITHHOLDING_TAX',amount='.30',net='1')
  batch,result=self.book(text);self.assertEqual((result['imported'],result['pending']),(4,0))
  totals=report(self.store,year='2025')['total'];self.assertEqual(Decimal(totals['total']),Decimal('1.30'));self.assertEqual(Decimal(totals['additional']),Decimal('1.00'));self.assertEqual(Decimal(totals['included']),Decimal('.30'))
  self.assertEqual(report(self.store,view='taxes')['total']['count'],2)
  self.assertEqual(len(ledger(self.store)['transactions']),4)
  self.assertEqual(self.book(text)[1]['imported'],0);self.assertEqual(len(entries(self.store)),4)
 def test_source_fees_taxes_and_original_dividend_net_are_preserved(self):
  text='Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Fee,Tax Amt.\n2025-12-01,buy,TEST,,BUY,2,USD,10,-21,1,0\n2025-12-18,income,TEST,,DIVIDEND,,USD,,.80,0,.20\n'
  _,result=self.book(text,'revolut');self.assertEqual(result['pending'],0)
  self.assertEqual(self.store.state()['dividends'][0]['amount'],'0.80')
  rows=entries(self.store);self.assertEqual([(r['category'],r['amount'],r['included_in_net']) for r in rows],[('COMMISSION','1',0),('WITHHOLDING_TAX','0.20',1)])
  self.assertEqual(self.book(text,'revolut')[1]['imported'],0)
 def test_legacy_custody_and_signed_tax_corrections_are_postings(self):
  text='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n2025-12-01,,CUSTODY FEE,,,USD -0.02,USD\n2025-12-18,TEST,DIVIDEND TAX (CORRECTION),,,USD -0.05,USD\n2025-12-18T10:00:00Z,TEST,DIVIDEND TAX (CORRECTION),,,USD 0.05,USD\n'
  _,result=self.book(text,'revolut');self.assertEqual((result['imported'],result['pending']),(3,0));self.assertEqual(sum(Decimal(r['amount']) for r in entries(self.store)),Decimal('.02'))
 def test_duplicate_legacy_trade_can_recover_missing_charges_without_rebooking(self):
  text='Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Fee\n2025-12-01,buy,TEST,,BUY,2,EUR,10,-21,1\n'
  _,result=self.book(text,'revolut');self.assertEqual(result['imported'],1)
  with self.store.connect() as db:db.execute('DELETE FROM charges')
  recovered,result=self.book(text,'revolut');self.assertTrue(recovered['rows'][0]['charges_pending']);self.assertEqual((result['imported'],result['pending']),(1,0));self.assertEqual(len(self.store.state()['purchases']),1);self.assertEqual(len(entries(self.store)),1)
 def test_failed_sale_rolls_back_its_charge_but_retains_valid_cash_expense(self):
  text='Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Fee\n2025-12-01,sale,TEST,,SELL,2,EUR,10,19,1\n2025-12-18,custody,,,CUSTODY FEE,,EUR,,-.20,\n'
  _,result=self.book(text,'revolut');self.assertEqual((result['imported'],result['pending']),(1,1));self.assertEqual(len(entries(self.store)),1);self.assertEqual(entries(self.store)[0]['category'],'CUSTODY');self.assertEqual(self.store.state()['purchases'],[])
 def test_vat_inclusion_is_explicit_and_never_double_counted(self):
  header='Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Fee,VAT,Fee includes VAT\n'
  text=header+'2025-12-01,buy,TEST,,BUY,2,EUR,10,-21.21,1.21,.21,1\n'
  _,result=self.book(text,'revolut');self.assertEqual(result['pending'],0);self.assertEqual(Decimal(report(self.store)['total']['total']),Decimal('1.21'))
  ambiguous=header+'2025-12-01,other,TEST,,BUY,2,EUR,10,-21.21,1.21,.21,\n'
  _,result=self.book(ambiguous,'revolut');self.assertEqual(result['pending'],1);self.assertEqual(len(entries(self.store)),2)
 def test_trading212_source_currency_and_net_withholding(self):
  self.store.add_account(dict(name='Other',broker='Trading 212'))
  header='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total),Transaction fee,Currency (Transaction fee),Withholding tax,Currency (Withholding tax)\n'
  text=header+'Market buy,2025-12-01 10:00:00,,TEST,Test,buy,2,10,EUR,21,EUR,1,EUR,,\nDividend (Ordinary),2025-12-18 10:00:00,,TEST,Test,div,,,,.8,EUR,,,0.2,EUR\n'
  _,result=self.book(text,'trading212',3);self.assertEqual(result['pending'],0)
  self.assertEqual(Decimal(report(self.store,3)['total']['additional']),1)
  self.assertEqual(Decimal(report(self.store,3)['total']['included']),Decimal('.2'))
 def test_fx_is_dated_pence_aware_and_missing_is_visible_without_network(self):
  self.book(HEADER+costs(currency='USD',amount='2')+costs(reference='pence',currency='GBX',amount='100')+costs(reference='missing',currency='CAD',amount='4'))
  from forex import save_rates
  save_rates(self.store,[dict(base='EUR',quote='USD',date='2025-12-18',rate='2'),dict(base='EUR',quote='GBP',date='2025-12-18',rate='.5'),dict(base='EUR',quote='CAD',date='2025-12-19',rate='2')],__import__('datetime').date(2025,12,19))
  with patch('forex.load_json',side_effect=AssertionError('report must not fetch')):result=report(self.store)
  self.assertEqual(Decimal(result['total']['total']),3);self.assertFalse(result['complete']);self.assertEqual(result['missing_fx'][0]['currency'],'CAD');self.assertEqual(result['total']['count'],2)
 def test_changed_reference_rejected_and_unknown_values_stay_pending(self):
  self.book(HEADER+costs())
  _,result=self.book(HEADER+costs(amount='99'));self.assertEqual(result['pending'],1);self.assertEqual(len(entries(self.store)),1)
  for args in (dict(category='UNKNOWN'),dict(amount='NaN'),dict(net='yes'),dict(day='2099-01-01'),dict(currency='?')):
   _,result=self.book(HEADER+costs(reference='bad',**args));self.assertEqual(result['pending'],1)
 def test_restore_and_scoped_reset_preserve_other_accounts_and_negative_refunds(self):
  self.book(HEADER+costs(amount='-.50'));self.book(HEADER+costs(reference='manual',amount='3'),account=1)
  content=self.store.backup().read_bytes();restored=Store(Path(self.store.root)/'restored');restore_backup(restored,content)
  self.assertEqual(len(entries(restored)),2);self.assertEqual(Decimal(report(restored,2)['total']['total']),Decimal('-.50'))
  revision=reset_preview(restored,2);self.assertEqual(revision['counts']['charges'],1)
  reset(restored,dict(account_id='2',revision=revision['revision'],confirmation='VERWIJDEREN'))
  self.assertEqual(len(entries(restored)),1);self.assertEqual(report(restored)['total']['total'],'3')
 def test_restore_rejects_invalid_charge_category_and_preserves_live_data(self):
  self.book(HEADER+costs());path=self.store.backup()
  with closing(sqlite3.connect(path)) as db, db:
   db.execute('PRAGMA ignore_check_constraints=ON');db.execute("UPDATE charges SET category='UNKNOWN'")
  with self.assertRaises(ValueError):restore_backup(self.store,path.read_bytes())
  self.assertEqual(len(entries(self.store)),1)
 def test_schema19_upgrade_preserves_existing_history_and_is_repeatable(self):
  path=Path(self.store.root)/'old.sqlite3'
  with closing(sqlite3.connect(path)) as db, db:
   for version in range(1,20):
    for statement in MIGRATIONS[version]:db.execute(statement)
   db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES('TEST','NYSE','Test','2','10','EUR','2025-01-01','2025-01-01T00:00:00+00:00')");db.execute("INSERT INTO daily_prices VALUES('TEST','NYSE','EUR','2025-01-01','11')")
   db.execute('PRAGMA user_version=19');db.execute("INSERT INTO dividends VALUES(1,'TEST','NYSE','EUR','2','2025-01-01','Synthetic','2025-01-01T00:00:00+00:00',1)")
  old_content=path.read_bytes();older=Store(Path(self.store.root)/'from-old');restore_backup(older,old_content)
  self.assertEqual(older.state()['purchases'][0]['quantity'],'2')
  migrate(path);migrate(path)
  with closing(sqlite3.connect(path)) as db, db:self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'2');self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],20);self.assertEqual(db.execute('SELECT quantity FROM purchases').fetchone()[0],'2');self.assertEqual(db.execute('SELECT price FROM daily_prices').fetchone()[0],'11')
  self.assertTrue(list((path.parent/'backups/migrations').glob('before-v19-to-v20-*.sqlite3')))
 def test_migration20_failure_rolls_back_to19(self):
  path=Path(self.store.root)/'rollback.sqlite3'
  with closing(sqlite3.connect(path)) as db, db:
   for version in range(1,20):
    for statement in MIGRATIONS[version]:db.execute(statement)
   db.execute('PRAGMA user_version=19')
  with patch.dict(MIGRATIONS,{20:MIGRATIONS[20]+('INVALID SQL',)}):
   with self.assertRaises(sqlite3.Error):migrate(path)
  with closing(sqlite3.connect(path)) as db, db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],19);self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='charges'").fetchone())

 def test_explicit_ignore_is_not_undone_when_reimporting_expenses(self):
  from imports.partial import resolve_issue,list_issues
  text='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n2025-12-01,,CUSTODY FEE,,,EUR -0.20,EUR\n'
  batch=preview(self.store,2,'revolut','synthetic.csv',text)
  row=batch['rows'][0];row.update(kind=None,error='legacy')
  with self.store.connect() as db:db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps([row]),batch['batch_id']))
  with patch('imports.partial.refresh_supported'):commit_partial(self.store,batch['batch_id'])
  issue=list_issues(self.store)['issues'][0];resolve_issue(self.store,dict(id=issue['id'],decision='IGNORE'))
  self.assertEqual(self.book(text,'revolut')[1]['imported'],0);self.assertEqual(entries(self.store),[])

 def test_performance_deducts_additional_costs_once_and_includes_them_in_xirr(self):
  from performance import overview
  from datetime import date
  self.store.add(dict(symbol='TEST',exchange='NYSE',name='Test',quantity='2',price='10',currency='EUR',purchased_on='2025-12-01'))
  self.store.quote('TEST','NYSE','EUR','12','2026-10-31T10:00:00+00:00','Test')
  self.store.add_dividend(dict(symbol='TEST',exchange='NYSE',currency='EUR',amount='.80',paid_on='2025-12-18'))
  with self.store.connect() as db:db.execute("INSERT INTO daily_prices VALUES('TEST','NYSE','EUR','2025-12-31','10')")
  before=overview(self.store,self.store.state(),account='1',today=date(2026,10,31))['groups'][0]
  self.book(HEADER+costs(amount='1')+costs(category='VAT',amount='.21')+costs(reference='refund',amount='-.20')+costs(reference='withheld',category='WITHHOLDING_TAX',amount='.20',net='1'),account=1)
  group=overview(self.store,self.store.state(),account='1',today=date(2026,10,31))['groups'][0]
  self.assertEqual(Decimal(group['total']),Decimal('3.79'));self.assertEqual(Decimal(group['additional_costs']),Decimal('.8'));self.assertEqual(Decimal(group['additional_taxes']),Decimal('.21'));self.assertEqual(Decimal(group['included_charges']),Decimal('.2'))
  self.assertLess(Decimal(group['irr']),Decimal(before['irr']))
  self.assertEqual(sum(Decimal(y['gain']) for y in group['years'] if y['gain'] is not None),Decimal('3.79'))
  other=overview(self.store,self.store.state(),account='2',today=date(2026,10,31))['groups'][0];self.assertIsNone(other['costs'])

 def test_explicit_fee_on_cash_movement_is_not_silently_discarded(self):
  text='Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Fee\n2025-12-01,deposit,,,CASH TOP-UP,,EUR,,100,1\n'
  _,result=self.book(text,'revolut');self.assertEqual((result['imported'],result['pending']),(1,0))
  self.assertEqual(entries(self.store)[0]['category'],'OTHER_FEE');self.assertEqual(self.store.state()['purchases'],[])

import test_transactions as transaction_tests
class ChargeHttpTests(unittest.TestCase):
 request=transaction_tests.TransactionHttpTests.request
 def setUp(self):transaction_tests.TransactionHttpTests.setUp(self)
 def tearDown(self):transaction_tests.TransactionHttpTests.tearDown(self)
 def data(self):return dict(account_id=1,date='2025-12-18',reference='invoice',category='COMMISSION',amount='1',currency='EUR',ticker='',included_in_net='0',description='Synthetic')
 def login(self):
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');return token,self.auth.user(token)['csrf']
 def test_signed_in_reports_and_admin_csrf_for_expenses_and_exports(self):
  self.assertEqual(self.request('/api/charges/export')[0],403)
  token,csrf=self.login()
  self.assertEqual(self.request('/api/reports/charges')[0],401)
  self.assertEqual(self.request('/api/charges/save',self.data(),token=token)[0],403)
  self.assertEqual(self.request('/api/charges/save',self.data(),token=token,csrf=csrf)[0],200)
  code,result=self.request('/api/reports/charges?account_id=1&year=2025',token=token);self.assertEqual(code,200);self.assertEqual(result['total']['total'],'1')
  self.assertEqual(self.request('/api/charges/export?year=2025',token=token)[0],200)
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/reports/charges',token=token)[0],200)
  self.assertEqual(self.request('/api/charges/save',self.data(),token=token,csrf=csrf)[0],403)
  self.assertEqual(self.request('/api/charges/export',token=token)[0],403)
  self.assertEqual(self.request('/api/charges/fx',dict(account_id=1),token=token,csrf=csrf)[0],403)
 def test_supplemental_csv_uses_existing_preview_and_partial_commit(self):
  token,csrf=self.login();text=HEADER+costs()
  code,batch=self.request('/api/imports/preview',dict(account_id=1,provider='charges',filename='synthetic.csv',csv=text),token=token,csrf=csrf)
  self.assertEqual(code,200);self.assertEqual(batch['instruments'],[])
  code,result=self.request('/api/imports/commit',dict(batch_id=batch['batch_id']),token=token,csrf=csrf);self.assertEqual(code,200);self.assertEqual(result['imported'],1)
  self.assertEqual(self.request('/api/reports/charges?view=unknown',token=token)[0],400)
  self.assertEqual(self.request('/api/reports/charges?account_id=999',token=token)[0],400)
  self.assertEqual(self.request('/charges.js')[0],200)
