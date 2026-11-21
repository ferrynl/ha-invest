"""Automatic polling obeys the owner's Dutch time window and durable budget."""
import io
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from market_schedule import automatic_window, claim_refresh
from provider import _payload, ProviderBusy
from storage import Store


class AutomaticWindowTests(unittest.TestCase):
    def test_dutch_window_and_summer_time_boundaries(self):
        for stamp, expected in (
            ('2026-11-23T06:59:59+00:00', False),
            ('2026-11-23T07:00:00+00:00', True),
            ('2026-11-23T20:59:59+00:00', True),
            ('2026-11-23T21:00:00+00:00', False),
            ('2026-07-20T05:59:59+00:00', False),
            ('2026-07-20T06:00:00+00:00', True),
            ('2026-07-20T20:00:00+00:00', False),
            ('2026-11-21T11:00:00+00:00', False),
            ('2026-11-22T11:00:00+00:00', False),
        ):
            with self.subTest(stamp=stamp):
                self.assertEqual(automatic_window(datetime.fromisoformat(stamp)), expected)

    def test_budget_survives_restart_and_lower_legacy_intervals(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with patch('market_schedule.automatic_window', return_value=True), \
                 patch('time.time', return_value=1000):
                self.assertTrue(claim_refresh(store, 300))
                self.assertFalse(claim_refresh(Store(folder), 300))
            with patch('market_schedule.automatic_window', return_value=True), \
                 patch('time.time', return_value=1899):
                self.assertFalse(claim_refresh(Store(folder), 300))
            with patch('market_schedule.automatic_window', return_value=True), \
                 patch('time.time', return_value=1900):
                self.assertTrue(claim_refresh(Store(folder), 300))

    def test_closed_window_does_not_claim_the_next_round(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with patch('market_schedule.automatic_window', return_value=False):
                self.assertFalse(claim_refresh(store, 900))
            with store.connect() as db:
                self.assertIsNone(db.execute("SELECT 1 FROM api_cache WHERE namespace='automatic-market'").fetchone())
            with patch('market_schedule.automatic_window', return_value=True):
                self.assertTrue(claim_refresh(store, 1800))
                self.assertFalse(claim_refresh(store, 1800))


class AutomaticBackgroundTests(unittest.TestCase):
    def test_closed_window_blocks_all_automatic_market_and_fx_tasks(self):
        import server
        class StopLoop(BaseException):
            pass
        with patch.object(server, 'automatic_window', return_value=False), \
             patch.object(server.store, 'backup'), \
             patch.object(server, 'refresh') as refresh, \
             patch.object(server, 'warm_dashboard') as warm, \
             patch.object(server, 'fx_currencies') as currencies, \
             patch.object(server, 'fx_snapshot') as fx, \
             patch.object(server.refresh_requested, 'wait', side_effect=StopLoop):
            with self.assertRaises(StopLoop):
                server.background()
            refresh.assert_not_called()
            warm.assert_not_called()
            currencies.assert_not_called()
            fx.assert_not_called()

    def test_rejected_automatic_claim_does_not_start_provider_work(self):
        import server
        with patch.object(server, 'claim_refresh', return_value=False), \
             patch.object(server, 'fetch_quote') as quote, \
             patch.object(server, 'fetch_history') as history, \
             patch.object(server, 'enrich_categories') as profile:
            self.assertFalse(server.refresh(automatic=True))
            quote.assert_not_called()
            history.assert_not_called()
            profile.assert_not_called()
        self.assertFalse(server.refresh_lock.locked())

    def test_round_stops_when_window_closes_before_next_instrument(self):
        import server
        from cache import StateCache
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.add(dict(symbol='IBM', exchange='NYSE', currency='USD', name='IBM',
                           quantity='1', price='100', purchased_on='2026-01-01'))
            with patch.object(server, 'store', store), \
                 patch.object(server, 'state_cache', StateCache(store=store)), \
                 patch.object(server, 'status', {}), \
                 patch.object(server, 'claim_refresh', return_value=True), \
                 patch.object(server, 'automatic_window', return_value=False), \
                 patch.object(server, 'fetch_quote') as quote, \
                 patch.object(server, 'fetch_history') as history, \
                 patch.object(server, 'enrich_categories') as profile:
                self.assertTrue(server.refresh(automatic=True))
                quote.assert_not_called()
                history.assert_not_called()
                profile.assert_not_called()


class ProgressiveBackoffTests(unittest.TestCase):
    def test_repeated_rate_limits_back_off_across_restarts_and_success_resets_them(self):
        request = Request('https://query1.finance.yahoo.com/test')
        with tempfile.TemporaryDirectory() as folder:
            stamp = 1000
            for index, expected in enumerate((900, 1800, 3600)):
                error = HTTPError(request.full_url, 429, 'limited', {}, None)
                with patch('time.time', return_value=stamp), patch('provider.urlopen', side_effect=error):
                    with self.assertRaises(ProviderBusy) as caught:
                        _payload(request, 1, Store(folder), 'test', str(index), 1)
                    self.assertEqual(caught.exception.details['retry_seconds'], expected)
                stamp += expected + 1
            with patch('time.time', return_value=stamp), \
                 patch('provider.urlopen', return_value=io.BytesIO(b'{"ok":true}')):
                self.assertEqual(_payload(request, 1, Store(folder), 'test', 'success', 1), {'ok': True})
            with patch('time.time', return_value=stamp + 1), \
                 patch('provider.urlopen', side_effect=HTTPError(request.full_url, 429, 'limited', {}, None)):
                with self.assertRaises(ProviderBusy) as caught:
                    _payload(request, 1, Store(folder), 'test', 'next', 1)
                self.assertEqual(caught.exception.details['retry_seconds'], 900)

    def test_longer_upstream_wait_is_preserved(self):
        request = Request('https://query1.finance.yahoo.com/test')
        with tempfile.TemporaryDirectory() as folder:
            error = HTTPError(request.full_url, 429, 'limited', {'Retry-After': '7200'}, None)
            with patch('provider.urlopen', side_effect=error):
                with self.assertRaises(ProviderBusy) as caught:
                    _payload(request, 1, Store(folder), 'test', 'long', 1)
                self.assertEqual(caught.exception.details['retry_seconds'], 7200)


    def test_upstream_http_date_wait_is_preserved(self):
        request = Request('https://query1.finance.yahoo.com/test')
        with tempfile.TemporaryDirectory() as folder:
            error = HTTPError(request.full_url, 429, 'limited',
                              {'Retry-After': 'Thu, 01 Jan 1970 02:00:00 GMT'}, None)
            with patch('time.time', return_value=0), patch('provider.urlopen', side_effect=error):
                with self.assertRaises(ProviderBusy) as caught:
                    _payload(request, 1, Store(folder), 'test', 'http-date', 1)
                self.assertEqual(caught.exception.details['retry_seconds'], 7200)


class SharedDemoProviderTests(unittest.TestCase):
    def test_demo_uses_primary_provider_budget_without_writing_primary_quotes(self):
        from demo import refresh_demo_quotes
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            primary = Store(Path(folder) / 'personal')
            demo = Store(Path(folder) / 'demo')
            demo.quote('IBM', 'NYSE', 'USD', '100', '2026-01-01T12:00:00+00:00', 'DEMO')
            fetch = Mock(return_value=('110', '2026-01-02T12:00:00+00:00'))
            with patch('demo.market_weekend', return_value=False):
                refresh_demo_quotes(demo, ttl=900, fetch=fetch, provider_store=primary)
            self.assertIs(fetch.call_args.kwargs['store'], primary)
            with primary.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM quotes').fetchone()[0], 0)
            with demo.connect() as db:
                self.assertEqual(db.execute('SELECT price FROM quotes ORDER BY id DESC LIMIT 1').fetchone()[0], '110')
