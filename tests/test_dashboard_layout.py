import json
import unittest
import test_security_restore_cache as support
from dashboard_layout import defaults, read, save, validate
from storage import Store
from restore import restore_backup


class DashboardLayoutTests(unittest.TestCase):
    setUp = support.AccessTests.setUp
    tearDown = support.AccessTests.tearDown
    request = support.AccessTests.request
    activate = support.AccessTests.activate

    def test_independent_users_profiles_restart_and_no_shared_state_leak(self):
        user = {'id': 1}
        rows = defaults()[::-1]
        rows[0]['enabled'] = False
        rows[1]['width'] = 'half'
        save(self.store, user, 'personal', {'modules': rows})
        self.assertEqual(read(Store(self.store.root), user, 'personal')['modules'], rows)
        self.assertEqual(read(self.store, {'id': 2}, 'personal')['modules'], defaults())
        self.assertEqual(read(self.store, user, 'demo')['modules'], defaults())
        self.assertEqual(read(self.store, {'id': None}, 'personal')['modules'], defaults())
        self.assertFalse(any(key.startswith('dashboard_layout:') for key in self.store.state()['settings']))
        self.assertEqual(read(self.store, user, 'personal')['modules'][0]['id'], 'holdings')

    def test_validation_and_future_modules(self):
        for data in [None, {}, {'modules': 'wrong'}, {'modules': [defaults()[0]] * 2},
                     {'modules': [{'id': 'unknown', 'enabled': True, 'width': 'full'}]},
                     {'modules': [{'id': 'chart', 'enabled': 'false', 'width': 'full'}]},
                     {'modules': [{'id': 'chart', 'enabled': True, 'width': '2000px'}]},
                     {'modules': [{'id': 'chart', 'enabled': True, 'width': 'full', 'html': '<script>'}]}]:
            with self.assertRaises(ValueError):
                validate(data)
        self.assertEqual(len(validate({'modules': [defaults()[-1]]})), len(defaults()))
        with self.assertRaises(ValueError):
            save(self.store, {'id': 1}, '../../user', {'modules': defaults()})
        self.assertEqual(read(self.store, {'id': 1}, 'personal')['modules'], defaults())

    def test_authenticated_basic_csrf_and_demo_preferences_use_primary_store(self):
        admin, csrf = self.activate()
        self.auth.save_user({'username': 'layoutviewer', 'password': self.password, 'role': 'basic'})
        basic = self.auth.login('layoutviewer', self.password, 'test')
        basic_csrf = self.auth.user(basic)['csrf']
        path = '/api/account/dashboard'
        rows = defaults()[::-1]
        rows[0]['enabled'] = False
        self.assertEqual(self.request('GET', path)[0], 401)
        self.assertEqual(self.request('POST', path, {'modules': rows}, basic)[0], 403)
        self.assertEqual(self.request('POST', path, {'modules': rows}, basic, basic_csrf)[0], 200)
        status, body, headers = self.request('GET', path, token=basic)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(json.loads(body)['modules'], rows)
        self.assertEqual(json.loads(self.request('GET', path, token=admin)[1])['modules'], defaults())
        demo = {'X-HomeInvest-Profile': 'demo'}
        self.assertEqual(self.request('POST', path, {'modules': rows}, basic, basic_csrf, extra=demo)[0], 200)
        self.assertEqual(json.loads(self.request('GET', path, token=basic, extra=demo)[1])['modules'], rows)
        self.assertFalse((self.store.root / 'demo').exists(), 'Layout changes must not create or modify a demo ledger')
        self.assertEqual(self.request('POST', '/api/purchases', {}, basic, basic_csrf, extra=demo)[0], 403)

    def test_restore_keeps_current_account_layout_and_ignores_uploaded_preferences(self):
        user = {'id': None}
        original = defaults()
        save(self.store, user, 'personal', {'modules': original})
        backup = self.store.backup().read_bytes()
        changed = defaults()[::-1]
        changed[0]['enabled'] = False
        save(self.store, user, 'personal', {'modules': changed})
        restore_backup(self.store, backup)
        self.assertEqual(read(self.store, user, 'personal')['modules'], changed)


if __name__ == '__main__':
    unittest.main()
