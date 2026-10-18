import sys
import unittest
import json
from pathlib import Path
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from history import daily_values, with_dividends, portfolio_values
from provider import fetch_history

class HistoryTests(unittest.TestCase):
    def test_portfolio_totals_align_start_dates_and_keep_currencies_separate(self):
        def position(symbol,currency,start,price,cost,dividend):
            points=daily_values([dict(purchased_on=start,quantity='1',price=cost)],
                                [dict(day=start,price=price)],[],date(2026,10,14))
            return dict(symbol=symbol,currency=currency,history=with_dividends(points,[dict(paid_on='2026-10-14',amount=dividend)]))
        positions=[position('ASML.AS','EUR','2026-10-12','120','100','5'),
                   position('INGA.AS','EUR','2026-10-13','30','20','2'),
                   position('AAPL','USD','2026-10-12','200','150','10')]
        portfolios={p['currency']:p for p in portfolio_values(positions)}
        eur=portfolios['EUR']['history']
        self.assertEqual(eur[0]['value'],'120')
        self.assertEqual(eur[1]['value'],'150')
        self.assertEqual(eur[-1]['cost'],'120')
        self.assertEqual(eur[-1]['dividend'],'7')
        self.assertEqual(eur[-1]['total_gain'],'37')
        self.assertEqual(eur[-1]['with_dividends'],'157')
        self.assertEqual(portfolios['USD']['history'][-1]['total_gain'],'60')

    def test_portfolio_does_not_present_partial_prices_as_complete(self):
        positions=[]
        for symbol,prices in [('A',[]),('B',[dict(day='2026-10-12',price='120')])]:
            points=daily_values([dict(purchased_on='2026-10-12',quantity='1',price='100')],prices,[],date(2026,10,12))
            positions.append(dict(symbol=symbol,currency='EUR',history=with_dividends(points,[])))
        day=portfolio_values(positions)[0]['history'][0]
        self.assertIsNone(day['value'])
        self.assertIsNone(day['total_gain'])
        self.assertEqual(day['cost'],'200')
    def test_daily_values_from_purchase_including_weekend_and_new_lot(self):
        lots = [dict(purchased_on='2026-10-12', quantity='1', price='999'),
                dict(purchased_on='2026-10-15', quantity='2', price='1100')]
        prices = [dict(day='2026-10-12', price='1000'),dict(day='2026-10-16', price='1200')]
        points = daily_values(lots, prices, [], date(2026,10,18))
        self.assertEqual(len(points), 7)
        self.assertEqual(points[0]['day'], '2026-10-12')
        self.assertEqual(points[0]['value'], '1000')
        self.assertEqual(points[3]['cost'], '3199')
        self.assertEqual(points[-1]['value'], '3600')
        self.assertTrue(points[-1]['carried'])

    def test_missing_data_is_not_invented_and_close_beats_old_intraday_quote(self):
        lots = [dict(purchased_on='2026-10-12', quantity='1', price='999')]
        points = daily_values(lots, [dict(day='2026-10-13', price='1100')],
                              [dict(quoted_at='2026-10-13T12:00:00+00:00', price='1050')], date(2026,10,14))
        self.assertIsNone(points[0]['value'])
        self.assertEqual(points[1]['value'], '1100')
        self.assertEqual(points[2]['value'], '1100')

    def test_weekend_purchase_uses_preceding_close(self):
        points = daily_values([dict(purchased_on='2026-10-17', quantity='1', price='999')],
                              [dict(day='2026-10-16', price='1200')], [], date(2026,10,18))
        self.assertEqual(points[0]['value'], '1200')
        self.assertTrue(points[0]['carried'])

    @patch('provider.urlopen')
    def test_provider_skips_nulls_and_checks_notation(self, request):
        response = request.return_value.__enter__.return_value
        response.read.return_value = json.dumps({'chart': {'result': [{
            'meta': dict(symbol='ASML.AS', exchangeName='AMS', currency='EUR'),
            'timestamp': [1791806400,1791892800],
            'indicators': {'quote': [{'close': [1000, None]}]}
        }]}}).encode()
        rows = fetch_history('ASML.AS','AMSTERDAM','EUR','2026-10-12')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['price'], '1000')
        with self.assertRaises(ValueError):
            fetch_history('ASML.AS','AMSTERDAM','USD','2026-10-12')
