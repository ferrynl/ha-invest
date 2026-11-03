"""Regression checks for Home Invest's passkey security boundary."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from migrations import migrate
from storage import Store
from security import Auth
import passkeys


class PasskeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.auth = Auth(self.store)
        self.auth.enable('tester', 'a-sufficiently-long-password')
        self.session = self.auth.login('tester', 'a-sufficiently-long-password', '127.0.0.1')
        self.user = self.auth.user(self.session)

    def tearDown(self):
        self.tmp.cleanup()

    def test_secure_origin_required(self):
        with self.assertRaises(ValueError):
            passkeys.ceremony_origin('http://example.org')
        with self.assertRaises(ValueError):
            passkeys.ceremony_origin('https://example.org.attacker.test/path')
        self.assertEqual(passkeys.ceremony_origin('https://invest.example.org'),
                         ('https://invest.example.org','invest.example.org'))

    def test_session_required_to_register(self):
        with self.assertRaises(ValueError):
            passkeys.begin_registration(self.store, None, '', 'a-sufficiently-long-password',
                                        'https://invest.example.org')

    def test_wrong_password_rejected(self):
        with self.assertRaises(ValueError):
            passkeys.begin_registration(self.store, self.user, self.session, 'incorrect-password',
                                        'https://invest.example.org')

    def test_challenge_single_use_and_session_bound(self):
        ceremony, _ = passkeys._new_challenge(self.store,'register',
            'https://invest.example.org','invest.example.org',self.user['id'],self.session)
        with self.assertRaises(ValueError):
            passkeys._consume(self.store,ceremony,'register','wrong-session')
        with self.assertRaises(ValueError):
            passkeys._consume(self.store,ceremony,'register',self.session)

    def test_password_login_still_works(self):
        self.assertEqual(self.auth.user(self.session)['username'],'tester')

    def test_passkey_session_issued_only_for_active_user(self):
        token = self.auth.login_by_id(self.user['id'])
        self.assertEqual(self.auth.user(token)['username'],'tester')
        with self.store.connect() as db:
            db.execute('UPDATE users SET active=0 WHERE id=?',(self.user['id'],))
        with self.assertRaises(ValueError):
            self.auth.login_by_id(self.user['id'])

    def test_failed_assertion_does_not_create_session(self):
        begin = passkeys.begin_login(self.store, 'https://invest.example.org')
        with self.assertRaises(ValueError):
            passkeys.finish_login(self.store,self.auth,begin['ceremony_id'],{'id':'dGVzdA'})
        with self.assertRaises(ValueError):
            passkeys.finish_login(self.store,self.auth,begin['ceremony_id'],{'id':'dGVzdA'})

    def test_register_and_login_uses_checked_public_key(self):
        registration = passkeys.begin_registration(
            self.store,self.user,self.session,'a-sufficiently-long-password',
            'https://invest.example.org')
        verified = SimpleNamespace(credential_id=b'credential-id',
                                   credential_public_key=b'server-verified-public-key',
                                   sign_count=0)
        with patch.object(passkeys, 'verify_registration_response', return_value=verified) as check:
            result = passkeys.finish_registration(
                self.store,self.user,self.session,registration['ceremony_id'],
                {'id':'Y3JlZGVudGlhbC1pZA'},'My phone')
            self.assertTrue(result['ok'])
            self.assertEqual(check.call_args.kwargs['expected_origin'],'https://invest.example.org')
            self.assertTrue(check.call_args.kwargs['require_user_verification'])
        begin = passkeys.begin_login(self.store,'https://invest.example.org')
        verified_login = SimpleNamespace(new_sign_count=2)
        with patch.object(passkeys,'verify_authentication_response',return_value=verified_login) as check:
            token=passkeys.finish_login(self.store,self.auth,begin['ceremony_id'],
                                        {'id':'Y3JlZGVudGlhbC1pZA'})
            self.assertEqual(check.call_args.kwargs['credential_public_key'],b'server-verified-public-key')
            self.assertTrue(check.call_args.kwargs['require_user_verification'])
            self.assertEqual(self.auth.user(token)['username'],'tester')
        with self.store.read() as db:
            self.assertEqual(db.execute('SELECT sign_count FROM passkeys').fetchone()[0],2)
        with self.assertRaises(ValueError):
            passkeys.finish_login(self.store,self.auth,begin['ceremony_id'],
                                  {'id':'Y3JlZGVudGlhbC1pZA'})

    def test_migration_tables_present(self):
        with self.store.read() as db:
            self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name='passkeys'").fetchone())
            self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name='passkey_challenges'").fetchone())


if __name__ == '__main__':
    unittest.main()
