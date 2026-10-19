"""Ordered, transactional SQLite upgrades. Never silently downgrade a database."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

SCHEMA_VERSION = 4
MIGRATIONS = {
    1: (
        'CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, exchange TEXT NOT NULL, name TEXT NOT NULL, quantity TEXT NOT NULL, price TEXT NOT NULL, currency TEXT NOT NULL, purchased_on TEXT NOT NULL, created_at TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, exchange TEXT NOT NULL, currency TEXT NOT NULL, price TEXT NOT NULL, quoted_at TEXT NOT NULL, fetched_at TEXT NOT NULL, source TEXT NOT NULL)',
        'CREATE INDEX IF NOT EXISTS quote_instrument ON quotes(symbol,exchange,currency,id)',
    ),
    2: (
        'CREATE TABLE IF NOT EXISTS daily_prices (symbol TEXT NOT NULL, exchange TEXT NOT NULL, currency TEXT NOT NULL, day TEXT NOT NULL, price TEXT NOT NULL, PRIMARY KEY(symbol,exchange,currency,day))',
        'CREATE TABLE IF NOT EXISTS history_sync (symbol TEXT NOT NULL, exchange TEXT NOT NULL, currency TEXT NOT NULL, start TEXT NOT NULL, synced_on TEXT NOT NULL, PRIMARY KEY(symbol,exchange,currency))',
    ),
    3: (
        'CREATE TABLE IF NOT EXISTS dividends (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, exchange TEXT NOT NULL, currency TEXT NOT NULL, amount TEXT NOT NULL, paid_on TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL)',
    ),
    4: (
        'CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
        "INSERT INTO app_settings VALUES('default_range','1M')",
    ),
}

def migrate(path):
    path = Path(path)
    with closing(sqlite3.connect(path, timeout=30)) as db:
        current = db.execute('PRAGMA user_version').fetchone()[0]
        if current > SCHEMA_VERSION:
            raise RuntimeError(f'Databaseversie {current} is nieuwer dan ondersteund ({SCHEMA_VERSION}). Installeer een nieuwere app; de database is niet aangepast.')
        if current == SCHEMA_VERSION:
            return
        has_tables = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        if has_tables:
            folder = path.parent / 'backups' / 'migrations'
            folder.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            with closing(sqlite3.connect(folder / f'before-v{current}-to-v{SCHEMA_VERSION}-{stamp}.sqlite3')) as target:
                db.backup(target)
        try:
            db.execute('BEGIN IMMEDIATE')
            # Recheck after locking in case another process completed the upgrade.
            current = db.execute('PRAGMA user_version').fetchone()[0]
            if current > SCHEMA_VERSION:
                raise RuntimeError('Database is inmiddels naar een nieuwere versie bijgewerkt.')
            for version in range(current + 1, SCHEMA_VERSION + 1):
                for statement in MIGRATIONS[version]:
                    db.execute(statement)
                db.execute(f'PRAGMA user_version={version}')
            db.commit()
        except Exception:
            db.rollback()
            raise
