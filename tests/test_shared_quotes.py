"""One public quote per listing and one log entry per ongoing provider incident."""
import io
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from diagnostics import read_logs
from provider import fetch_quote, _payload, ProviderBusy, record_failure
from storage import Store


def quote_response(symbol, exchange, currency, price=100):
    return json.dumps({'chart': {'result': [{'meta': dict(
        symbol=symbol, exchangeName=exchange, currency=currency,
        regularMarketPrice=price, regularMarketTime=1795176000,
    )}], 'error': None}}).encode()


class SharedQuoteTests(unittest.TestCase):
    def test_aliases_and_demo_reuse_one_listing_cache(self):
        from demo import refresh_demo_quotes
        with tempfile.TemporaryDirectory() as folder:
            primary = Store(Path(folder) / 'personal')
            demo = Store(Path(folder) / 'demo')
            demo.quote('ASML.AS', 'AMSTERDAM', 'EUR', '90', '2026-01-01T12:00:00+00:00', 'DEMO')
            with patch('provider.urlopen', return_value=io.BytesIO(quote_response('ASML.AS', 'AMS', 'EUR'))) as network, \
                 patch('demo.market_weekend', return_value=False), patch('demo.time.sleep'):
                first = fetch_quote('', 'ASML', 'AMSTERDAM', 'EUR', store=primary)
                second = fetch_quote('', 'ASML.AS', 'AMSTERDAM', 'EUR', store=Store(primary.root))
                refresh_demo_quotes(demo, provider_store=primary)
                self.assertEqual(first, second)
                network.assert_called_once()
            with demo.connect() as db:
                self.assertEqual(db.execute('SELECT price FROM quotes ORDER BY id DESC LIMIT 1').fetchone()[0], '100')

    def test_pence_and_pounds_share_source_data_and_keep_their_own_units(self):
        from decimal import Decimal
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with patch('provider.urlopen', return_value=io.BytesIO(quote_response('EQGB.L', 'LSE', 'GBp', 12345))) as network:
                pence, _ = fetch_quote('', 'EQGB', 'LONDON', 'GBX', store=store)
                pounds, _ = fetch_quote('', 'EQGB.L', 'LONDON', 'GBP', store=store)
                network.assert_called_once()
            self.assertEqual(Decimal(str(pence)), Decimal('12345'))
            self.assertEqual(Decimal(str(pounds)), Decimal('123.45'))


class IncidentLoggingTests(unittest.TestCase):
    def test_same_outage_logs_once_across_listings_stages_and_restart_until_recovery(self):
        request = Request('https://query1.finance.yahoo.com/test')
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            error = HTTPError(request.full_url, 429, 'limited', {}, None)
            references = []
            with patch('provider.urlopen', side_effect=error) as network:
                for symbol, stage in (('IBM', 'yahoo-quote'), ('KO', 'yahoo-history')):
                    with self.assertRaises(ProviderBusy) as caught:
                        _payload(request, 1, Store(folder), stage, symbol, 900)
                    references.append(record_failure(Store(folder), 'quote_failed', 'Actuele koers ophalen mislukt.',
                                                     (symbol, 'NYSE', 'USD'), caught.exception))
                network.assert_called_once()
            self.assertEqual(references[0], references[1])
            self.assertEqual(len(read_logs(store)['entries']), 1)
            with store.connect() as db:
                db.execute("UPDATE api_cache SET expires_at=0 WHERE namespace='provider-cooldown'")
            with patch('provider.urlopen', return_value=io.BytesIO(b'{"quotes":[]}')):
                _payload(request, 1, store, 'yahoo-search-v4', 'recovery', 900)
            with patch('provider.urlopen', side_effect=HTTPError(request.full_url, 429, 'limited', {}, None)):
                with self.assertRaises(ProviderBusy) as caught:
                    _payload(request, 1, store, 'yahoo-quote', 'next', 900)
                next_reference = record_failure(store, 'quote_failed', 'Actuele koers ophalen mislukt.',
                                                ('IBM', 'NYSE', 'USD'), caught.exception)
            self.assertNotEqual(references[0], next_reference)
            self.assertEqual(len(read_logs(store)['entries']), 2)

    def test_concurrent_reports_of_one_incident_create_one_log(self):
        with tempfile.TemporaryDirectory() as folder:
            stores = [Store(folder) for _ in range(8)]
            def report(store):
                error = ProviderBusy('Even wachten', 900, 429)
                error.provider_details = {'endpoint_host': 'query1.finance.yahoo.com', 'stage': 'yahoo-quote'}
                return record_failure(store, 'quote_failed', 'Actuele koers ophalen mislukt.',
                                      ('IBM', 'NYSE', 'USD'), error)
            with ThreadPoolExecutor(max_workers=4) as pool:
                references = list(pool.map(report, stores))
            self.assertEqual(len(set(references)), 1)
            self.assertEqual(len(read_logs(stores[0])['entries']), 1)
