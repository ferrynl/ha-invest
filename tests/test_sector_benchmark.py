import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio/app'))
from sector_benchmark import compare
from storage import Store


class SectorBenchmarkTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(directory.name)
        self.today = date(2026, 10, 30)
        self.position = dict(symbol='TEST', exchange='AMSTERDAM', currency='EUR',
                             quantity='2', categories={'sector': 'Technologie'})

    def test_comparison_uses_same_dates_and_dated_eur_conversion(self):
        prices = [('2026-10-01', '50', '2'), ('2026-10-30', '60', '2.4')]
        with self.store.connect() as db:
            for day, price, rate in prices:
                db.execute("INSERT INTO daily_prices VALUES('TEST','AMSTERDAM','EUR',?,?)", (day, price))
                db.execute("INSERT INTO fx_rates VALUES('EUR','USD',?,?,'Test','2026-10-30T00:00:00Z')", (day, rate))
        benchmark = [dict(day='2026-10-01', price='100'), dict(day='2026-10-30', price='120')]
        with patch('sector_benchmark.fetch_history', return_value=benchmark) as fetch:
            result = compare(self.store, [self.position], 'Technologie', self.today)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual((result['start'], result['end']), ('2026-10-01', '2026-10-30'))
        self.assertEqual([Decimal(result[k]) for k in ('portfolio','benchmark','difference')], [20, 0, 20])
        self.assertEqual(fetch.call_args.args[:3], ('XLK', 'NYSEARCA', 'USD'))

    def test_custom_sector_and_missing_history_do_not_contact_provider(self):
        with patch('sector_benchmark.fetch_history') as fetch:
            self.assertEqual(compare(self.store, [self.position], 'Mijn sector', self.today)['status'], 'unsupported')
            self.assertEqual(compare(self.store, [self.position], 'Technologie', self.today)['status'], 'unavailable')
        fetch.assert_not_called()
