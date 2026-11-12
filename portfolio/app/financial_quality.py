"""Read-only financial data-quality checks for Home Invest.

This module does not modify transactions, prices, broker holdings or SQLite.
Callers must normalize records and explicitly provide the current holdings.
Amounts are represented using Decimal to avoid float drift.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Any


def _decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return 1900 <= parsed.year <= date.today().year + 1


def inspect_transactions(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Flag invalid rows and *possible* duplicates without deleting anything.

    Required normalized fields: id, broker, symbol, date, side, quantity.
    Optional: price, source_id. Duplicate matching is strictly broker scoped.
    A matching fingerprint is a warning, not proof of duplicate booking.
    """
    issues: list[dict[str, Any]] = []
    seen_ids: dict[tuple[str, str], str] = {}
    seen_fingerprints: dict[tuple[str, ...], str] = {}
    for row in records:
        ident = str(row.get("id") or "")
        broker = str(row.get("broker") or "").strip()
        symbol = str(row.get("symbol") or "").strip().upper()
        day = row.get("date")
        side = str(row.get("side") or "").strip().lower()
        qty = _decimal(row.get("quantity"))
        price = _decimal(row.get("price")) if row.get("price") is not None else None
        def flag(code: str, detail: str) -> None:
            issues.append({"code": code, "transaction_id": ident, "detail": detail})
        if not broker or not symbol:
            flag("missing_identity", "Broker or instrument is missing")
        if not _date(day):
            flag("invalid_date", "Invalid transaction date")
        if side not in {"buy", "sell"}:
            flag("unknown_side", "Transaction type requires manual review")
        if qty is None or qty <= 0:
            flag("invalid_quantity", "Quantity must be positive and finite")
        if row.get("price") is not None and (price is None or price < 0):
            flag("invalid_price", "Price must be nonnegative and finite")
        source_id = str(row.get("source_id") or "").strip()
        if broker and source_id:
            key = (broker, source_id)
            if key in seen_ids:
                flag("duplicate_source_id", "Possible duplicate source ID; compare with transaction " + seen_ids[key])
            else:
                seen_ids[key] = ident
        if broker and symbol and _date(day) and qty is not None and qty > 0 and side in {"buy", "sell"}:
            fingerprint = (broker, symbol, str(day), side, str(qty.normalize()), str(price.normalize()) if price is not None else "")
            if fingerprint in seen_fingerprints:
                flag("possible_duplicate", "Same transaction fields as " + seen_fingerprints[fingerprint])
            else:
                seen_fingerprints[fingerprint] = ident
    return issues


def reconcile_quantities(
    transactions: Iterable[Mapping[str, Any]],
    holdings: Iterable[Mapping[str, Any]],
    tolerance: Decimal = Decimal("0.00000001"),
) -> list[dict[str, str]]:
    """Compare normalized buy/sell ledger with broker holdings, read-only.

    Only instruments whose *full* history consists of valid buy/sell records
    should be supplied. Corporate actions, transfers and incomplete imports
    require reconciliation by the calling application before using this.
    """
    totals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    invalid: set[tuple[str, str]] = set()
    for row in transactions:
        key = (str(row.get("broker") or ""), str(row.get("symbol") or "").upper())
        quantity = _decimal(row.get("quantity"))
        side = str(row.get("side") or "").lower()
        if not all(key) or quantity is None or quantity <= 0 or side not in {"buy", "sell"}:
            invalid.add(key)
            continue
        totals[key] += quantity if side == "buy" else -quantity
    findings: list[dict[str, str]] = []
    for holding in holdings:
        key = (str(holding.get("broker") or ""), str(holding.get("symbol") or "").upper())
        reported = _decimal(holding.get("quantity"))
        if key in invalid or not all(key) or reported is None:
            continue
        expected = totals.get(key, Decimal(0))
        if abs(expected - reported) > tolerance:
            findings.append({"code": "quantity_mismatch", "broker": key[0], "symbol": key[1],
                             "ledger": str(expected), "holding": str(reported),
                             "difference": str(reported - expected)})
    return findings
