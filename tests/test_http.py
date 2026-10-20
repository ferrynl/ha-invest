import os
import sys
import json
import tempfile
import threading
import unittest
import http.client
import importlib
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {'DATA_DIR': cls.tmp.name}):
            cls.module = importlib.import_module('server')
        cls.http = cls.module.ThreadingHTTPServer(('127.0.0.1', 0), cls.module.Handler)
        cls.worker = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.worker.join()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            conn.close()

    def test_frontend_and_api(self):
        for path in ['/', '/style.css', '/app.js', '/pages.js', '/chart.js', '/chart-view.js', '/api/state']:
            status, body, headers = self.request('GET', path)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 0)
            self.assertEqual(headers['Cache-Control'], 'no-store' if path in ('/','/api/state') else 'private, max-age=86400, immutable')

    def test_persistent_settings_and_version_information(self):
        headers={'Content-Type':'application/json','X-Portfolio-Request':'1'}
        self.assertEqual(self.request('POST','/api/settings',json.dumps({'default_range':'3M'}),headers)[0],200)
        status,data,_=self.request('GET','/api/state')
        state=json.loads(data)
        self.assertEqual(state['settings']['default_range'],'3M')
        self.assertEqual(state['database_version'],10)
        from version import APP_VERSION
        self.assertEqual(state['app_version'],APP_VERSION)
        self.assertEqual(self.request('POST','/api/settings',json.dumps({'default_range':'bad'}),headers)[0],400)

    def test_purchase_backup_and_reject_cross_site_write(self):
        body = json.dumps(dict(name='Apple', symbol='AAPL', exchange='NASDAQ', quantity='2', price='200', currency='USD', purchased_on=(date.today()-timedelta(days=7)).isoformat()))
        self.assertEqual(self.request('POST', '/api/purchases', body)[0], 403)
        headers = {'Content-Type': 'application/json', 'X-Portfolio-Request': '1'}
        self.assertEqual(self.request('POST', '/api/purchases', body, headers)[0], 201)
        status, data, _ = self.request('GET', '/api/state')
        self.assertEqual(json.loads(data)['positions'][0]['cost'], '400')
        payment=json.dumps(dict(symbol='AAPL',exchange='NASDAQ',currency='USD',amount='3.25',paid_on=(date.today()-timedelta(days=6)).isoformat()))
        self.assertEqual(self.request('POST','/api/dividends',payment,headers)[0],201)
        status,data,_=self.request('GET','/api/state')
        self.assertEqual(json.loads(data)['positions'][0]['dividend'],'3.25')
        self.assertEqual(self.request('POST','/api/dividends',payment)[0],403)
        status, backup, headers = self.request('GET', '/api/backup')
        self.assertEqual(status, 200)
        self.assertTrue(backup.startswith(b'SQLite format 3'))
        self.assertIn('attachment;', headers['Content-Disposition'])
        self.assertEqual(self.request('POST', '/api/purchases', '[]', headers={'Content-Type': 'application/json', 'X-Portfolio-Request': '1'})[0], 400)

    def test_search_validation_and_provider_failure(self):
        self.assertEqual(self.request('GET', '/api/search?q=a')[0], 400)
        self.assertEqual(self.request('GET', '/api/listing?symbol=bad%20symbol')[0],400)
        with patch('web.resolve_listing',return_value={'symbol':'EQGB.L','exchange':'LONDON','currency':'GBX','name':'Example'}):
            status,body,_=self.request('GET','/api/listing?symbol=EQGB.L');self.assertEqual(status,200);self.assertEqual(json.loads(body)['currency'],'GBX')
        with patch('web.search_stocks', return_value=[dict(name='Apple', symbol='AAPL', exchange='NASDAQ', currency='USD')]) as search:
            status, body, _ = self.request('GET', '/api/search?q=ap')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['results'][0]['symbol'], 'AAPL')
            search.assert_called_once_with('ap',store=self.module.store)
        with patch('web.search_stocks', side_effect=TimeoutError):
            self.assertEqual(self.request('GET', '/api/search?q=ap')[0], 502)
