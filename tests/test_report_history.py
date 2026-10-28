import sys
import unittest
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from reports import history


class ReportHistoryTests(unittest.TestCase):
    def setUp(self):
        self.position = dict(account_id=1, symbol='AAA', exchange='AMS', currency='EUR',
                             history=[dict(day='2026-01-01', value='0.10', cost='0.05', dividend='0.02'),
                                      dict(day='2026-01-02', value=None, cost='0.05', dividend='0.02')])
        self.snapshot = dict(accounts=[{'id': 1}, {'id': 2}], data_revision=5, positions=[
            self.position,
            {**deepcopy(self.position), 'account_id': 2},
            {**deepcopy(self.position), 'currency': 'USD'}])

    def test_account_instrument_and_currency_are_scoped(self):
        result = history(self.snapshot, '1', ['AAA', 'AMS', 'EUR'], 'EUR')
        self.assertEqual(result['data_revision'], 5)
        self.assertEqual(len(result['currencies']), 1)
        self.assertEqual(result['currencies'][0]['history'][0]['value'], '0.10')
        self.assertEqual(result['currencies'][0]['omitted_days'], 1)
        self.assertEqual(result['currencies'][0]['omitted_dates'], ['2026-01-02'])
        self.assertEqual(result['currencies'][0]['as_of'], '2026-01-02')
        self.assertEqual(history(self.snapshot, '2', currency='USD')['currencies'], [])

    def test_missing_positions_excluded_from_all_daily_totals(self):
        self.snapshot['positions'][1]['history'][0]['value'] = None
        result = history(self.snapshot, currency='EUR')['currencies'][0]
        point = result['history'][0]
        self.assertEqual((point['value'], point['cost'], point['dividend']), ('0.10', '0.05', '0.02'))
        self.assertEqual((point['count'], point['skipped']), (1, 1))

    def test_decimal_precision_currencies_and_zero_are_preserved(self):
        result = history(self.snapshot)['currencies']
        self.assertEqual([p['currency'] for p in result], ['EUR', 'USD'])
        self.assertEqual(result[0]['history'][0]['value'], '0.20')
        self.position['history'][1]['value'] = '0'
        self.assertEqual(len(history(self.snapshot, '1', currency='EUR')['currencies'][0]['history']), 2)

    def test_invalid_amounts_and_unknown_accounts(self):
        for value in ('NaN', 'Infinity', '', None):
            self.position['history'][0]['value'] = value
            self.assertEqual(history(self.snapshot, '1', currency='EUR')['currencies'][0]['history'], [])
        for account in ('999', 'invalid'):
            with self.assertRaises(ValueError):
                history(self.snapshot, account)
        for instrument in ('AAA', [], [1, 2, 3]):
            with self.assertRaises(ValueError):
                history(self.snapshot, instrument=instrument)

    def test_report_does_not_mutate_saved_snapshot(self):
        before = deepcopy(self.snapshot)
        history(self.snapshot)
        self.assertEqual(self.snapshot, before)
