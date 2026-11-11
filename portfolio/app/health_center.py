"""Read-only health checks; no portfolio repairs or external requests."""
import shutil
import sqlite3
from datetime import datetime, timezone
from contextlib import closing
from migrations import SCHEMA_VERSION


def snapshot(store, auth):
    checks = []
    def add(key, status, detail):
        checks.append(dict(key=key, status=status, detail=detail))
    try:
        with store.read() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            healthy = db.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
            add("database", "ok" if healthy and version == SCHEMA_VERSION else "error",
                str(version) + " / " + str(SCHEMA_VERSION))
            keys = db.execute("SELECT COUNT(*) FROM passkeys").fetchone()[0]
            add("passkeys", "ok" if keys else "warning", str(keys))
    except sqlite3.Error:
        add("database", "error", "SQLite")
        add("passkeys", "unknown", "")
    disk = shutil.disk_usage(store.root)
    free = disk.free / disk.total if disk.total else 0
    add("storage", "error" if free < .05 else "warning" if free < .15 else "ok",
        f"{disk.free / 1024**3:.2f} GiB")
    add("authentication", "ok" if auth.enabled() else "warning", "")
    folder = store.root / "backups"
    try:
        files = sorted((p for p in folder.glob("portfolio-*.sqlite3")
                        if not p.is_symlink() and p.is_file()), reverse=True)
        if not files:
            add("backup", "warning", "")
        else:
            path = files[0]
            age = max(0, (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400)
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
                db.execute("PRAGMA trusted_schema=OFF")
                valid = db.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok"
                version = db.execute("PRAGMA user_version").fetchone()[0]
                valid = valid and 1 <= version <= SCHEMA_VERSION
            add("backup", "error" if not valid else "warning" if age > 7 else "ok",
                f"{age:.1f} d")
    except (OSError, sqlite3.Error):
        add("backup", "error", "")
    return dict(checked_at=datetime.now(timezone.utc).isoformat(), checks=checks)
