import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from datetime import date,datetime,timedelta,timezone
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

    def test_long_ranges_include_leap_days_without_gaps_and_never_exceed_a_year(self):
        end=datetime(2026,10,19,18,40,47,tzinfo=timezone.utc)
        parts=api.report_periods(date(2010,1,1),end)
        self.assertGreater(len(parts),16)
        self.assertEqual(datetime.fromisoformat(parts[0]['start']),datetime(2010,1,1,tzinfo=timezone.utc))
        self.assertEqual(datetime.fromisoformat(parts[-1]['end']),end)
        for index,part in enumerate(parts):
            self.assertLessEqual(datetime.fromisoformat(part['end'])-datetime.fromisoformat(part['start']),timedelta(days=364))
            if index:self.assertEqual(parts[index-1]['end'],part['start'])

    def test_multiple_reports_resume_and_only_create_one_complete_preview(self):
        first=CSV.replace('2026-01-01','2024-01-01')
        second=CSV.replace('Market buy','Market sell').replace('2026-01-01','2025-01-01').replace(',2,100,EUR,123',',1,150,EUR,456')
        report=lambda number:dict(reportId=number,status='Finished',downloadLink='https://reports.s3.amazonaws.com/'+str(number))
        with patch.object(api,'request',side_effect=[{'reportId':101},[report(101)],first,{'reportId':102},[report(102)],second]) as network:
            with patch('time.time',return_value=1800001000):result=api.start(self.store,2,'2024-01-01','2025-01-02')
            self.assertEqual(result['total'],2)
            with patch('time.time',return_value=1800001100):result=api.poll(self.store,2)
            self.assertTrue(result['pending']);self.assertEqual(result['completed'],1)
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM import_batches').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],0)
            restarted=Store(self.temp.name)
            with patch('time.time',return_value=1800001200):result=api.poll(restarted,2)
            self.assertFalse(result['pending']);self.assertEqual(len(result['preview']['rows']),2)
            self.assertEqual(network.call_count,6)
            for call in (network.call_args_list[0],network.call_args_list[3]):
                payload=call.args[2]
                self.assertLessEqual(datetime.fromisoformat(payload['timeTo'])-datetime.fromisoformat(payload['timeFrom']),timedelta(days=364))
        mapping={'ASML|EUR':dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')}
        self.assertEqual(commit(restarted,result['preview']['batch_id'],mapping)['imported'],2)
        self.assertEqual(restarted.state()['positions'][0]['quantity'],'1')
        self.assertFalse(api.connection_status(restarted,2)['pending'])

    def test_failed_part_submission_can_resume_without_losing_completed_reports(self):
        report=dict(reportId=101,status='Finished',downloadLink='https://reports.s3.amazonaws.com/101')
        with patch('time.time',return_value=1800001000),patch.object(api,'request',return_value={'reportId':101}):api.start(self.store,2,'2024-01-01','2025-01-02')
        with patch('time.time',return_value=1800001100),patch.object(api,'request',side_effect=[[report],CSV,ValueError('offline')]):
            with self.assertRaises(ValueError):api.poll(self.store,2)
        value=api.read_connection(self.store,2);self.assertEqual(value['plan']['completed'],[101]);self.assertNotIn('job',value)
        with patch('time.time',return_value=1800001200),patch.object(api,'request',return_value={'reportId':102}) as network:
            result=api.poll(Store(self.temp.name),2);self.assertEqual(result['completed'],1);self.assertEqual(network.call_count,1)
        api.cancel(self.store,2);self.assertFalse(api.connection_status(self.store,2)['pending'])

    def test_legacy_single_report_pending_before_upgrade_still_completes(self):
        value=api.read_connection(self.store,2);value['job']=88;api.persist(self.store,2,value)
        with patch.object(api,'request',side_effect=[[dict(reportId=88,status='Finished',downloadLink='https://reports.s3.amazonaws.com/88')],CSV]):
            self.assertIn('preview',api.poll(self.store,2))

    def test_empty_report_period_finishes_without_importing_transactions(self):
        with patch.object(api,'request',side_effect=[{'reportId':1},[dict(reportId=1,status='Finished',downloadLink='https://reports.s3.amazonaws.com/1')],CSV.splitlines()[0]+'\n']):
            api.start(self.store,2,'2026-01-01','2026-01-02');result=api.poll(self.store,2)
            self.assertFalse(result['pending']);self.assertNotIn('preview',result)
            self.assertFalse(api.connection_status(self.store,2)['pending'])

    def test_resume_cached_api_csv_with_exact_time_utc_header_without_network(self):
        import csv,io
        from persistent_cache import cached_json
        fields=['Action','Time (UTC)','ISIN','Ticker','Name','ID','No. of shares','Price / share','Currency (Price / share)','Exchange rate','Total','Currency (Total)','Withholding tax','Currency (Withholding tax)','Stamp duty reserve tax','Currency (Stamp duty reserve tax)']
        output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
        writer.writerow({'Action':'Market buy','Time (UTC)':'2026-10-12 10:00:00','ISIN':'NL0010273215','Ticker':'ASML','Name':'ASML','ID':'api-123','No. of shares':'1','Price / share':'100','Currency (Price / share)':'EUR','Total':'100','Currency (Total)':'EUR'})
        value=api.read_connection(self.store,2)
        value['plan']={'parts':[{'start':'2026-10-01T00:00:00+00:00','end':'2026-10-19T00:00:00+00:00'}],'completed':[123],'dividends':True}
        api.persist(self.store,2,value)
        cached_json(self.store,'trading212',value['identity']+':csv:123',86400,lambda:output.getvalue())
        with patch.object(api,'request') as network:result=api.poll(Store(self.temp.name),2);network.assert_not_called()
        row=result['preview']['rows'][0];self.assertIsNone(row['error']);self.assertEqual(row['day'],'2026-10-12')
        self.assertEqual(row['raw']['Time (UTC)'],'2026-10-12 10:00:00')
        self.assertEqual(row['raw']['ISIN'],'NL0010273215')
        self.assertFalse(api.connection_status(self.store,2)['pending'])

    def test_combine_mixed_time_headers_and_optional_tax_columns(self):
        from persistent_cache import cached_json
        first=CSV.replace('2026-01-01','2024-01-01')
        second=CSV.replace('Action,Time,','Action,Time (UTC),').replace('2026-01-01','2025-01-01').replace(',ID\n',',ID,Withholding tax\n').replace(',123\n',',456,0\n')
        value=api.read_connection(self.store,2)
        value['plan']={'parts':[{},{}],'completed':[1,2],'dividends':True}
        api.persist(self.store,2,value)
        for index,text in enumerate([first,second],1):cached_json(self.store,'trading212',value['identity']+':csv:'+str(index),86400,lambda:text)
        with patch.object(api,'request') as network:result=api.poll(self.store,2);network.assert_not_called()
        rows=result['preview']['rows'];self.assertEqual(len(rows),2);self.assertTrue(all(r['error'] is None for r in rows))
        self.assertEqual(rows[1]['raw']['Withholding tax'],'0');self.assertEqual(rows[0]['raw']['Withholding tax'],'')

if __name__=='__main__':unittest.main()
