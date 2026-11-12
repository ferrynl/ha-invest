"""Phase 9: busy SQLite must not cause a blind retry of financial writes."""
import http.client
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio/app"))
from storage import Store
from security import Auth
from cache import StateCache
from web import make_handler


class DatabaseLockResponseTests(unittest.TestCase):
    def test_sqlite_lock_returns_actionable_503_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            auth = Auth(store)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, auth, StateCache(), {}, 900,
                             threading.Lock(), threading.Event(), enable_demo=False),
            )
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            transaction = dict(
                symbol="ASML.AS", exchange="AMSTERDAM", currency="EUR",
                name="ASML", purchased_on="2026-01-12", quantity="1", price="100"
            )
            try:
                with patch.object(store, "add", side_effect=sqlite3.OperationalError("database is locked")) as add:
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
                    try:
                        payload = json.dumps(transaction)
                        connection.request(
                            "POST", "/api/purchases", payload,
                            {"Content-Type": "application/json", "X-Portfolio-Request": "1"},
                        )
                        response = connection.getresponse()
                        body = json.loads(response.read())
                    finally:
                        connection.close()
                    self.assertEqual(response.status, 503)
                    self.assertIn("Controleer eerst", body["error"])
                    add.assert_called_once()
                self.assertEqual(store.state()["purchases"], [])
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


if __name__ == "__main__":
    unittest.main()
