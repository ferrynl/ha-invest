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
