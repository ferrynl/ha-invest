"""Session reads should not contend with financial writes on every request."""
import hashlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "portfolio" / "app"))
from security import Auth, SESSION_TTL, SESSION_MAX_AGE


class TestStore:
    def __init__(self, path):
        self.path = path

    def settings(self):
        return {"auth_enabled": "true"}

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=1)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()


class SessionReadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = TestStore(str(Path(self.folder.name) / "test.sqlite3"))
        self.token = "test-token"
        self.key = hashlib.sha256(self.token.encode()).hexdigest()
        with self.store._connect() as db:
            db.executescript("""
              CREATE TABLE auth_sessions
                (token_hash TEXT PRIMARY KEY, user_id INTEGER, revision INTEGER,
                 csrf TEXT, expires_at REAL, absolute_expiry REAL);
              CREATE TABLE users
                (id INTEGER PRIMARY KEY, username TEXT, role TEXT,
                 active INTEGER, revision INTEGER, language TEXT);
              INSERT INTO users VALUES (1, 'test', 'admin', 1, 1, 'nl');
            """)
            db.execute("INSERT INTO auth_sessions VALUES (?,?,?,?,?,?)",
                       (self.key, 1, 1, "csrf", 1000+SESSION_TTL, 1000+SESSION_MAX_AGE))
        self.auth = Auth(self.store)

    def expiry(self):
        with self.store._connect() as db:
            return db.execute("SELECT expires_at FROM auth_sessions WHERE token_hash=?",
                              (self.key,)).fetchone()["expires_at"]

    def test_normal_reads_do_not_write_or_require_writer_lock(self):
        # Holding the SQLite write lock would break the old BEGIN IMMEDIATE path.
        locker = sqlite3.connect(self.store.path, timeout=1)
        try:
            locker.execute("BEGIN IMMEDIATE")
            with patch("security.time.time", return_value=1010):
                self.assertEqual("test", self.auth.user(self.token)["username"])
            self.assertEqual(1000+SESSION_TTL, self.expiry())
        finally:
            locker.rollback()
            locker.close()

    def test_renews_near_expiry(self):
        with patch("security.time.time", return_value=1000+SESSION_TTL-120):
            self.assertEqual("test", self.auth.user(self.token)["username"])
        self.assertEqual(1000+SESSION_TTL-120+SESSION_TTL, self.expiry())

    def test_rejects_expired_session(self):
        with patch("security.time.time", return_value=1000+SESSION_TTL+1):
            self.assertIsNone(self.auth.user(self.token))

    def test_rejects_revoked_user_revision(self):
        with self.store._connect() as db:
            db.execute("UPDATE users SET revision=2 WHERE id=1")
        with patch("security.time.time", return_value=1010):
            self.assertIsNone(self.auth.user(self.token))

    def test_unauthenticated_request_is_not_session_write(self):
        with patch("security.time.time", return_value=1010):
            self.assertIsNone(self.auth.user(""))


if __name__ == "__main__":
    unittest.main()
