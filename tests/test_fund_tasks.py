import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio/app'))
import fund_providers as providers
import fund_tasks as tasks
from fund_holdings import save, saved
from instruments import save_categories
from storage import Store

IDENTITY = dict(symbol='EQQQ.DE', exchange='XETRA', currency='EUR')
KEY = tuple(IDENTITY.values())
URL = providers.INVESCO + '/cache/v1/accounts/en_GB/shareclasses/IE0032077012/holdings/fund?idType=isin'
SNAPSHOT = dict(as_of='2026-10-29', holdings=[dict(name='Example', weight='100', sector='Technology', country='US')])


class ProviderTests(unittest.TestCase):
    def test_invesco_keeps_extra_cash_and_missing_classifications(self):
        data = dict(effectiveDate='2026-10-29', numberOfHoldings=1, holdings=[dict(name='Equity', isin=None, weight=99, currency=None), dict(name='Cash', weight=1)])
        with patch.object(providers, 'request', return_value=json.dumps(data)):
            result = providers.retrieve_invesco(URL)
        self.assertEqual(result['coverage'], '100')
        self.assertEqual(len(result['holdings']), 2)
        self.assertEqual(result['holdings'][0]['country'], '')

    def test_vaneck_requires_identity_and_complete_list(self):
        data = dict(Ticker='TDT', IsTopTen=False, TotalAmount=1, AsOfDate='10/30/2026', Holdings=[dict(HoldingName='Equity', Weight='100', Sector='Energy', Country='Netherlands')])
        url = providers.VANECK + '/Main/HoldingsBlock/GetContent/?ticker=TDT'
        with patch.object(providers, 'request', side_effect=lambda _: json.dumps(dict(data=data))):
            self.assertEqual(providers.retrieve_vaneck(url)['holdings'][0]['sector'], 'Energy')
            for fields in (dict(Ticker='OTHER'), dict(IsTopTen=True), dict(TotalAmount=2)):
                original = data.copy();data.update(fields)
                with self.assertRaises(ValueError):providers.retrieve_vaneck(url)
                data = original

    def page(self, weight, cursor=None, total=2, day='2026-10-29'):
        return dict(borHoldings=[dict(holdings=dict(items=[dict(issuerName='Example', marketValuePercentage=weight, ticker=None, effectiveDate=day, bloombergIsoCountry='US', gicsSectorDescription='Technology')], totalHoldings=total, lastItemKey=cursor))])

    def test_vanguard_reads_all_pages_without_scaling(self):
        with patch.object(providers, 'graphql', side_effect=[self.page(60, 'opaque-cursor'), self.page(40)]) as fetch:
            result = providers.retrieve_vanguard('https://www.vanguard.co.uk/professional/product/etf/equity/9679/example')
        self.assertEqual(len(result['holdings']), 2)
        self.assertEqual(result['coverage'], '100')
        self.assertEqual(fetch.call_args_list[1].args[1]['lastItemKey'], 'opaque-cursor')

    def test_vanguard_rejects_cursor_loop_changed_date_and_total(self):
        for second in (self.page(40, 'cursor'), self.page(40, day='2026-10-28'), self.page(40, total=3)):
            with patch.object(providers, 'graphql', side_effect=[self.page(60, 'cursor'), second]):
                with self.assertRaises(ValueError):providers.retrieve_vanguard('https://www.vanguard.co.uk/professional/product/etf/equity/9679/example')

    def test_discovery_isin_wins_over_same_ticker(self):
        entries = [dict(issuer='invesco', isin='IE0032077012', name='One', symbols=['EQQQ'], url=URL), dict(issuer='invesco', isin='IE0000000001', name='Two', symbols=['EQQQ'], url=URL)]
        listing = dict(symbol='EQQQ.DE', name='Invesco ETF', isin='IE0032077012')
        with patch.object(providers, 'catalog', return_value=entries):
            self.assertEqual(providers.discover(None, listing)['isin'], 'IE0032077012')
            listing['isin'] = ''
            with self.assertRaises(ValueError):providers.discover(None, listing)

    def test_unknown_issuer_still_searches_other_catalogues_after_outage(self):
        entry = dict(issuer='vaneck', isin='NL0009272749', name='VanEck AEX ETF', symbols=['TDT'], url=URL)
        def catalogue(_, name):
            if name == 'invesco':raise OSError('offline')
            return [entry] if name == 'vaneck' else []
        with patch.object(providers, 'catalog', side_effect=catalogue):
            self.assertEqual(providers.discover(None, dict(symbol='TDT', name='ETF', isin=entry['isin']))['issuer'], 'vaneck')

    def test_catalogue_outage_is_retryable_and_not_an_unsupported_fund(self):
        with patch.object(providers, 'catalog', side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'tijdelijk'):
                providers.discover(None, dict(symbol='EXAMPLE', name='ETF'))

    def test_saved_issuer_urls_use_new_adapters(self):
        import fund_holdings
        cases = [(URL,'retrieve_invesco'), (providers.VANECK+'/Main/HoldingsBlock/GetContent/?ticker=TDT','retrieve_vaneck'), ('https://www.vanguard.co.uk/professional/product/etf/equity/9679/example','retrieve_vanguard')]
        for url, method in cases:
            with patch.object(providers, method, return_value=SNAPSHOT) as fetch:
                self.assertEqual(fund_holdings.retrieve(url), SNAPSHOT);fetch.assert_called_once_with(url)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name);self.cache = Mock()
        self.store.add(dict(**IDENTITY, name='Invesco EQQQ ETF', quantity='2', price='50', purchased_on='2026-10-01'))
        save_categories(self.store, dict(**IDENTITY, asset_type='ETF'))
        self.addCleanup(lambda:tasks._jobs.pop(tasks.key(self.store), None))

    def start(self, mode='all'):
        with patch.object(tasks.threading, 'Thread') as thread:
            state = tasks.start(self.store, self.cache, mode)
        return state, thread

    def test_read_never_fetches_and_duplicate_start_keeps_single_queue(self):
        with patch.object(tasks, 'discover') as discovery, patch.object(tasks, 'refresh') as refresh:
            self.assertEqual(len(tasks.status(self.store)['rows']), 1)
            state, thread = self.start()
            again, other = self.start()
            self.assertEqual(state, again);other.assert_not_called()
            discovery.assert_not_called();refresh.assert_not_called()
            thread.return_value.start.assert_called_once()

    def test_success_updates_composition_and_cache(self):
        self.start();job=tasks._jobs[tasks.key(self.store)]
        with patch.object(tasks, 'discover', return_value=dict(url=URL, issuer='invesco', isin='IE0032077012')), patch('fund_holdings.retrieve', return_value=SNAPSHOT):
            tasks.run(self.store, self.cache, job)
        state=tasks.status(self.store)
        self.assertFalse(state['running']);self.assertEqual(state['rows'][0]['status'], 'success')
        self.assertEqual(saved(self.store, KEY)['holdings'][0]['name'], 'Example')
        self.cache.invalidate.assert_called_once()

    def test_cancel_before_work_does_not_fetch(self):
        self.start();tasks.cancel(self.store)
        with patch.object(tasks, 'discover') as discovery:
            tasks.run(self.store, self.cache, tasks._jobs[tasks.key(self.store)])
            discovery.assert_not_called()
        self.assertEqual(tasks.status(self.store)['rows'][0]['status'], 'cancelled')

    def test_cancel_after_discovery_does_not_fetch_holdings(self):
        self.start()
        def discover(*_):
            tasks.cancel(self.store)
            return dict(url=URL, issuer='invesco', isin='IE0032077012')
        with patch.object(tasks, 'discover', side_effect=discover), patch.object(tasks, 'refresh') as refresh:
            tasks.run(self.store, self.cache, tasks._jobs[tasks.key(self.store)])
            refresh.assert_not_called()

    def test_failure_preserves_previous_composition(self):
        save(self.store, KEY, SNAPSHOT, URL);self.start()
        with patch.object(tasks, 'refresh', side_effect=OSError('secret upstream body')):
            tasks.run(self.store, self.cache, tasks._jobs[tasks.key(self.store)])
        row=tasks.status(self.store)['rows'][0]
        self.assertEqual(row['status'], 'error');self.assertNotIn('secret', row['message'])
        self.assertEqual(saved(self.store, KEY)['holdings'][0]['name'], 'Example')

    def test_restart_only_restores_current_listings_and_never_executes(self):
        self.start();tasks._jobs.clear()
        with self.store.connect() as db:
            payload=json.loads(db.execute("SELECT payload FROM api_cache WHERE namespace='fund-task-status'").fetchone()[0])
            payload['rows'].append(dict(symbol='EVIL', exchange='X', currency='USD', status='running', source_url='https://localhost'))
            db.execute("UPDATE api_cache SET payload=? WHERE namespace='fund-task-status'", (json.dumps(payload),))
        with patch.object(tasks, 'discover') as discovery:
            state=tasks.status(self.store);discovery.assert_not_called()
        self.assertEqual(state['phase'], 'interrupted');self.assertFalse(state['running'])
        self.assertEqual(len(state['rows']), 1);self.assertEqual(state['rows'][0]['source_url'], '')
        self.assertEqual(state['rows'][0]['status'], 'interrupted')

    def test_missing_mode_keeps_fresh_composition(self):
        from datetime import date
        save(self.store, KEY, dict(SNAPSHOT, as_of=date.today().isoformat()), URL)
        state,_=self.start('missing');self.assertEqual(state['rows'][0]['status'], 'skipped')
        with self.assertRaises(ValueError):tasks.start(self.store, self.cache, 'invalid')


import test_transactions as support

class TaskHttpTests(unittest.TestCase):
    setUp = support.TransactionHttpTests.setUp
    tearDown = support.TransactionHttpTests.tearDown
    request = support.TransactionHttpTests.request

    def test_admin_get_does_not_start_network_and_invalid_action_rejected(self):
        with patch.object(tasks, 'discover') as discovery:
            self.assertEqual(self.request('/api/tasks/etf')[0], 200);discovery.assert_not_called()
        self.assertEqual(self.request('/api/tasks/etf', dict(action='delete'))[0], 400)

    def test_admin_role_and_csrf_are_required(self):
        self.auth.enable('owner', 'Long-test-password-2026')
        self.assertEqual(self.request('/api/tasks/etf')[0], 401)
        token=self.auth.login('owner','Long-test-password-2026','test')
        self.assertEqual(self.request('/api/tasks/etf', dict(mode='all'), token)[0], 403)
        with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
        token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
        self.assertEqual(self.request('/api/tasks/etf', None, token)[0], 403)
        self.assertEqual(self.request('/api/tasks/etf', dict(mode='all'), token, csrf)[0], 403)
