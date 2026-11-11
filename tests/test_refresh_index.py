import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio" / "app"))
from refresh_index import purchase_index


class RefreshIndexTests(unittest.TestCase):
    def test_earliest_date_and_transferred_sells(self):
        purchases = [
            dict(symbol="AAA", exchange="NYSE", currency="USD", purchased_on="2025-04-01", side="BUY"),
            dict(symbol="BBB", exchange="NASDAQ", currency="USD", purchased_on="2026-01-01", side="BUY"),
            dict(symbol="AAA", exchange="NYSE", currency="USD", purchased_on="2024-03-01", side="BUY"),
            dict(symbol="AAA", exchange="NYSE", currency="USD", purchased_on="2026-05-01", side="SELL", transfer_id="t1"),
            dict(symbol="AAA", exchange="NYSE", currency="EUR", purchased_on="2023-01-01", side="BUY"),
        ]
        dates, transfers = purchase_index(purchases)
        self.assertEqual(dates[("AAA", "NYSE", "USD")], "2024-03-01")
        self.assertEqual(dates[("AAA", "NYSE", "EUR")], "2023-01-01")
        self.assertEqual(dates[("BBB", "NASDAQ", "USD")], "2026-01-01")
        self.assertEqual(transfers, {("AAA", "NYSE", "USD")})

    def test_empty_and_missing_dates(self):
        self.assertEqual(purchase_index([]), ({}, set()))
        dates, transfers = purchase_index([
            dict(symbol="X", exchange="LSE", currency="GBP", purchased_on="", side="BUY"),
        ])
        self.assertEqual(dates, {})
        self.assertEqual(transfers, set())

    def test_large_portfolio(self):
        rows = [dict(symbol=f"S{i % 500}", exchange="NYSE", currency="USD",
                     purchased_on=f"2025-01-{i % 28 + 1:02d}", side="BUY") for i in range(10000)]
        dates, transfers = purchase_index(rows)
        self.assertEqual(len(dates), 500)
        self.assertFalse(transfers)
