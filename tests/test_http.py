import os
import sys
import json
import tempfile
import threading
import unittest
import http.client
import importlib
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
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            conn.close()

    def test_frontend_and_api(self):
        for path in ['/', '/style.css', '/app.js', '/api/state']:
            status, body, headers = self.request('GET', path)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 0)
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_purchase_backup_and_reject_cross_site_write(self):
        body = json.dumps(dict(name='Apple', symbol='AAPL', exchange='NASDAQ', quantity='2', price='200', currency='USD', purchased_on='2025-01-01'))
        self.assertEqual(self.request('POST', '/api/purchases', body)[0], 403)
        headers = {'Content-Type': 'application/json', 'X-Portfolio-Request': '1'}
        self.assertEqual(self.request('POST', '/api/purchases', body, headers)[0], 201)
        status, data, _ = self.request('GET', '/api/state')
        self.assertEqual(json.loads(data)['positions'][0]['cost'], '400')
        status, backup, headers = self.request('GET', '/api/backup')
        self.assertEqual(status, 200)
        self.assertTrue(backup.startswith(b'SQLite format 3'))
        self.assertIn('attachment;', headers['Content-Disposition'])
        self.assertEqual(self.request('POST', '/api/purchases', '[]', headers={'Content-Type': 'application/json', 'X-Portfolio-Request': '1'})[0], 400)
