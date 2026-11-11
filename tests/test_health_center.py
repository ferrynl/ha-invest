import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio/app"))
from storage import Store
from security import Auth
from health_center import snapshot


class HealthCenterTests(unittest.TestCase):
    def test_health_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            auth = Auth(store)
            def checks():
                return {item["key"]: item for item in snapshot(store, auth)["checks"]}
            self.assertEqual(checks()["database"]["status"], "ok")
            self.assertEqual(checks()["authentication"]["status"], "warning")
            self.assertEqual(checks()["backup"]["status"], "warning")
            auth.enable("healthowner", "Health-test-password-2026")
            self.assertEqual(checks()["authentication"]["status"], "ok")
            backup = store.backup()
            self.assertEqual(checks()["backup"]["status"], "ok")
            backup.write_bytes(b"not sqlite")
            self.assertEqual(checks()["backup"]["status"], "error")

    def test_financial_findings_do_not_modify_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            auth = Auth(store)
            trade = dict(symbol="ASML.AS", exchange="AMSTERDAM", currency="EUR",
                         name="ASML", quantity="1", price="100", purchased_on="2025-01-10")
            store.add(trade)
            store.add(trade)
            before = store.state()["purchases"]
            checks = {item["key"]: item for item in snapshot(store, auth)["checks"]}
            self.assertEqual(checks["missing_quotes"]["status"], "warning")
            self.assertEqual(checks["duplicate_trades"]["detail"], "1")
            self.assertEqual(checks["missing_fx"]["status"], "ok")
            self.assertEqual(store.state()["purchases"], before)
