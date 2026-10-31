import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
import feedback
from storage import Store

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        feedback._retry_after = 0

    def response(self, rows):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(rows).encode()
        return response

    def test_normalizes_and_caches_without_credentials(self):
        rows = [{'number':1,'title':'[Bug] <script>alert(1)</script>','state':'open','html_url':'https://evil.invalid','labels':[]},
                {'number':2,'title':'Feature','state':'closed','labels':[{'name':'enhancement'}]},
                {'number':3,'title':'PR','pull_request':{}},
                {'number':4,'title':'[Wens] test','labels':[]},
                {'number':'bad','title':'invalid'}]
        with patch('feedback.urlopen',return_value=self.response(rows)) as request:
            result = feedback.overview(self.store)
            self.assertEqual(result,feedback.overview(self.store))
            request.assert_called_once()
            req = request.call_args.args[0]
            self.assertEqual(req.full_url,feedback.API)
            self.assertFalse(req.has_header('Authorization'))
            self.assertIsNone(req.data)
        self.assertEqual([r['kind'] for r in result['issues']],['bug','wish','wish'])
        self.assertEqual(result['issues'][0]['url'],feedback.REPOSITORY+'/issues/1')
        self.assertNotIn('body',result['issues'][0])
        self.assertEqual(result['issues'][1]['state'],'closed')

    def test_failure_is_generic_and_backed_off(self):
        with patch('feedback.urlopen',side_effect=RuntimeError('secret provider response')) as request:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'GitHub is tijdelijk') as error:
                    feedback.overview(self.store)
                self.assertNotIn('secret',str(error.exception))
            request.assert_called_once()

    def test_oversize_response_is_rejected(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value=b' '*2000001
        with patch('feedback.urlopen',return_value=response):
            with self.assertRaises(ValueError):feedback.overview(self.store)

if __name__=='__main__':unittest.main()
