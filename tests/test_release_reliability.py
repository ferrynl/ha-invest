"""Release regression tests using disposable databases only."""
import sys
import tempfile
import unittest
import time
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio/app"))
from storage import Store
from security import Auth
from restore import restore_backup

STOCK = dict(symbol="ASML.AS", exchange="AMSTERDAM", currency="EUR", name="ASML")


class ReleaseReliabilityTests(unittest.TestCase):
    def test_restart_and_restore_preserve_portfolio_and_live_login(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            auth = Auth(store)
            password = "Release-test-password-2026"
            auth.enable("releaseowner", password)
            store.add_account(dict(name="Test broker", broker="Trading 212"))
            store.add(dict(**STOCK, account_id=2, quantity="10", price="100",
                           purchased_on="2025-01-10"))
            store.add_dividend(dict(**STOCK, account_id=2, amount="25",
                                    paid_on="2025-02-10"))
            backup = store.backup().read_bytes()
            original = store.state()
            reopened = Store(folder)
            self.assertEqual(reopened.state()["purchases"], original["purchases"])
            self.assertEqual(reopened.state()["dividends"], original["dividends"])
            self.assertTrue(Auth(reopened).login("releaseowner", password, "test"))
            reopened.add(dict(**STOCK, account_id=2, quantity="2", price="100",
                              purchased_on="2025-03-10"))
            restore_backup(reopened, backup)
            restored = reopened.state()
            self.assertEqual(restored["purchases"], original["purchases"])
            self.assertEqual(restored["dividends"], original["dividends"])
            self.assertTrue(Auth(reopened).login("releaseowner", password, "test"))
            with reopened.connect() as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_large_ledger_compact_state_preserves_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            # Use a deterministic fixture; no external market data.
            for i in range(1000):
                store.add(dict(**STOCK, quantity="1", price="100",
                               purchased_on="2025-01-10"))
            started = time.monotonic()
            state = store.state(compact_view=True)
            elapsed = time.monotonic() - started
            self.assertEqual(len(state["purchases"]), 1000)
            self.assertEqual(sum(Decimal(p["quantity"]) for p in state["positions"]), 1000)
            self.assertEqual(sum(Decimal(p["cost"]) for p in state["positions"]), 100000)
            print(f"Compact state, 1000 trades: {elapsed:.3f}s")
            # Generous regression guard for shared CI runners, not a production SLA.
            self.assertLess(elapsed, 30)
