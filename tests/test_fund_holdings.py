import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from storage import Store
from fund_holdings import parse_csv, validate, save, saved, refresh, source_url, KNOWN
from instruments import save_categories, details
from restore import restore_backup

KEY = ('EXV1.DE', 'XETRA', 'EUR')
IDENTITY = dict(zip(('symbol', 'exchange', 'currency'), KEY))
CSV = '''Fund Holdings as of,"29/Oct/2026"
Ticker,Name,Sector,Asset Class,Weight (%),Location
AAA,First bank,Financials,Equity,60,Netherlands
BBB,Second bank,Financials,Equity,39,Spain
EUR,EUR CASH,Cash and/or Derivatives,Cash,1.01,European Union
GBP,GBP CASH,Cash and/or Derivatives,Cash,-0.01,United Kingdom
'''


class FundHoldingsTests(unittest.TestCase):
    def test_german_ishares_csv_uses_date_decimal_comma_and_canonical_countries(self):
        content='Fondsposition per,"29.Okt.2026"\n\nEmittententicker,Name,Sektor,Anlageklasse,Gewichtung (%),Standort,Marktwährung\nAAPL,APPLE,IT,Aktien,"99,99",Vereinigte Staaten,USD\nEUR,EURO,Cash und/oder Derivate,Geldmarkt,"0,01",Deutschland,EUR\n'
        result=parse_csv(content)
        self.assertEqual(result['as_of'],'2026-10-29');self.assertEqual(result['coverage'],'100.00')
        self.assertEqual(result['holdings'][0]['weight'],'99.99');self.assertEqual(result['holdings'][0]['country'],'US');self.assertEqual(result['holdings'][0]['sector'],'Technology');self.assertEqual(result['holdings'][0]['asset_type'],'Equity')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.store.add(dict(**IDENTITY, name='Example ETF', quantity='2', price='50', purchased_on='2026-10-01'))
        save_categories(self.store, dict(**IDENTITY, asset_type='ETF'))

    def test_full_issuer_file_keeps_cash_and_signed_weights(self):
        payload = parse_csv(CSV)
        self.assertEqual(len(payload['holdings']), 4)
        self.assertEqual(payload['coverage'], '100.00')
        self.assertTrue(payload['signed'])
        self.assertEqual(payload['holdings'][-1]['weight'], '-0.01')
        self.assertEqual(payload['as_of'], '2026-10-29')

    def test_generic_csv_supports_any_fund_and_preserves_partial_coverage(self):
        payload = parse_csv('Naam;Weging (%);Sector;Land;Categorie\nApple;12,5;Technology;US;Growth', '2026-10-20')
        self.assertEqual(payload['coverage'], '12.5')
        self.assertEqual(payload['holdings'][0]['category'], 'Growth')
        with self.assertRaises(ValueError):
            parse_csv('Naam,Weging (%)\nOne,100\nBroken,nope', '2026-10-20')

    def test_invalid_values_and_missing_date_are_rejected(self):
        for weight in ('NaN', 'Infinity', '10000', 'invalid', ''):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                parse_csv('Name,Weight (%)\nExample,' + weight, '2026-10-20')
        with self.assertRaises(ValueError):
            parse_csv('Name,Weight (%)\nExample,100')
        with self.assertRaises(ValueError):
            validate(dict(as_of='2999-01-01', holdings=[dict(name='One', weight=100)]))

    def test_source_allowlist_blocks_internal_urls_and_credentials(self):
        for url in ('http://www.ishares.com/test', 'https://localhost/test', 'https://127.0.0.1/a',
                    'https://www.ishares.com.evil.test/a', 'https://user:password@www.ishares.com/a',
                    'https://www.ishares.com:8443/a', 'file:///tmp/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                source_url(url)
        self.assertEqual(source_url(KNOWN[KEY]), KNOWN[KEY])

    def test_saved_snapshot_survives_restart_and_invalidates_revision(self):
        before = self.store.state()['data_revision']
        save(self.store, KEY, parse_csv(CSV), KNOWN[KEY])
        snapshot = Store(self.tmp.name).state()
        self.assertGreater(snapshot['data_revision'], before)
        self.assertEqual(snapshot['fund_compositions'][0]['holdings'][0]['name'], 'First bank')
        self.assertTrue(details(self.store, IDENTITY)['is_etf'])
        self.assertEqual(details(self.store, IDENTITY)['fund_composition']['coverage'], '100.00')
        self.assertEqual(snapshot['positions'][0]['quantity'], '2')

    def test_refresh_failure_retains_saved_data_and_honors_cooldown(self):
        save(self.store, KEY, parse_csv(CSV), KNOWN[KEY])
        with patch('fund_holdings.retrieve', side_effect=ValueError('offline')) as fetch:
            with self.assertRaises(ValueError):
                refresh(self.store, KEY)
            old = refresh(self.store, KEY)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(len(old['holdings']), 4)
        with self.assertRaises(ValueError):
            save(self.store, KEY, dict(as_of='2026-10-01', holdings=[dict(name='Old', weight='100')]))

    def test_backup_roundtrip_and_invalid_payload_rollback(self):
        save(self.store, KEY, parse_csv(CSV), KNOWN[KEY])
        backup = self.store.backup()
        restore_backup(self.store, backup.read_bytes())
        self.assertEqual(saved(self.store, KEY)['holdings'][0]['name'], 'First bank')
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(backup)) as db:
            db.execute("UPDATE fund_compositions SET payload=?", (json.dumps(dict(as_of='2026-10-29', holdings=[dict(name='Bad', weight='NaN')])),))
            db.commit()
        with self.assertRaises(ValueError):
            restore_backup(self.store, backup.read_bytes())
        self.assertEqual(saved(self.store, KEY)['holdings'][0]['name'], 'First bank')


import test_transactions as support


class FundHoldingsHttpTests(unittest.TestCase):
    setUp = support.TransactionHttpTests.setUp
    tearDown = support.TransactionHttpTests.tearDown
    request = support.TransactionHttpTests.request

    def test_owned_listing_import_read_and_foreign_listing_rejection(self):
        identity = dict(symbol='ASML.AS', exchange='AMSTERDAM', currency='EUR')
        code, result = self.request('/api/instrument/holdings', dict(**identity, csv=CSV))
        self.assertEqual(code, 200)
        self.assertEqual(result['composition']['coverage'], '100.00')
        self.assertEqual(self.request('/api/instrument/holdings?symbol=ASML.AS&exchange=AMSTERDAM&currency=EUR')[0], 200)
        self.assertEqual(self.request('/api/instrument/holdings', dict(**IDENTITY, csv=CSV))[0], 400)

    def test_reader_cannot_change_composition(self):
        self.auth.enable('owner', 'Long-test-password-2026')
        self.assertEqual(self.request('/api/instrument/holdings', dict(**IDENTITY, csv=CSV))[0], 401)
        token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
        self.assertEqual(self.request('/api/instrument/holdings',dict(csv=CSV),token)[0],403)
        with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
        token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
        self.assertEqual(self.request('/api/instrument/holdings',dict(csv=CSV),token,csrf)[0],403)
