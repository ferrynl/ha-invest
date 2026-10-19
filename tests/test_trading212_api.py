import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports import trading212_api as api
from imports.service import commit,preview

CSV='Action,Time,Ticker,Name,No. of shares,Price / share,Currency (Price / share),ID\nMarket buy,2026-01-01 10:00:00,ASML,ASML,2,100,EUR,123\n'

class Trading212Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name);self.store.add_account({'name':'Broker','broker':'Trading 212'})
        self.account=2
        api.save_connection(self.store,2,'test-key','test-secret','demo')

    def test_encrypted_connection_survives_restart_and_never_enters_database(self):
        restarted=Store(self.temp.name)
        self.assertEqual(api.connection_status(restarted,2),dict(saved=True,environment='demo',pending=False))
        encrypted=(Path(self.temp.name)/'connections/2.encrypted').read_bytes()
        self.assertNotIn(b'test-secret',encrypted)
        self.assertNotIn(b'test-key',encrypted)
        self.assertNotIn(b'test-secret',restarted.path.read_bytes())
        self.assertEqual(api.read_connection(restarted,2)['secret'],'test-secret')
        api.forget(restarted,2);self.assertFalse(api.connection_status(restarted,2)['saved'])
        with self.assertRaises(ValueError):api.save_connection(self.store,1,'x','y','live')

    def test_api_report_preview_and_csv_deduplicate(self):
        mapping={'ASML|EUR':dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')}
        old=preview(self.store,2,'trading212','old.csv',CSV);commit(self.store,old['batch_id'],mapping)
        with patch.object(api,'request',side_effect=[{'reportId':42},[dict(reportId=42,status='Finished',downloadLink='https://reports.s3.eu-central-1.amazonaws.com/report?signature=test')],CSV]) as network:
            api.start(self.store,2,'2026-01-01','2026-01-02')
            result=api.poll(self.store,2)
            self.assertTrue(result['preview']['rows'][0]['duplicate'])
            self.assertEqual(commit(self.store,result['preview']['batch_id'],mapping)['imported'],0)
            self.assertEqual(network.call_count,3)
            self.assertIn('Basic ',network.call_args_list[0].args[1])
            self.assertEqual(network.call_args_list[2].kwargs,{'csv':True})
        with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM api_cache WHERE namespace='trading212'").fetchone()[0],3)

    def test_queued_polls_are_cached_and_job_survives_restart(self):
        with patch.object(api,'request',side_effect=[{'reportId':99},[dict(reportId=99,status='Queued')]]) as network:
            api.start(self.store,2,'2026-01-01','2026-01-02')
            for _ in range(3):self.assertTrue(api.poll(Store(self.temp.name),2)['pending'])
            self.assertEqual(network.call_count,2)
            with self.assertRaises(ValueError):api.start(self.store,2,'2026-01-01','2026-01-02')

    def test_no_redirects_or_untrusted_downloads(self):
        for url in ['http://reports.s3.amazonaws.com/x','https://127.0.0.1/x','https://evil.test/x','https://trading212.com.evil.test/x','https://user@reports.s3.amazonaws.com/x','https://reports.s3.amazonaws.com:8080/x']:
            with self.subTest(url=url),self.assertRaises(ValueError):api.download_url(url)
        self.assertIsNone(api.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test'))

    def test_provider_errors_hide_credentials_and_rate_limit_failed_polls(self):
        with patch.object(api,'build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://secret-url',401,'contains secret',{},None)
            with self.assertRaisesRegex(ValueError,'API-sleutel of secret onjuist'):api.request('https://demo.trading212.com','Basic private')
        with patch.object(api,'request',return_value={'reportId':5}):api.start(self.store,2,'2026-01-01','2026-01-02')
        with patch.object(api,'request',side_effect=ValueError('offline')) as network:
            with self.assertRaises(ValueError):api.poll(self.store,2)
            with self.assertRaisesRegex(ValueError,'Wacht een minuut'):api.poll(self.store,2)
            self.assertEqual(network.call_count,1)

    def test_restore_keeps_local_connection_and_rejects_different_owner(self):
        from restore import restore_backup
        backup=self.store.backup().read_bytes()
        restore_backup(self.store,backup)
        self.assertTrue(api.connection_status(self.store,2)['saved'])
        with self.store.connect() as db:db.execute("UPDATE broker_accounts SET created_at='2026-01-01T00:00:00Z' WHERE id=2")
        with self.assertRaises(ValueError):api.read_connection(self.store,2)

if __name__=='__main__':unittest.main()
