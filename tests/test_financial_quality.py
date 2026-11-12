"""Regression tests for read-only financial checks (phase 7 and 8)."""
import unittest
from decimal import Decimal
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio/app'))
from financial_quality import inspect_transactions, reconcile_quantities


def tx(id, broker="A", symbol="NN", day="2026-11-01", side="buy", quantity="2", price="10", source_id=None):
    return {"id": id, "broker": broker, "symbol": symbol, "date": day,
            "side": side, "quantity": quantity, "price": price, "source_id": source_id}


class QualityTests(unittest.TestCase):
    def test_duplicate_scoped_by_broker(self):
        rows = [tx("1", source_id="abc"), tx("2", source_id="abc"),
                tx("3", broker="B", source_id="abc")]
        issues = inspect_transactions(rows)
        self.assertEqual(sum(x["code"] == "duplicate_source_id" for x in issues), 1)
        self.assertEqual(sum(x["code"] == "possible_duplicate" for x in issues), 1)

    def test_invalid_values_do_not_crash(self):
        issues = inspect_transactions([tx("1", day="0026-01-01", quantity="NaN", price="Infinity")])
        self.assertEqual({x["code"] for x in issues},
                         {"invalid_date", "invalid_quantity", "invalid_price"})

    def test_broker_isolation_and_precision(self):
        rows = [tx("1", quantity="0.1"), tx("2", quantity="0.2"),
                tx("3", broker="B", quantity="3")]
        positions = [{"broker": "A", "symbol": "NN", "quantity": "0.3"},
                     {"broker": "B", "symbol": "NN", "quantity": "2"}]
        findings = reconcile_quantities(rows, positions)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["broker"], "B")
        self.assertEqual(Decimal(findings[0]["difference"]), Decimal("-1"))

    def test_unsupported_actions_not_reconciled(self):
        rows = [tx("1", side="split")]
        positions = [{"broker": "A", "symbol": "NN", "quantity": "4"}]
        self.assertEqual(reconcile_quantities(rows, positions), [])

    def test_large_batch(self):
        rows = [tx(str(i), broker=str(i), source_id=str(i)) for i in range(10000)]
        self.assertEqual(inspect_transactions(rows), [])


if __name__ == "__main__":
    unittest.main()
