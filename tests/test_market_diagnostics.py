"""Market failures retain useful diagnostics and bound automatic network retries."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from diagnostics import read_logs
from provider import _payload, ProviderBusy, error_details
from storage import Store


class ProviderDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.request = Request('https://query1.finance.yahoo.com/test?token=private-query')

    def test_rate_limit_reason_status_and_wait_survive_restart_without_another_request(self):
        for status in (429, 503):
            with self.subTest(status=status):
                with self.store.connect() as db:
                    db.execute('DELETE FROM api_cache')
                error = HTTPError(self.request.full_url, status, 'private-response',
                                  {'Retry-After': '180', 'Set-Cookie': 'private-cookie'},
                                  io.BytesIO(b'private-body'))
                with patch('provider.urlopen', side_effect=error) as network:
                    for key, store in (('first', self.store), ('second', Store(self.folder.name))):
                        with self.assertRaises(ProviderBusy) as caught:
                            _payload(self.request, 1, store, 'yahoo-quote', key, 900)
                        details = error_details(caught.exception)
                        self.assertEqual(details['http_status'], status)
                        self.assertGreater(details['retry_seconds'], 0)
                        self.assertLessEqual(details['retry_seconds'], 180)
                        self.assertEqual(details['endpoint_host'], 'query1.finance.yahoo.com')
                        self.assertIn('duration_ms', details)
                        self.assertEqual(details['stage'], 'yahoo-quote')
                        self.assertTrue(details['reason'])
                        record_text = json.dumps(details)
                        for secret in ('private-query', 'private-response', 'private-cookie', 'private-body'):
                            self.assertNotIn(secret, record_text)
                    self.assertEqual(network.call_count, 1)

    def test_legacy_cooldown_stays_usable_and_expiry_allows_recovery(self):
        with self.store.connect() as db:
            db.execute("INSERT INTO api_cache VALUES('provider-cooldown','yahoo','{}',0,9999999999)")
        with patch('provider.urlopen') as network:
            with self.assertRaises(ProviderBusy) as caught:
                _payload(self.request, 1, self.store, 'yahoo-quote', 'legacy', 900)
            self.assertEqual(caught.exception.code, 'provider_cooldown')
            network.assert_not_called()
        with self.store.connect() as db:
            db.execute("UPDATE api_cache SET expires_at=0")
        with patch('provider.urlopen', return_value=io.BytesIO(b'{"ok":true}')):
            self.assertEqual(_payload(self.request, 1, self.store, 'yahoo-quote', 'legacy', 900), {'ok': True})

    def test_unknown_and_network_errors_do_not_log_raw_messages(self):
        for error in (ValueError('secret-message'), URLError('secret-message'),
                      HTTPError(self.request.full_url, 403, 'secret-message', {}, None)):
            details = error_details(error)
            self.assertIn('reason', details)
            self.assertNotIn('secret-message', json.dumps(details))
        self.assertEqual(error_details(TimeoutError())['code'], 'provider_connection_failed')

    def test_http_rejection_retains_status_and_fixed_endpoint_metadata(self):
        error = HTTPError(self.request.full_url, 403, 'secret-message', {}, None)
        with patch('provider.urlopen', side_effect=error):
            with self.assertRaises(HTTPError) as caught:
                _payload(self.request, 1, self.store, 'yahoo-quote', 'blocked', 900)
        details = error_details(caught.exception)
        self.assertEqual(details['http_status'], 403)
        self.assertEqual(details['endpoint_host'], 'query1.finance.yahoo.com')
        self.assertNotIn('private-query', json.dumps(details))


class MarketRefreshDiagnosticsTests(unittest.TestCase):
    def test_busy_quote_logs_reason_and_pauses_remaining_yahoo_calls(self):
        import server
        from cache import StateCache
        with patch.object(server, 'market_weekend', return_value=False), tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            for symbol in ('IBM', 'KO'):
                store.add(dict(symbol=symbol, exchange='NYSE', currency='USD', name=symbol,
                               quantity='1', price='100', purchased_on='2026-01-01'))
            error = HTTPError('https://query1.finance.yahoo.com/test', 429, 'secret',
                              {'Retry-After': '180'}, None)
            with patch.object(server, 'store', store), patch.object(server, 'state_cache', StateCache(store=store)), \
                 patch.object(server, 'status', {}), patch.object(server, 'enrich_categories', return_value=False), \
                 patch('fund_holdings.background_refresh', return_value=False), patch('server.time.sleep'), \
                 patch('provider.urlopen', side_effect=error) as network, patch.object(server, 'fetch_history') as history:
                server.refresh()
                self.assertEqual(network.call_count, 1)
                history.assert_not_called()
            entries = [row for row in read_logs(store)['entries'] if row['event'] == 'quote_failed']
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['details']['http_status'], 429)
            self.assertEqual(entries[0]['details']['retry_seconds'], 180)
            self.assertIn('Yahoo', entries[0]['details']['reason'])


class FundDownloadBudgetTests(unittest.TestCase):
    def test_background_failure_retries_daily_after_restart_and_keeps_manual_refresh(self):
        from fund_holdings import background_refresh, refresh, KNOWN
        key = ('EXV1.DE', 'XETRA', 'EUR')
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with patch('fund_holdings.retrieve', side_effect=ValueError('private-response')) as network:
                self.assertFalse(background_refresh(store, key))
                with store.connect() as db:
                    # The manual hourly pause expires, while the daily background budget remains.
                    db.execute("UPDATE api_cache SET expires_at=0 WHERE namespace='fund-refresh'")
                self.assertFalse(background_refresh(Store(folder), key))
                self.assertEqual(network.call_count, 1)
                with self.assertRaises(ValueError):
                    refresh(store, key, url=KNOWN[key])
                self.assertEqual(network.call_count, 2)
                with store.connect() as db:
                    db.execute("UPDATE api_cache SET expires_at=0 WHERE namespace IN ('fund-background','fund-refresh')")
                self.assertFalse(background_refresh(store, key))
                self.assertEqual(network.call_count, 3)
            entries = [row for row in read_logs(store)['entries'] if row['event'] == 'fund_holdings_failed']
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]['details']['background_retry_seconds'], 86400)
            self.assertNotIn('private-response', json.dumps(entries))

    def test_failed_background_download_preserves_saved_holdings(self):
        from fund_holdings import background_refresh, save, saved, KNOWN
        key = ('EXV1.DE', 'XETRA', 'EUR')
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            save(store, key, dict(as_of='2026-01-01', holdings=[dict(name='Example', weight='100')]), KNOWN[key])
            with store.connect() as db:
                db.execute("UPDATE fund_compositions SET fetched_at='2026-01-01T00:00:00+00:00'")
            with patch('fund_holdings.retrieve', side_effect=ValueError('offline')) as network:
                background_refresh(store, key)
                background_refresh(store, key)
                self.assertEqual(network.call_count, 1)
            self.assertEqual(saved(store, key)['holdings'][0]['name'], 'Example')
