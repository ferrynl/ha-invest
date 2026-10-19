import base64
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from diagnostics import record,read_logs,scrub
from imports import trading212_api as api

class DiagnosticTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name)
 def test_http_error_has_status_reference_and_safe_persistent_provider_details(self):
  self.store.add_account({'name':'Broker','broker':'Trading 212'})
  api.save_connection(self.store,2,'private-key','private-secret','demo')
  error={'code':'INVALID_PERIOD','message':'timeFrom is outside range; private-secret https://reports.s3.amazonaws.com/report?signature=private','apiKey':'private-key'}
  headers={'x-request-id':'request-42','Retry-After':'60'}
  with patch.object(api,'build_opener') as opener:
   opener.return_value.open.side_effect=HTTPError('https://demo.trading212.com/api/v0/equity/history/exports',400,'bad',headers,io.BytesIO(json.dumps(error).encode()))
   with self.assertRaisesRegex(ValueError,r'HTTP 400.*Log-ID') as caught:api.start(self.store,2,'2026-01-01','2026-01-02')
  entries=read_logs(Store(self.temp.name),level='ERROR')['entries'];self.assertEqual(len(entries),1)
  entry=entries[0];self.assertIn(entry['reference'],str(caught.exception));self.assertEqual(entry['details']['http_status'],400)
  self.assertEqual(entry['details']['provider']['code'],'INVALID_PERIOD');self.assertEqual(entry['details']['request_id'],'request-42')
  raw=json.dumps(entries);self.assertNotIn('private-secret',raw);self.assertNotIn('private-key',raw);self.assertNotIn('signature=private',raw)
  self.assertEqual(entry['details']['environment'],'demo');self.assertEqual(entry['details']['account_id'],2)
 def test_nested_secrets_urls_headers_and_known_values_are_redacted(self):
  encoded=base64.b64encode(b'private-key:private-secret').decode()
  from diagnostics import auth_secrets
  result=scrub({'nested':{'api_key':'hidden','secret':'hidden'},'message':'private-key private-secret Basic '+encoded+' https://host.test/file?signed=yes foo@example.com'},auth_secrets('Basic '+encoded))
  text=json.dumps(result)
  for secret in ['private-key','private-secret',encoded,'signed=yes','foo@example.com','hidden']:self.assertNotIn(secret,text)
 def test_portfolio_restore_keeps_local_logs_without_importing_uploaded_logs(self):
  from restore import restore_backup
  local=record(self.store,'INFO','system','local','Lokale log')
  with tempfile.TemporaryDirectory() as folder:
   source=Store(folder);record(source,'ERROR','system','uploaded','Log uit upload')
   restore_backup(self.store,source.backup().read_bytes())
  entries=read_logs(self.store)['entries'];self.assertEqual(len(entries),1);self.assertEqual(entries[0]['reference'],local)
 def test_retention_pagination_filter_and_literal_search(self):
  stamp=datetime.now(timezone.utc).isoformat();expired=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
  with self.store.connect() as db:
   db.executemany('INSERT INTO app_logs(created_at,level,source,event,message,details,reference) VALUES(?,?,?,?,?,?,?)',[(stamp,'INFO','system','test','Test','{}',str(n)) for n in range(5010)])
   db.execute('INSERT INTO app_logs(created_at,level,source,event,message,details,reference) VALUES(?,?,?,?,?,?,?)',(expired,'ERROR','system','old','Expired','{}','expired'))
  reference=record(self.store,'ERROR','trading212','http_error','Test fout',{'http_status':422})
  page=read_logs(self.store);self.assertEqual(len(page['entries']),100)
  older=read_logs(self.store,before=page['next_before']);self.assertLess(older['entries'][0]['id'],page['entries'][-1]['id'])
  self.assertEqual(len(read_logs(self.store,level='ERROR',source='trading212',query=reference)['entries']),1)
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM app_logs').fetchone()[0],5000)
   self.assertEqual(db.execute("SELECT COUNT(*) FROM app_logs WHERE reference='expired'").fetchone()[0],0)
  with self.assertRaises(ValueError):read_logs(self.store,level='DEBUG')
