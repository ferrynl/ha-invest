import sys,tempfile,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio/app'))
from storage import Store
import broker_accounts,transactions
import test_transactions as ledger_tests

class BrokerAccountTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Invest',broker='Trading 212'))
  self.store.add_account(dict(name='Tweede',broker='Revolut'))
 def trade(self,account=2):self.store.add(dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML',quantity='2',price='100',purchased_on='2026-01-01',account_id=account))
 def edit(self,account=2,**fields):return broker_accounts.edit(self.store,{**broker_accounts.overview(self.store,account),**fields})
 def delete(self,account=2):return transactions.reset(self.store,{**transactions.reset_preview(self.store,account),'confirmation':'VERWIJDEREN'},remove_account=True)
 def test_rename_keeps_ledger_and_rejects_stale_editor(self):
  self.trade();before=self.store.state()['purchases'];snapshot=broker_accounts.overview(self.store,2)
  self.edit(name='Nieuwe naam');after=self.store.state()['purchases'];self.assertEqual([{k:v for k,v in row.items() if k!='account_name'} for row in before],[{k:v for k,v in row.items() if k!='account_name'} for row in after])
  self.assertEqual(broker_accounts.overview(self.store,2)['name'],'Nieuwe naam')
  with self.assertRaises(ValueError):broker_accounts.edit(self.store,{**snapshot,'name':'Verouderd'})
 def test_broker_change_requires_empty_account_without_connection(self):
  self.edit(broker='Revolut');self.trade()
  with self.assertRaises(ValueError):self.edit(broker='Trading 212')
  folder=self.store.root/'connections';folder.mkdir();(folder/'3.encrypted').write_bytes(b'fixture')
  with self.assertRaises(ValueError):self.edit(3,broker='Trading 212')
  self.assertEqual(broker_accounts.overview(self.store,3)['broker'],'Revolut')
 def test_delete_scopes_data_preserves_other_accounts_and_saves_backup(self):
  self.trade();self.trade(3)
  folder=self.store.root/'connections';folder.mkdir();(folder/'2.encrypted').write_bytes(b'fixture');(folder/'3.encrypted').write_bytes(b'other')
  result=self.delete();self.assertFalse((folder/'2.encrypted').exists());self.assertTrue((folder/'3.encrypted').exists())
  state=self.store.state();self.assertEqual([a['id'] for a in state['accounts']],[1,3]);self.assertEqual([p['account_id'] for p in state['purchases']],[3])
  backup=transactions.deletion_backup(self.store,result['backup_name'])
  with closing(sqlite3.connect(backup)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],2);self.assertEqual(db.execute('SELECT name FROM broker_accounts WHERE id=2').fetchone()[0],'Invest')
  with self.store.connect() as db:self.assertEqual(list(db.execute('PRAGMA foreign_key_check')),[])
 def test_empty_and_last_account_can_be_deleted(self):
  for account in [3,2,1]:self.delete(account)
  self.assertEqual(self.store.state()['accounts'],[])
  self.store.add_account(dict(name='Opnieuw',broker='Revolut'));self.assertEqual(len(self.store.state()['accounts']),1)
 def test_delete_confirmation_stale_preview_and_backup_failure(self):
  snapshot=transactions.reset_preview(self.store,2)
  with self.assertRaises(ValueError):transactions.reset(self.store,{**snapshot,'confirmation':'yes'},remove_account=True)
  self.edit(name='Gewijzigd')
  with self.assertRaises(ValueError):transactions.reset(self.store,{**snapshot,'confirmation':'VERWIJDEREN'},remove_account=True)
  with patch.object(self.store,'backup',side_effect=OSError('full')),self.assertRaises(OSError):self.delete()
  self.assertEqual(broker_accounts.overview(self.store,2)['name'],'Gewijzigd')
  with self.assertRaises(ValueError):self.delete('all')
 def test_connection_unlink_failure_rolls_back_ledger_and_account(self):
  self.trade()
  with patch.object(Path,'unlink',side_effect=OSError('locked')),self.assertRaises(OSError):self.delete()
  self.assertEqual(len(self.store.state()['purchases']),1);self.assertEqual(broker_accounts.overview(self.store,2)['name'],'Invest')
 def test_import_provenance_is_removed_only_for_selected_account(self):
  from imports.service import preview
  for account in [1,2]:
   if account==1:self.edit(1,broker='Trading 212')
   result=preview(self.store,account,'trading212','source.csv',ledger_tests.HEADER+ledger_tests.SOURCE)
   from imports.registry import remember
   from imports.partial import commit_partial
   for row in result['rows']:
    if row.get('currency'):remember(self.store,account,'trading212',row,ledger_tests.STOCK)
   commit_partial(self.store,result['batch_id'])
  self.delete()
  with self.store.connect() as db:
   self.assertEqual([r[0] for r in db.execute('SELECT account_id FROM import_batches')],[1]);self.assertEqual(list(db.execute('PRAGMA foreign_key_check')),[])
   for table in ('purchases','capital_returns','instrument_mappings','import_records'):
    self.assertEqual({r[0] for r in db.execute('SELECT account_id FROM '+table)},{1},table)

class BrokerAccountHttpTests(ledger_tests.TransactionHttpTests):
 def test_account_changes_invalidate_cached_state_and_delete_returns_backup(self):
  self.cache.get(self.store.state);_,account=self.request('/api/accounts/edit?account_id=1')
  code,_=self.request('/api/accounts/edit',{**account,'name':'Mijn rekening'});self.assertEqual(code,200)
  self.assertEqual(self.request('/api/state')[1]['accounts'][0]['name'],'Mijn rekening')
  _,snapshot=self.request('/api/accounts/delete-preview?account_id=1')
  code,result=self.request('/api/accounts/delete',{**snapshot,'confirmation':'VERWIJDEREN'});self.assertEqual(code,200)
  self.assertEqual(self.request('/api/state')[1]['accounts'],[])
  self.assertEqual(self.request('/api/portfolio/deletion-backup?name='+result['backup_name'])[0],200)
 def test_account_routes_require_admin_and_csrf(self):
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
  paths=['/api/accounts/edit','/api/accounts/delete']
  for path in paths:self.assertEqual(self.request(path,{},token)[0],403)
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  for path in paths:self.assertEqual(self.request(path,{},token,csrf)[0],403)
  for path in ['/api/accounts/edit?account_id=1','/api/accounts/delete-preview?account_id=1']:self.assertEqual(self.request(path,token=token)[0],403)
