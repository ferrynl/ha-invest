import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
import test_security_restore_cache as support
from backup_files import inventory,file_path,revision
from resource_stats import ResourceMonitor
from restore import restore_backup

class BackupFileTests(unittest.TestCase):
 setUp=support.AccessTests.setUp
 tearDown=support.AccessTests.tearDown
 request=support.AccessTests.request
 activate=support.AccessTests.activate
 def make_file(self,name,content=b'update package'):
  path=self.store.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content);return path
 def test_inventory_includes_all_nested_safety_and_update_files_and_matches_stats(self):
  for folder in ('','migrations/','restores/','deletions/','conversions/'):
   self.make_file('backups/'+folder+'test.sqlite3',b'SQLite format 3\x00'+b'x'*20)
  self.make_file('updates/old/package.zip');self.make_file('private.txt')
  data=inventory(self.store);self.assertEqual(len(data['files']),6)
  self.assertEqual(data['backup_bytes'],ResourceMonitor(self.store,self.cache).disk()['backup_bytes'])
  self.assertEqual({r['kind'] for r in data['files']},{'backup','migration','restore','deletion','conversion','update'})
  self.assertEqual(sum(r['bytes'] for r in data['files']),data['total_bytes'])
  self.assertFalse(next(r for r in data['files'] if r['kind']=='update')['restorable'])
 def test_path_rejects_traversal_live_database_and_missing_files(self):
  for name in ('../portfolio.sqlite3','backups/../../portfolio.sqlite3','/backups/a','backups\\a','portfolio.sqlite3','backups','backups/missing',None):
   with self.subTest(name=name),self.assertRaises(ValueError):file_path(self.store,name)
 def test_basic_users_cannot_list_download_delete_or_restore_and_csrf_is_required(self):
  token,csrf=self.activate();self.auth.save_user({'username':'viewer','password':self.password,'role':'basic'});basic=self.auth.login('viewer',self.password,'test')
  for path in ('/api/portfolio/files','/api/portfolio/file?name=backups/test.sqlite3'):
   self.assertEqual(self.request('GET',path,token=basic)[0],403)
  for path in ('/api/portfolio/file-delete','/api/portfolio/file-restore'):
   self.assertEqual(self.request('POST',path,{},token=basic,csrf=self.auth.user(basic)['csrf'])[0],403)
   self.assertEqual(self.request('POST',path,{},token=token)[0],403)
 def test_download_and_reviewed_delete_require_confirmation_and_unchanged_file(self):
  path=self.make_file('updates/sub/file.zip',b'package contents');data={'name':'updates/sub/file.zip','revision':revision(path)}
  code,body,headers=self.request('GET','/api/portfolio/file?name=updates/sub/file.zip');self.assertEqual(code,200);self.assertEqual(body,b'package contents');self.assertEqual(headers['Cache-Control'],'no-store')
  self.assertEqual(self.request('POST','/api/portfolio/file-delete',data)[0],400);self.assertTrue(path.exists())
  data['confirmation']='DELETE';path.write_bytes(b'changed package');self.assertEqual(self.request('POST','/api/portfolio/file-delete',data)[0],400);self.assertTrue(path.exists())
  data['revision']=revision(path);self.assertEqual(self.request('POST','/api/portfolio/file-delete',data)[0],200);self.assertFalse(path.exists())
 def test_server_restore_large_file_preserves_users_makes_safety_backup_and_clears_sessions(self):
  token,csrf=self.activate()
  trade=dict(symbol='TEST',exchange='TEST',currency='EUR',name='Test',quantity='2',price='100',purchased_on='2026-01-02')
  self.store.add(trade);self.store.add_dividend(dict(symbol='TEST',exchange='TEST',currency='EUR',amount='5',paid_on='2026-02-01'))
  backup=self.store.backup();
  with backup.open('ab') as stream:stream.truncate(26*1024*1024)
  self.store.add({**trade,'quantity':'3'})
  data=dict(name=backup.relative_to(self.store.root).as_posix(),revision=revision(backup),confirmation='RESTORE')
  with patch.object(Path,'read_bytes',side_effect=AssertionError('Large backups must not be read into memory')):
   code,body,headers=self.request('POST','/api/portfolio/file-restore',data,token=token,csrf=csrf)
  self.assertEqual(code,200,body);self.assertIsNone(self.auth.user(token))
  with self.store.read() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5')
   self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE username='owner'").fetchone()[0],1)
  self.assertTrue(any(r['kind']=='restore' for r in inventory(self.store)['files']))
 def test_non_database_cannot_be_restored(self):
  path=self.make_file('updates/file.zip');data=dict(name='updates/file.zip',revision=revision(path),confirmation='RESTORE')
  self.assertEqual(self.request('POST','/api/portfolio/file-restore',data)[0],400);self.assertTrue(path.exists())
 def test_symlinks_are_not_listed_or_accessible(self):
  path=self.make_file('private.txt');link=self.store.root/'backups'/'leak';link.parent.mkdir(exist_ok=True)
  try:link.symlink_to(path)
  except OSError:self.skipTest('Symlinks unavailable on this Windows account')
  self.assertNotIn('backups/leak',[r['name'] for r in inventory(self.store)['files']])
  with self.assertRaises(ValueError):file_path(self.store,'backups/leak')
