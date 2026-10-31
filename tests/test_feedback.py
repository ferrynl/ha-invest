import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,MagicMock
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from feedback_service.github import GitHub,GitHubFailure

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.github=GitHub.__new__(GitHub)
        self.github.access_token=Mock(return_value='scoped-test-token')

    def test_board_normalizes_plain_text_and_excludes_pull_requests(self):
        rows=[{'number':1,'title':'[Bug] <script>alert(1)</script>','state':'open','html_url':'https://evil.invalid','body':'not exposed','labels':[]},
              {'number':2,'title':'Feature','state':'closed','labels':[{'name':'enhancement'}]},
              {'number':3,'title':'PR','pull_request':{}},
              {'number':4,'title':'[Wens] test','labels':[]},
              {'number':'bad','title':'invalid'}]
        self.github.request=Mock(return_value=(rows,'etag'))
        board,etag=self.github.board()
        self.assertEqual([r['kind'] for r in board['issues']],['bug','wish','wish'])
        self.assertEqual(board['issues'][1]['state'],'closed')
        self.assertNotIn('body',board['issues'][0])
        self.assertNotIn('url',board['issues'][0])
        self.assertEqual(etag,'etag')
        self.github.request.assert_called_once_with('/repos/ferrynl/ha-invest/issues?state=all&sort=updated&direction=desc&per_page=100','scoped-test-token',etag=None)

    def test_conditional_board_keeps_existing_snapshot(self):
        self.github.request=Mock(return_value=(None,'etag'))
        self.assertEqual(self.github.board('etag'),(None,'etag'))

    def test_oversize_response_and_redirect_are_rejected(self):
        self.github.opener=Mock()
        response=MagicMock();response.__enter__.return_value.read.return_value=b' '*2000001
        self.github.opener.open.return_value=response
        with self.assertRaises(GitHubFailure):self.github.request('/repos/ferrynl/ha-invest/issues','test')
        self.github.opener.open.side_effect=HTTPError('https://api.github.com',302,'redirect',{},None)
        with self.assertRaises(GitHubFailure) as error:self.github.request('/repos/ferrynl/ha-invest/issues','test')
        self.assertEqual(error.exception.status,302)

if __name__=='__main__':unittest.main()
