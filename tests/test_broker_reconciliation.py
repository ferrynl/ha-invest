"""Reconcile a large broker export against the booked ledger and a replay."""
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from imports.partial import commit_partial
from imports.registry import remember
from imports.service import preview
from storage import Store


class BrokerReconciliationTests(unittest.TestCase):
    def test_large_trading212_export_reconciles_and_replays_without_double_booking(self):
        header = (
            'Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,'
            'Currency (Price / share),Total,Currency (Total)\n'
        )
        buys = [
            f'Market buy,2025-01-02 10:00:00,NL0010273215,ASML,ASML,buy-{i},'
            '0.25,120,EUR,30,EUR\n'
            for i in range(100)
        ]
        dividends = [
            f'Dividend (Ordinary),2025-02-03 10:00:00,NL0010273215,ASML,ASML,dividend-{i},'
            ',,,0.07,EUR\n'
            for i in range(9900)
        ]
        export = header + ''.join(buys + dividends)

        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            store.add_account(dict(name='Broker', broker='Trading 212'))
            batch = preview(store, 2, 'trading212', 'history.csv', export)
            self.assertEqual(len(batch['rows']), 10_000)
            remember(
                store, 2, 'trading212', batch['rows'][0],
                dict(symbol='ASML.AS', exchange='AMSTERDAM', currency='EUR', name='ASML'),
            )
            imported = commit_partial(store, batch['batch_id'])
            self.assertEqual((imported['imported'], imported['pending']), (10_000, 0))
            self.assertEqual(imported['standalone_dividends'], 0)

            # Reopen the store to verify deduplication uses persistent source IDs.
            store = Store(directory)
            replay = preview(store, 2, 'trading212', 'history-replayed.csv', export)
            self.assertTrue(all(row.get('duplicate') for row in replay['rows']))
            repeated = commit_partial(store, replay['batch_id'])
            self.assertEqual((repeated['imported'], repeated['pending']), (0, 0))
            self.assertEqual(repeated['duplicates'], 10_000)

            with store.connect() as db:
                trades = db.execute(
                    'SELECT account_id, currency, side, quantity, price FROM purchases'
                ).fetchall()
                income = db.execute('SELECT account_id, currency, amount FROM dividends').fetchall()
                sources = db.execute(
                    'SELECT account_id, provider, external_id FROM import_records'
                ).fetchall()

            self.assertEqual(len(trades), 100)
            self.assertEqual({(row[0], row[1], row[2]) for row in trades}, {(2, 'EUR', 'BUY')})
            self.assertEqual(sum(Decimal(row[3]) for row in trades), Decimal('25'))
            self.assertEqual(
                sum(Decimal(row[3]) * Decimal(row[4]) for row in trades), Decimal('3000')
            )
            self.assertEqual(len(income), 9900)
            self.assertEqual({(row[0], row[1]) for row in income}, {(2, 'EUR')})
            self.assertEqual(sum(Decimal(row[2]) for row in income), Decimal('693'))
            self.assertEqual(len(sources), 10_000)
            self.assertEqual({(row[0], row[1]) for row in sources}, {(2, 'trading212')})
            self.assertEqual(len({row[2] for row in sources}), 10_000)
