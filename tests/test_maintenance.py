import sys,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from cache import StateCache
from maintenance import preview,clean,backups

class MaintenanceTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(tmp.name);self.cache=StateCache(store=self.store)
  self.store.add(dict(symbol='TEST',exchange='TEST',currency='EUR',name='Test',quantity='2',price='100',purchased_on='2026-01-02'))
  for stamp,price in [('2026-01-02T10:00:00+00:00','105'),('2026-01-02T11:00:00+00:00','110'),('2026-01-03T11:00:00+00:00','115')]:self.store.quote('TEST','TEST','EUR',price,stamp,'test')
  self.store.add_dividend(dict(symbol='TEST',exchange='TEST',currency='EUR',amount='3',paid_on='2026-01-03'))
  with self.store.connect() as db:
   db.execute("INSERT INTO api_cache VALUES('provider','expired','{}',0,1)")
   db.execute("INSERT INTO api_cache VALUES('provider','fresh','{}',0,9999999999)")
   db.execute("INSERT INTO api_cache VALUES('fund-task-status','latest','{}',0,1)")
   db.execute("INSERT INTO api_cache VALUES('provider-cooldown','yahoo','{}',0,1)")
 def request(self,options=None):
  plan=preview(self.store,options or {})
  return dict(options=plan['options'],review=plan['review'],confirmation='OPSCHONEN')
 def test_preview_never_mutates_and_cleanup_preserves_finances_and_daily_valuations(self):
  before=self.store.state();files=backups(self.store);plan=preview(self.store,{})
  self.assertEqual(plan['quote_count'],1);self.assertEqual(plan['cache_count'],1);self.assertEqual(backups(self.store),files)
  result=clean(self.store,self.cache,self.request())
  after=self.store.state();self.assertEqual(before['purchases'],after['purchases']);self.assertEqual(before['dividends'],after['dividends']);self.assertEqual(before['positions'],after['positions']);self.assertEqual(before['portfolios'],after['portfolios'])
  self.assertTrue((self.store.root/'backups'/result['backup_name']).is_file());self.assertTrue(result['compacted'])
  with self.store.read() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM quotes').fetchone()[0],2)
   keys=[tuple(r) for r in db.execute('SELECT namespace,cache_key FROM api_cache')]
  self.assertNotIn(('provider','expired'),keys);self.assertIn(('provider','fresh'),keys);self.assertIn(('fund-task-status','latest'),keys);self.assertIn(('provider-cooldown','yahoo'),keys)
 def test_five_newest_backups_include_recovery_copy_and_future_backups_keep_policy(self):
  for i in range(7):self.store.backup(retain=False)
  original=backups(self.store);plan=preview(self.store,{})
  self.assertEqual(plan['backup_count'],3)
  result=clean(self.store,self.cache,self.request())
  self.assertEqual(len(backups(self.store)),5);self.assertTrue(all(p.exists() for p in original[-4:]))
  self.assertEqual(result['backup_count'],3);self.store.backup();self.assertEqual(len(backups(self.store)),5)
 def test_changed_quote_rejects_old_review_before_making_backup(self):
  request=self.request();self.store.quote('TEST','TEST','EUR','120','2026-01-04T10:00:00+00:00','test')
  with self.assertRaisesRegex(ValueError,'gewijzigd'):clean(self.store,self.cache,request)
  self.assertEqual(backups(self.store),[])
 def test_backup_failure_prevents_cleanup(self):
  request=self.request()
  with patch.object(self.store,'backup',side_effect=OSError('failure')):
   with self.assertRaises(OSError):clean(self.store,self.cache,request)
  with self.store.read() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM quotes').fetchone()[0],3)
 def test_preserving_backups_does_not_enable_retention_or_delete_files(self):
  self.store.backup(retain=False);before=backups(self.store)
  clean(self.store,self.cache,self.request(dict(backups=False,compact=False)))
  self.assertTrue(before[0].exists());self.assertEqual(len(backups(self.store)),2);self.assertNotIn('backup_retention',self.store.settings())

import test_transactions as support
class MaintenanceHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_admin_csrf_review_and_execution_are_enforced(self):
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
  self.assertEqual(self.request('/api/portfolio/cleanup-preview',{})[0],401)
  self.assertEqual(self.request('/api/portfolio/cleanup-preview',{},token=token)[0],403)
  code,plan=self.request('/api/portfolio/cleanup-preview',{},token=token,csrf=csrf);self.assertEqual(code,200)
  code,result=self.request('/api/portfolio/cleanup',dict(options=plan['options'],review=plan['review'],confirmation='OPSCHONEN'),token=token,csrf=csrf);self.assertEqual(code,200);self.assertTrue(result['ok'])
  self.auth.save_user(dict(username='reader',password='Long-test-password-2026',role='basic',active=True));reader=self.auth.login('reader','Long-test-password-2026','test')
  self.assertEqual(self.request('/api/portfolio/cleanup-preview',{},token=reader,csrf=self.auth.user(reader)['csrf'])[0],403)
