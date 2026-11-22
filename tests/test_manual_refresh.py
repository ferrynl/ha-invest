"""The explicit Health Center action may run outside the automatic time window."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from cache import StateCache
from diagnostics import read_logs
from security import Auth
from storage import Store
from web import make_handler


class ManualRefreshHttpTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.auth = Auth(self.store)
        self.wake = threading.Event()
        self.manual = threading.Event()
        self.lock = threading.Lock()
        handler = make_handler(self.store, self.auth, StateCache(store=self.store), {}, 900,
                               self.lock, self.wake, manual_refresh=self.manual)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join()

    def request(self, token='', csrf=''):
        connection = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=10)
        try:
            connection.request('POST', '/api/health-action', json.dumps({'action': 'refresh'}),
                               {'Content-Type': 'application/json', 'X-Portfolio-Request': '1',
                                'Cookie': 'homeinvest_session=' + token, 'X-CSRF-Token': csrf})
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def test_health_action_queues_explicit_manual_request_and_wakes_worker(self):
        self.assertEqual(self.request(), 202)
        self.assertTrue(self.manual.is_set())
        self.assertTrue(self.wake.is_set())

    def test_busy_worker_does_not_accept_an_unstarted_request(self):
        with self.lock:
            self.assertEqual(self.request(), 409)
        self.assertFalse(self.manual.is_set())

    def test_admin_and_csrf_are_required_when_login_is_enabled(self):
        self.auth.enable('owner', 'Long-test-password-2026')
        self.assertEqual(self.request(), 401)
        token = self.auth.login('owner', 'Long-test-password-2026', 'test')
        csrf = self.auth.user(token)['csrf']
        self.assertEqual(self.request(token), 403)
        with self.store.connect() as db:
            db.execute("UPDATE users SET role='basic'")
        self.assertEqual(self.request(token, csrf), 403)
        self.assertFalse(self.manual.is_set())


class ManualRefreshWorkerTests(unittest.TestCase):
    def test_weekend_manual_sync_updates_quotes_and_logs_completion(self):
        import server
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.add(dict(symbol='IBM', exchange='NYSE', currency='USD', name='IBM',
                           quantity='1', price='100', purchased_on='2026-01-01'))
            state = {}
            with patch.object(server, 'store', store), \
                 patch.object(server, 'state_cache', StateCache(store=store)), \
                 patch.object(server, 'status', state), \
                 patch.object(server, 'market_weekend', return_value=True), \
                 patch.object(server, 'automatic_window', return_value=False), \
                 patch.object(server, 'fetch_quote', return_value=('150', '2026-11-20T21:00:00+00:00')) as quote, \
                 patch.object(server, 'fetch_history', return_value=[dict(day='2026-11-20', price='150')]) as history, \
                 patch.object(server, 'enrich_categories', return_value=False), \
                 patch('fund_holdings.background_refresh', return_value=False), patch('server.time.sleep'):
                self.assertTrue(server.refresh(manual=True))
                quote.assert_called_once()
                history.assert_called_once()
            self.assertEqual(store.state()['positions'][0]['quote']['quoted_at'][:10], '2026-11-20')
            entries = [r for r in read_logs(store)['entries'] if r['event'] == 'manual_sync_finished']
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['details']['quotes_updated'], 1)
            self.assertFalse(state['provider_paused'])

    def test_manual_sync_preserves_yahoo_cooldown_and_reports_it(self):
        import server
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.add(dict(symbol='IBM', exchange='NYSE', currency='USD', name='IBM',
                           quantity='1', price='100', purchased_on='2026-01-01'))
            state = {}
            error = HTTPError('https://query1.finance.yahoo.com/test', 429, 'limited', {}, None)
            with patch.object(server, 'store', store), \
                 patch.object(server, 'state_cache', StateCache(store=store)), \
                 patch.object(server, 'status', state), \
                 patch.object(server, 'market_weekend', return_value=True), \
                 patch.object(server, 'automatic_window', return_value=False), \
                 patch('provider.urlopen', side_effect=error) as network, \
                 patch.object(server, 'enrich_categories', return_value=False), \
                 patch('fund_holdings.background_refresh', return_value=False), patch('server.time.sleep'):
                server.refresh(manual=True)
                server.refresh(manual=True)
                network.assert_called_once()
            summary = next(r for r in read_logs(store)['entries'] if r['event'] == 'manual_sync_finished')
            self.assertEqual(summary['level'], 'WARNING')
            self.assertEqual(summary['details']['http_status'], 429)
            self.assertGreater(summary['details']['retry_seconds'], 0)
            self.assertTrue(state['provider_paused'])

    def test_explicit_request_runs_outside_window_without_starting_demo_sync(self):
        import server
        class StopLoop(BaseException):
            pass
        manual = threading.Event()
        manual.set()
        with patch.object(server, 'manual_refresh_requested', manual), \
             patch.object(server, 'automatic_window', return_value=False), \
             patch.object(server.store, 'backup'), patch.object(server, 'record'), \
             patch.object(server, 'refresh', return_value=True) as refresh, \
             patch.object(server, 'warm_dashboard'), patch.object(server, 'fx_currencies'), \
             patch.object(server, 'fx_snapshot'), patch('demo.refresh_active_demo') as demo, \
             patch.object(server.refresh_requested, 'wait', side_effect=StopLoop):
            with self.assertRaises(StopLoop):
                server.background()
            refresh.assert_called_once_with(manual=True)
            demo.assert_not_called()
            self.assertFalse(manual.is_set())
