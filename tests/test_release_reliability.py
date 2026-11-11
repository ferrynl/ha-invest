"""Release regression tests using disposable databases only."""
import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest
import time
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio/app"))
from storage import Store
from security import Auth, password_hash
from migrations import MIGRATIONS, SCHEMA_VERSION
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

    def test_upgrade_historical_schemas_preserves_data_and_backup(self):
        for version in (6, 11, 19, 24):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "portfolio.sqlite3"
                password = "Historical-test-password-2026"
                with closing(sqlite3.connect(path)) as db:
                    for number in range(1, version + 1):
                        for statement in MIGRATIONS[number]:
                            db.execute(statement)
                        db.execute(f"PRAGMA user_version={number}")
                    db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES(?,?,?,?,?,?,?,?)",
                               ("ASML.AS", "AMSTERDAM", "ASML", "10", "100", "EUR", "2025-01-10", "2025-01-10"))
                    db.execute("INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at) VALUES(?,?,?,?,?,?,?)",
                               ("ASML.AS", "AMSTERDAM", "EUR", "25", "2025-02-10", "", "2025-02-10"))
                    db.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                               ("legacyowner", password_hash(password), "admin", "2025-01-10"))
                    db.execute("UPDATE app_settings SET value='true' WHERE key='auth_enabled'")
                    db.commit()
                store = Store(folder)
                with store.connect() as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
                    self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                state = store.state()
                self.assertEqual(Decimal(state["purchases"][0]["quantity"]), 10)
                self.assertEqual(Decimal(state["dividends"][0]["amount"]), 25)
                self.assertTrue(Auth(store).login("legacyowner", password, "test"))
                backups = list((Path(folder) / "backups/migrations").glob("*.sqlite3"))
                self.assertEqual(len(backups), 1)
                with closing(sqlite3.connect(backups[0])) as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], version)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0], 1)
                Store(folder)
                self.assertEqual(len(list((Path(folder) / "backups/migrations").glob("*.sqlite3"))), 1)

    def test_ten_thousand_trades_compact_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            # Bulk fixture keeps CI setup fast; calculations use production code.
            with store.connect() as db:
                db.executemany(
                    "INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    [("ASML.AS", "AMSTERDAM", "ASML", "1", "100", "EUR", "2025-01-10", "2025-01-10")] * 10000)
            started = time.monotonic()
            state = store.state(compact_view=True)
            elapsed = time.monotonic() - started
            self.assertEqual(len(state["purchases"]), 10000)
            self.assertEqual(sum(Decimal(p["quantity"]) for p in state["positions"]), 10000)
            self.assertEqual(sum(Decimal(p["cost"]) for p in state["positions"]), 1000000)
            print(f"Compact state, 10000 trades: {elapsed:.3f}s")
            self.assertLess(elapsed, 30)
