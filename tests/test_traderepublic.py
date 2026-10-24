import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from imports.traderepublic import parse_csv
from imports.service import preview,open_preview
from imports.partial import commit_partial,resolve_issue
from storage import Store

FIELDS='date datetime category type name symbol shares price amount currency transaction_id asset_class'.split()

def export(*entries):
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader()
    for changes in entries:
        writer.writerow(dict(date='2026-01-02',datetime='2026-01-02T10:00:00Z',category='TRADING',type='BUY',name='ASML',symbol='NL0010273215',shares='2',price='100',amount='-201',currency='EUR',transaction_id='buy-1',asset_class='stock')|changes)
    return stream.getvalue()

class TradeRepublicTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(tmp.name)
        self.store.add_account(dict(name='TR',broker='Trade Republic'))

    def mapped(self,text):
        result=preview(self.store,2,'traderepublic','transactions.csv',text)
        from imports.registry import remember
        for row in result['rows']:
            if row.get('currency') and row['ticker']:
                remember(self.store,2,'traderepublic',row,dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML'))
        return result

    def test_roundtrip_overlap_and_account_isolation(self):
        text=export({},dict(type='SELL',shares='-1',price='150',amount='149',transaction_id='sell-1'),dict(category='CASH',type='DIVIDEND',amount='2',transaction_id='div-1'))
        batch=self.mapped(text)
        self.assertEqual(commit_partial(self.store,batch['batch_id'])['imported'],3)
        state=self.store.state();self.assertEqual(state['positions'][0]['quantity'],'1')
        self.assertEqual(state['positions'][0]['cost'],'100');self.assertEqual(state['dividends'][0]['amount'],'2')
        self.assertIn('Trade Republic',state['dividends'][0]['note'])
        again=self.mapped(text);self.assertTrue(all(r['duplicate'] for r in again['rows']))
        self.assertEqual(commit_partial(self.store,again['batch_id'])['imported'],0)
        self.store.add_account(dict(name='Other TR',broker='Trade Republic'))
        other=preview(self.store,3,'traderepublic','same.csv',text);self.assertFalse(any(r.get('duplicate') for r in other['rows']))

    def test_unknown_and_invalid_remain_durable_and_can_be_reviewed(self):
        batch=self.mapped(export({},dict(type='CORPORATE_ACTION',transaction_id='unknown'),dict(category='CASH',type='DIVIDEND',amount='-1',transaction_id='negative'),dict(price='',transaction_id='missing')))
        self.assertEqual(len(open_preview(self.store,batch['batch_id'])['rows']),4)
        result=commit_partial(self.store,batch['batch_id']);self.assertEqual(result['imported'],1);self.assertEqual(result['pending'],3)
        with self.store.connect() as db:issue=db.execute('SELECT id FROM import_issues WHERE batch_id=? AND line=3',(batch['batch_id'],)).fetchone()
        result=resolve_issue(self.store,dict(id=issue['id'],decision='BUY'));self.assertEqual(result['imported'],1)

    def test_source_conflicts_and_missing_id_do_not_book(self):
        batch=self.mapped(export({},dict(price='101')))
        self.assertEqual(commit_partial(self.store,batch['batch_id'])['imported'],0)
        self.assertTrue(parse_csv(export(dict(transaction_id='')))[0]['error'])
        self.assertTrue(parse_csv(export(dict(price='NaN')))[0]['error'])
        self.assertTrue(parse_csv(export(dict(asset_class='crypto')))[0]['error'])
        self.assertTrue(parse_csv(export(dict(date='2026-01-03')))[0]['error'])

    def test_cash_rows_and_wrong_format(self):
        self.assertEqual(parse_csv(export(dict(category='CASH',type='INTEREST_PAYMENT')))[0]['kind'],'SKIP')
        with self.assertRaises(ValueError):parse_csv('Date,Amount\n2026-01-02,1')
        with self.assertRaises(ValueError):preview(self.store,1,'traderepublic','x.csv',export({}))
