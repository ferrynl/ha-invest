"""Automatic market traffic follows local weekends and actual demo use."""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from market_schedule import market_weekend
from storage import Store


class WeekendTests(unittest.TestCase):
    def test_listing_timezone_decides_weekend_instead_of_host_date(self):
        for exchange, stamp, expected in (
            ('NYSE', '2026-11-21T04:59:00+00:00', False),
            ('NYSE', '2026-11-21T05:00:00+00:00', True),
            ('NYSE', '2026-07-18T03:59:00+00:00', False),
            ('NYSE', '2026-07-18T04:00:00+00:00', True),
            ('ASX', '2026-11-22T22:00:00+00:00', False),
            ('TOKYO', '2026-11-22T15:00:00+00:00', False),
            ('AMSTERDAM', '2026-11-21T12:00:00+00:00', True),
        ):
            with self.subTest(exchange=exchange, stamp=stamp):
                self.assertEqual(market_weekend(exchange, datetime.fromisoformat(stamp)), expected)

    def test_unknown_market_uses_utc_calendar(self):
        self.assertTrue(market_weekend('UNKNOWN', datetime(2026, 11, 21, 12, tzinfo=timezone.utc)))


class RefreshScheduleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def add(self, symbol='IBM', side='BUY', account_id=1):
        self.store.add(dict(symbol=symbol, exchange='NYSE', currency='USD', name=symbol,
                            quantity='1', price='100', side=side, account_id=account_id,
                            purchased_on='2026-01-01' if side == 'BUY' else '2026-01-02'))

    def run_refresh(self, weekend=False):
        import server
        from cache import StateCache
        with patch.object(server, 'store', self.store), \
             patch.object(server, 'state_cache', StateCache(store=self.store)), \
             patch.object(server, 'status', {}), \
             patch.object(server, 'market_weekend', return_value=weekend), \
             patch.object(server, 'fetch_quote', return_value=('110', '2026-01-03T10:00:00+00:00')) as quote, \
             patch.object(server, 'fetch_history', return_value=[dict(day='2026-01-01', price='100')]) as history, \
             patch.object(server, 'enrich_categories', return_value=False), \
             patch('fund_holdings.background_refresh', return_value=False), patch('server.time.sleep'):
            server.refresh()
            return quote.call_count, history.call_count

    def test_weekend_has_no_automatic_quote_or_history_calls(self):
        self.add()
        self.assertEqual(self.run_refresh(weekend=True), (0, 0))
        self.assertEqual(self.run_refresh(weekend=False), (1, 1))

    def test_closed_position_keeps_history_backfill_without_requesting_a_live_quote(self):
        self.add()
        self.add(side='SELL')
        self.assertEqual(self.run_refresh(), (0, 1))

    def test_same_listing_still_updates_when_another_broker_holds_it(self):
        self.add()
        self.add(side='SELL')
        self.store.add_account(dict(name='Other', broker='Trading 212'))
        self.add(account_id=2)
        self.assertEqual(self.run_refresh(), (1, 1))

    def test_historical_internal_symbol_never_reaches_yahoo(self):
        self.add('WOLF.OLD')
        self.assertEqual(self.run_refresh(), (0, 0))


class DemoActivityTests(unittest.TestCase):
    def test_unused_or_expired_demo_does_not_create_or_fetch_data(self):
        import demo
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'demo'
            with patch.dict(demo._demo_active_until, {}, clear=True), \
                 patch('demo.ensure_demo') as seed, patch('demo.refresh_demo_quotes') as quotes:
                self.assertFalse(demo.refresh_active_demo(root))
                seed.assert_not_called()
                quotes.assert_not_called()
            with patch.dict(demo._demo_active_until, {str(root.resolve()): 100}, clear=True), \
                 patch('demo.time.monotonic', return_value=101), \
                 patch('demo.ensure_demo') as seed, patch('demo.refresh_demo_quotes') as quotes:
                self.assertFalse(demo.refresh_active_demo(root))
                seed.assert_not_called()
                quotes.assert_not_called()

    def test_active_demo_uses_configured_interval_and_stops_after_activity_expires(self):
        import demo
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'demo'
            with patch.dict(demo._demo_active_until, {str(root.resolve()): 1000}, clear=True), \
                 patch('demo.time.monotonic', return_value=100), \
                 patch('demo.ensure_demo', return_value=self) as seed, \
                 patch('demo.refresh_demo_quotes') as quotes:
                self.assertTrue(demo.refresh_active_demo(root, ttl=1800))
                seed.assert_called_once_with(root)
                quotes.assert_called_once_with(self, ttl=1800)

    def test_demo_skips_weekend_quotes(self):
        from demo import refresh_demo_quotes
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.quote('IBM', 'NYSE', 'USD', '100', '2026-01-01T12:00:00+00:00', 'DEMO')
            fetch = Mock()
            with patch('demo.market_weekend', return_value=True):
                refresh_demo_quotes(store, fetch=fetch)
            fetch.assert_not_called()
