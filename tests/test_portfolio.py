import sys
import tempfile
import unittest
import sqlite3
import json
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from storage import Store
from provider import fetch_quote, search_stocks, _search_stocks

class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.buy = dict(name='ASML', symbol='ASML.AS', exchange='AMSTERDAM', quantity='2.5', price='600.10', currency='EUR', purchased_on='2025-01-01')

    def test_decimal_multiple_lots_and_persistence(self):
        self.store.add(self.buy)
        self.store.add({**self.buy, 'quantity': '1', 'price': '700'})
        self.store.quote('ASML.AS', 'AMSTERDAM', 'EUR', '800', '2026-10-16T15:30:00+00:00', 'test')
        p = Store(self.tmp.name).state()['positions'][0]
        self.assertEqual(p['quantity'], '3.5')
        self.assertEqual(p['cost'], '2200.250')
        self.assertEqual(p['value'], '2800.0')
        self.assertEqual(p['gain'], '599.750')

    def test_missing_quote_is_not_zero(self):
        self.store.add(self.buy)
        self.assertIsNone(self.store.state()['positions'][0]['value'])

    def test_reject_bad_inputs_atomically(self):
        for field, value in [('quantity', 'NaN'), ('price', '-1'), ('quantity', 'Infinity'), ('currency', 'EU'), ('purchased_on', '2099-01-01'), ('exchange', '')]:
            with self.assertRaises(ValueError):
                self.store.add({**self.buy, field: value})
        self.assertEqual(self.store.state()['purchases'], [])

    def test_quotes_do_not_cross_currency_or_exchange(self):
        self.store.add(self.buy)
        self.store.quote('ASML.AS', 'NASDAQ', 'USD', '800', '2026-10-16T15:30:00+00:00', 'test')
        self.assertIsNone(self.store.state()['positions'][0]['value'])

    def test_backup_can_be_restored(self):
        self.store.add(self.buy)
        path = self.store.backup()
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0], 1)
        for _ in range(32):
            self.store.backup()
        self.assertEqual(len(list(path.parent.glob('*.sqlite3'))), 30)

    @patch('provider.urlopen')
    def test_yahoo_response_and_currency_guard(self, request):
        response = request.return_value.__enter__.return_value
        payload = dict(symbol='ASML.AS', exchangeName='AMS', currency='EUR', regularMarketPrice=800, regularMarketTime=1792164600)
        response.read.return_value = json.dumps({'chart': {'result': [{'meta': payload}]}}).encode()
        price, stamp = fetch_quote('', 'ASML.AS', 'AMSTERDAM', 'EUR')
        self.assertEqual(price, 800)
        self.assertIn('+00:00', stamp)
        with self.assertRaises(ValueError):
            fetch_quote('', 'ASML.AS', 'AMSTERDAM', 'USD')

    @patch('provider.urlopen')
    def test_search_filters_exchanges_and_deduplicates(self, request):
        _search_stocks.cache_clear()
        request.return_value.__enter__.return_value.read.return_value = json.dumps({'quotes': [
            {'symbol': 'ASML.AS', 'longname': 'ASML Holding', 'exchange': 'AMS', 'quoteType': 'EQUITY'},
            {'symbol': 'ASML.AS', 'exchange': 'AMS', 'quoteType': 'EQUITY'},
            {'symbol': 'ASML', 'shortname': 'ASML ADR', 'exchange': 'NMS', 'quoteType': 'EQUITY'},
            {'symbol': 'IBM', 'shortname': 'IBM', 'exchange': 'NYQ', 'quoteType': 'EQUITY'},
            {'symbol': 'ASX.L', 'exchange': 'LSE', 'quoteType': 'EQUITY'},
            {'symbol': '^AEX', 'exchange': 'AMS', 'quoteType': 'INDEX'},
        ]}).encode()
        results = search_stocks('AS')
        self.assertEqual([item['symbol'] for item in results], ['ASML.AS', 'ASML', 'IBM'])
        self.assertEqual(results[0]['currency'], 'EUR')
        self.assertEqual(results[1]['currency'], 'USD')
        self.assertEqual(results[2]['exchange'], 'NYSE')
        self.assertEqual(search_stocks(' as '), results)
        request.assert_called_once()
        _search_stocks.cache_clear()

    def test_search_requires_two_characters(self):
        for query in ['', 'a', '  a  ', 'x' * 81]:
            with self.assertRaises(ValueError):
                search_stocks(query)

if __name__ == '__main__':
    unittest.main()
