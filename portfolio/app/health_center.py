"""Read-only health checks; no portfolio repairs or external requests."""
import shutil
import sqlite3
from datetime import datetime, timezone, date
from decimal import Decimal
from collections import Counter
from contextlib import closing
from migrations import SCHEMA_VERSION
from financial_quality import inspect_transactions


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
    try:
        with store.read() as db:
            state = store._state(db, True, 'all')
            fx = {r[0] for r in db.execute("SELECT DISTINCT quote FROM fx_rates WHERE base='EUR'")}
            pending = db.execute("SELECT COUNT(*) FROM instrument_mappings WHERE origin='pending' OR symbol='' OR exchange=''").fetchone()[0]
        findings = financial_checks(state, fx, pending)
        checks.extend(findings)
    except (sqlite3.Error, ArithmeticError, ValueError, KeyError, TypeError):
        for key in FINANCIAL_KEYS:
            add(key, "unknown", "")
    return dict(checked_at=datetime.now(timezone.utc).isoformat(), checks=checks)


FINANCIAL_KEYS = ("missing_quotes", "stale_quotes", "duplicate_trades", "invalid_positions", "unusual_returns", "missing_fx", "pending_mappings", "invalid_dividends", "invalid_trades")


def financial_checks(state, fx, pending, today=None):
    today = today or date.today()
    issues = {key: [] for key in FINANCIAL_KEYS}
    def label(row):
        return f"{row['symbol']} · {row['exchange']} · {row['currency']} · #{row['account_id']}"
    def number(value):
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError()
        return result
    for row in state["positions"]:
        name = label(row)
        if row.get("invalid_position"):
            issues["invalid_positions"].append(name)
            continue
        if number(row["quantity"]) <= 0:
            continue
        quote = row.get("quote")
        if not quote:
            issues["missing_quotes"].append(name)
        elif not row.get("quote_paused"):
            try:
                if (today - date.fromisoformat(quote["quoted_at"][:10])).days > 7:
                    issues["stale_quotes"].append(name)
            except (ValueError, KeyError, TypeError):
                issues["stale_quotes"].append(name)
        if row["currency"] != "EUR" and row["currency"] not in fx:
            issues["missing_fx"].append(name)
        cost = number(row["cost"])
        if cost > 0 and row.get("value") is not None:
            change = (number(row["value"]) - cost) / cost
            if change > 5 or change < Decimal("-0.9"):
                issues["unusual_returns"].append(name)
    fields = ("account_id", "symbol", "exchange", "currency", "purchased_on", "trade_time", "side", "quantity", "price", "split_before")
    trades = Counter(tuple(row.get(k) for k in fields) for row in state["purchases"])
    for identity, count in trades.items():
        if count > 1:
            issues["duplicate_trades"].append(f"{identity[1]} · {identity[2]} · {identity[3]} · #{identity[0]} · {identity[4]} × {count}")
    # Transactions may include corporate actions (splits/transfers). Validate
    # only plain buys and sells; never report unsupported actions as errors.
    # Existing duplicate_trades already covers same-field duplicates, so
    # the new validator contributes only data-invalidity findings here.
    ordinary_trades = (
        dict(id=row.get("id"), broker=str(row.get("account_id") or ""),
             symbol=row.get("symbol"), date=row.get("purchased_on"),
             side=str(row.get("side") or "").lower(),
             quantity=row.get("quantity"), price=row.get("price"))
        for row in state["purchases"]
        if str(row.get("side") or "").upper() in {"BUY", "SELL"}
    )
    for finding in inspect_transactions(ordinary_trades):
        if finding["code"] in {"missing_identity", "invalid_date", "invalid_quantity", "invalid_price"}:
            issues["invalid_trades"].append(
                f'#{finding["transaction_id"]} · {finding["code"]}'
            )
    for row in state["dividends"]:
        try:
            day = date.fromisoformat(row["paid_on"])
            if day > today or day.year < 1900 or number(row["amount"]) <= 0:
                raise ValueError()
        except (ValueError, ArithmeticError, TypeError):
            issues["invalid_dividends"].append(label(row))
    result = []
    for key, values in issues.items():
        count = pending if key == "pending_mappings" else len(values)
        result.append(dict(key=key, status="warning" if count else "ok", detail=str(count), examples=values[:10]))
    return result
