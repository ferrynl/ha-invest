import csv
import io
import sys
import tempfile
import unittest
import json
from unittest.mock import patch
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
        self.assertTrue(parse_csv(export(dict(date='2026-01-05')))[0]['error'])

    def test_cash_rows_and_wrong_format(self):
        self.assertEqual(parse_csv(export(dict(category='CASH',type='INTEREST_PAYMENT')))[0]['kind'],'SKIP')
        with self.assertRaises(ValueError):parse_csv('Date,Amount\n2026-01-02,1')
        with self.assertRaises(ValueError):preview(self.store,1,'traderepublic','x.csv',export({}))

    def test_private_fund_prepayment_and_execution_book_only_once(self):
        from imports.matching import resolve_instrument
        from valuations import save
        from profiles import enrich_categories,fetch_company
        from decimal import Decimal
        cash=dict(category='CASH',type='PRIVATE_MARKET_BUY',asset_class='PRIVATE_FUND',symbol='LU3170240538',shares='',price='',amount='-1',transaction_id='cash')
        trade=dict(asset_class='PRIVATE_FUND',symbol='LU3170240538',shares='0.01',price='100',amount='',transaction_id='fund')
        batch=preview(self.store,2,'traderepublic','fund.csv',export(cash,trade))
        self.assertEqual([r['kind'] for r in batch['rows']],['SKIP','BUY'])
        with patch('imports.matching.listing') as listing,patch('imports.matching.search_stocks') as search:
            mapping=resolve_instrument(self.store,batch['batch_id'],'LU3170240538|EUR')['mapping']
            self.assertEqual(mapping['exchange'],'PRIVATE');listing.assert_not_called();search.assert_not_called()
        result=commit_partial(self.store,batch['batch_id']);self.assertEqual(result['imported'],1);self.assertEqual(result['pending'],0)
        position=self.store.state()['positions'][0];self.assertEqual(Decimal(position['quantity']),Decimal('.01'));self.assertEqual(Decimal(position['cost']),1);self.assertIsNone(position['value'])
        with patch('profiles._download_profile') as download:
            enrich_categories(self.store,('LU3170240538','PRIVATE','EUR'))
            self.assertIn('Niet-beursgenoteerd',fetch_company(self.store,('LU3170240538','PRIVATE','EUR'))['description']);download.assert_not_called()
        target=dict(symbol='LU3170240538',exchange='PRIVATE',currency='EUR')
        with self.assertRaises(ValueError):save(self.store,dict(**target,automatic=True))
        save(self.store,dict(**target,automatic=False,price='110',day='2026-01-03'))
        self.assertEqual(Decimal(self.store.state()['positions'][0]['value']),Decimal('1.10'))
        from restore import restore_backup
        backup=self.store.backup().read_bytes();restore_backup(self.store,backup)
        self.assertEqual(Decimal(Store(self.store.root).state()['positions'][0]['value']),Decimal('1.10'))
        again=preview(self.store,2,'traderepublic','overlap.csv',export(cash,trade));self.assertEqual(commit_partial(self.store,again['batch_id'])['imported'],0)

    def test_old_rejected_rows_recover_without_new_upload_and_keep_identity(self):
        from imports.matching import resolve_instrument
        cash=dict(category='CASH',type='PRIVATE_MARKET_BUY',asset_class='PRIVATE_FUND',symbol='LU3170240538',shares='',price='',amount='-1',transaction_id='cash')
        trade=dict(asset_class='PRIVATE_FUND',symbol='LU3170240538',transaction_id='fund')
        date_row=dict(date='2026-01-03',datetime='2026-01-02T23:30:00Z',transaction_id='local-date')
        batch=preview(self.store,2,'traderepublic','old.csv',export(cash,trade,date_row))
        old=batch['rows']
        for row in old:
            row['error']='Oude parserfout'
            if row['line']==2:row['kind']=None
        identities=[(r['external_id'],r['digest']) for r in old]
        with self.store.connect() as db:
            db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(old),batch['batch_id']))
            for row in old:db.execute("INSERT INTO import_issues(batch_id,line,state,reason,payload,updated_at) VALUES(?,?,'pending',?,?,datetime('now'))",(batch['batch_id'],row['line'],row['error'],json.dumps(row)))
        opened=open_preview(self.store,batch['batch_id']);self.assertFalse(any(r['error'] for r in opened['rows']))
        self.assertEqual(identities,[(r['external_id'],r['digest']) for r in opened['rows']]);self.assertEqual(opened['rows'][2]['day'],'2026-01-03')
        resolve_instrument(self.store,batch['batch_id'],'LU3170240538|EUR')
        from imports.registry import remember
        remember(self.store,2,'traderepublic',opened['rows'][2],dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML'))
        result=commit_partial(self.store,batch['batch_id']);self.assertEqual(result['imported'],2);self.assertEqual(result['pending'],0)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT state FROM import_issues WHERE line=2').fetchone()[0],'ignored')

    def test_private_cash_shape_changes_still_require_review(self):
        row=parse_csv(export(dict(category='CASH',type='PRIVATE_MARKET_BUY',asset_class='PRIVATE_FUND')))[0]
        self.assertIsNone(row['kind']);self.assertTrue(row['error'])

    def test_unknown_private_fund_never_searches_for_a_public_substitute(self):
        from imports.matching import resolve_instrument
        batch=preview(self.store,2,'traderepublic','unknown.csv',export(dict(asset_class='PRIVATE_FUND')))
        with patch('imports.matching.listing') as listing,patch('imports.matching.search_stocks') as search:
            result=resolve_instrument(self.store,batch['batch_id'],'NL0010273215|EUR')
            self.assertIn('Niet-beursgenoteerd',result['error']);listing.assert_not_called();search.assert_not_called()

    def test_reported_isins_prefer_verified_euro_listings(self):
        from imports.matching import resolve_instrument
        for isin,symbol,exchange in [('CA25537R1091','641.F','FRANKFURT'),('CNE100000296','BY6.F','FRANKFURT'),('DE0007030009','RHM.DE','XETRA'),('KYG9830T1067','3CP.F','FRANKFURT'),('US02079K3059','ABEA.DE','XETRA')]:
            batch=preview(self.store,2,'traderepublic','equity.csv',export(dict(symbol=isin)))
            stock=dict(symbol=symbol,exchange=exchange,currency='EUR',name='Example')
            with patch('imports.matching.listing',return_value=stock) as listing,patch('imports.matching.search_stocks') as search:
                result=resolve_instrument(self.store,batch['batch_id'],isin+'|EUR')
                self.assertEqual(result['mapping'],stock);self.assertEqual(listing.call_args.args[0],symbol);search.assert_not_called()

    def test_backup_still_rejects_unknown_mapping_providers(self):
        import sqlite3
        from restore import restore_backup
        self.mapped(export({}));backup=self.store.backup()
        from contextlib import closing
        with closing(sqlite3.connect(backup)) as db:
            db.execute("UPDATE instrument_mappings SET provider='unknown-provider'");db.commit()
        with self.assertRaisesRegex(ValueError,'instrumentkoppeling'):restore_backup(self.store,backup.read_bytes())
