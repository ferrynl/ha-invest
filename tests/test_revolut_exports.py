import sys,unittest,io,csv
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from imports.revolut import parse_csv
from exports import export

class RevolutTests(unittest.TestCase):
 def test_formats_and_unknown_actions(self):
  header='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n'
  rows=parse_csv(header+'2026-01-01T10:00:00Z,AAPL,BUY,2,USD 10,USD 20,USD\n2026-01-02,AAPL,SPLIT,2,,,USD\n')
  self.assertEqual(rows[0]['price'],'10');self.assertIsNone(rows[0]['error']);self.assertTrue(rows[1]['error'])
  modern='Date,Reference,Symbol,ISIN,Type,Quantity,CCY,Price/share,Net Amt.\n2026-01-01,abc,AAPL,US0378331005,DIVIDEND,,USD,,2\n'
  row=parse_csv(modern)[0];self.assertEqual(row['amount'],'2');self.assertEqual(row['external_id'],'id:abc')
 def test_review_reason_identifies_action_and_invalid_source_values(self):
  header='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n'
  rows=parse_csv(header+'2026-01-01,MCD,STOCK SPLIT,2,0,0,USD\n2026-01-01,MCD,BUY,2,0,0,USD\n2026-01-01,,BUY,2,10,20,USD\n')
  self.assertIn('Splitsing:',rows[0]['error'])
  self.assertEqual(rows[1]['error'],'Aantal of bedrag ontbreekt of is ongeldig.')
  self.assertEqual(rows[2]['error'],'Geldige ticker ontbreekt.')
 def test_bad_rows_and_stable_identity(self):
  text='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n2026-01-01,AAPL,BUY,2,NaN,20,USD\n'
  row=parse_csv(text)[0];self.assertTrue(row['error']);self.assertEqual(row['external_id'],parse_csv(text)[0]['external_id'])
 def test_export_safe_csv_and_pdf(self):
  rows=[dict(day='2026-01-01',account_name='=HYPERLINK("x")',symbol='AAPL',currency='USD',quantity='2',price='10')]
  with patch('exports.ledger',return_value={'transactions':rows}):
   content,kind=export(None,'all','csv');self.assertIn("'=HYPERLINK",content.decode('utf-8-sig'))
   content,kind=export(None,'all','pdf');self.assertTrue(content.startswith(b'%PDF'))

from test_transactions import TransactionHttpTests
class ExportHttpTests(TransactionHttpTests):
 def test_exports_require_signed_in_admin_and_validate_scope(self):
  self.assertEqual(self.request('/api/export?format=csv')[0],403)
  self.auth.enable('owner','Long-test-password-2026')
  self.assertEqual(self.request('/api/export?format=csv')[0],401)
  token=self.auth.login('owner','Long-test-password-2026','test')
  self.assertEqual(self.request('/api/export?format=csv',token=token)[0],200)
  code,body=self.request('/api/export?format=pdf',token=token);self.assertEqual(code,200);self.assertTrue(body.startswith(b'%PDF'))
  self.assertEqual(self.request('/api/export?format=csv&account_id=999',token=token)[0],400)
  self.assertEqual(self.request('/api/export?format=exe',token=token)[0],400)
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request('/api/export?format=csv',token=token)[0],403)

class RevolutIntegrationTests(unittest.TestCase):
 def test_preview_partial_deduplication_and_account_scope(self):
  import tempfile
  from storage import Store
  from imports.service import preview
  from imports.partial import commit_partial
  from imports.registry import remember
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);store.add_account(dict(name='Revolut',broker='Revolut'))
   text='Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n2026-01-01,AAPL,BUY,2,10,20,EUR\n2026-01-02,AAPL,UNKNOWN,1,12,12,EUR\n'
   batch=preview(store,2,'revolut','test.csv',text)
   remember(store,2,'revolut',batch['rows'][0],dict(symbol='AAPL',exchange='NASDAQ',currency='EUR',name='Apple'))
   result=commit_partial(store,batch['batch_id']);self.assertEqual((result['imported'],result['pending']),(1,1))
   self.assertEqual(len(store.state()['purchases']),1)
   again=preview(store,2,'revolut','again.csv',text);self.assertTrue(again['rows'][0]['duplicate'])
   store.add_account(dict(name='Second',broker='Revolut'))
   other=preview(store,3,'revolut','other.csv',text);self.assertFalse(other['rows'][0]['duplicate'])
