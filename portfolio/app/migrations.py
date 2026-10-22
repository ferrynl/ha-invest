"""Ordered, transactional SQLite upgrades. Never silently downgrade a database."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

SCHEMA_VERSION = 13
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
    5: (
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','basic')), active INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)",
        "INSERT INTO app_settings VALUES('auth_enabled','false')",
    ),
    6: (
        "CREATE TABLE broker_accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, broker TEXT NOT NULL, created_at TEXT NOT NULL)",
        "INSERT INTO broker_accounts VALUES(1,'Handmatig','Handmatig',strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
        'ALTER TABLE purchases ADD COLUMN account_id INTEGER NOT NULL DEFAULT 1 REFERENCES broker_accounts(id)',
        "ALTER TABLE purchases ADD COLUMN side TEXT NOT NULL DEFAULT 'BUY' CHECK(side IN ('BUY','SELL'))",
        "ALTER TABLE purchases ADD COLUMN trade_time TEXT NOT NULL DEFAULT ''",
        'ALTER TABLE dividends ADD COLUMN account_id INTEGER NOT NULL DEFAULT 1 REFERENCES broker_accounts(id)',
        'CREATE TABLE api_cache (namespace TEXT NOT NULL, cache_key TEXT NOT NULL, payload TEXT NOT NULL, fetched_at REAL NOT NULL, expires_at REAL NOT NULL, PRIMARY KEY(namespace,cache_key))',
        "CREATE TABLE import_batches (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES broker_accounts(id), provider TEXT NOT NULL, filename TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'preview', created_at TEXT NOT NULL)",
        'CREATE TABLE import_records (id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES import_batches(id), account_id INTEGER NOT NULL REFERENCES broker_accounts(id), provider TEXT NOT NULL, external_id TEXT NOT NULL, digest TEXT NOT NULL, raw TEXT NOT NULL, UNIQUE(account_id,provider,external_id))',
    ),
    7: (
        'CREATE TABLE app_logs (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, level TEXT NOT NULL, source TEXT NOT NULL, event TEXT NOT NULL, message TEXT NOT NULL, details TEXT NOT NULL, reference TEXT NOT NULL)',
        'CREATE INDEX app_logs_time ON app_logs(created_at)',
    ),
    8: (
        'CREATE TABLE fx_currencies (code TEXT PRIMARY KEY, name TEXT NOT NULL, updated_at TEXT NOT NULL)',
        'CREATE TABLE fx_rates (base TEXT NOT NULL, quote TEXT NOT NULL, day TEXT NOT NULL, rate TEXT NOT NULL, source TEXT NOT NULL, fetched_at TEXT NOT NULL, PRIMARY KEY(base,quote,day))',
        'CREATE TABLE fx_coverage (currency TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL, checked_at TEXT NOT NULL, PRIMARY KEY(currency,start,end))',
        'CREATE TABLE import_fx (id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES import_batches(id), external_id TEXT NOT NULL, kind TEXT NOT NULL, source_currency TEXT NOT NULL, target_currency TEXT NOT NULL, original_amount TEXT NOT NULL, converted_amount TEXT NOT NULL, rate TEXT NOT NULL, requested_on TEXT NOT NULL, rate_on TEXT NOT NULL, source TEXT NOT NULL, UNIQUE(batch_id,external_id))',
    ),
    9: (
        "CREATE TABLE instrument_mappings (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES broker_accounts(id), provider TEXT NOT NULL, identity TEXT NOT NULL, ticker TEXT NOT NULL, isin TEXT NOT NULL, source_currency TEXT NOT NULL, symbol TEXT NOT NULL DEFAULT '', exchange TEXT NOT NULL DEFAULT '', currency TEXT NOT NULL DEFAULT '', name TEXT NOT NULL DEFAULT '', origin TEXT NOT NULL DEFAULT 'pending', updated_at TEXT NOT NULL, UNIQUE(account_id,provider,identity,source_currency))",
    ),
    10: (
        "CREATE TABLE import_issues (id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES import_batches(id), line INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','resolved','ignored')), reason TEXT NOT NULL, payload TEXT NOT NULL, resolution TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, UNIQUE(batch_id,line))",
        "CREATE TABLE capital_returns (id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES import_batches(id), account_id INTEGER NOT NULL REFERENCES broker_accounts(id), provider TEXT NOT NULL, external_id TEXT NOT NULL, ticker TEXT NOT NULL, isin TEXT NOT NULL, amount TEXT NOT NULL, currency TEXT NOT NULL, paid_on TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(account_id,provider,external_id))",
    ),
    11: (
        "ALTER TABLE purchases ADD COLUMN split_before TEXT NOT NULL DEFAULT ''",
    ),
    12: (
        "CREATE TABLE transaction_edits (id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('trade','dividend','capital')), record_id INTEGER NOT NULL, account_id INTEGER NOT NULL REFERENCES broker_accounts(id), before_payload TEXT NOT NULL, after_payload TEXT NOT NULL, changed_by TEXT NOT NULL, created_at TEXT NOT NULL)",
        'CREATE INDEX transaction_edits_record ON transaction_edits(kind,record_id,id)',
    ),
    13: (
        "CREATE TABLE instrument_categories (symbol TEXT NOT NULL, exchange TEXT NOT NULL, currency TEXT NOT NULL, sector TEXT NOT NULL DEFAULT '', country TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, PRIMARY KEY(symbol,exchange,currency))",
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
