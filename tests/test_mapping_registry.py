import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,commit,open_preview
from imports.matching import resolve_instrument
from imports.registry import discover,edit,lookup,remember
from provider import _payload,ProviderBusy
from restore import restore_backup

CSV='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share)\nMarket buy,2026-01-01 10:00:00,NL0010273215,ASML,ASML,mapping-test,1,100,EUR\n'
STOCK=dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')
class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
  self.batch=preview(self.store,2,'trading212','test.csv',CSV)['batch_id']
 def remember(self):
  row=open_preview(self.store,self.batch)['rows'][0];remember(self.store,2,'trading212',row,STOCK);return row
 def test_persistent_mapping_reused_offline_after_cache_expiry_and_restart(self):
  self.remember()
  with self.store.connect() as db:db.execute('DELETE FROM api_cache')
  with patch('imports.matching.search_stocks',side_effect=AssertionError('network')),patch('imports.matching.listing',side_effect=AssertionError('network')):
   result=resolve_instrument(Store(self.tmp.name),self.batch,'ASML|EUR')
  self.assertEqual(result['mapping'],STOCK)
 def test_listing_and_backfill_never_call_provider(self):
  with self.store.connect() as db:
   rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(self.batch,)).fetchone()[0]);rows[0]['mapping']=STOCK
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),self.batch))
  with patch('imports.registry.listing',side_effect=AssertionError('network')):
   found=discover(Store(self.tmp.name));self.assertEqual(found[0]['symbol'],'ASML.AS')
 def test_edit_updates_open_preview_but_never_booked_trades(self):
  row=self.remember();commit(self.store,self.batch,{})
  second=preview(self.store,2,'trading212','next.csv',CSV.replace('mapping-test','next-test'))['batch_id']
  entry=discover(self.store)[0];corrected={**STOCK,'symbol':'ASML.DE','exchange':'XETRA'}
  with patch('imports.registry.listing',return_value=corrected):edit(self.store,dict(id=entry['id'],**corrected))
  self.assertEqual(open_preview(self.store,second)['rows'][0]['mapping'],corrected)
  self.assertEqual(self.store.state()['purchases'][0]['symbol'],'ASML.AS')
  self.assertEqual(lookup(self.store,2,'trading212',row),corrected)
  commit(self.store,second,{})
  with self.store.connect() as db:
   payload=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(second,)).fetchone()[0])
   self.assertEqual(payload[0]['mapping'],corrected)
 def test_edit_rejects_unverified_currency_and_preserves_mapping(self):
  row=self.remember();entry=discover(self.store)[0]
  with patch('imports.registry.listing',return_value=STOCK),self.assertRaises(ValueError):edit(self.store,dict(id=entry['id'],**{**STOCK,'currency':'USD'}))
  self.assertEqual(lookup(self.store,2,'trading212',row),STOCK)
 def test_isin_reuse_across_settlement_currency_but_never_accounts(self):
  row=self.remember();self.assertEqual(lookup(self.store,2,'trading212',{**row,'currency':'USD'}),STOCK)
  self.store.add_account(dict(name='Other',broker='Trading 212'))
  self.assertIsNone(lookup(self.store,3,'trading212',row))
 def test_registry_backup_restore_includes_manual_and_pending_entries(self):
  row=self.remember();entry=discover(self.store)[0]
  with patch('imports.registry.listing',return_value=STOCK):edit(self.store,dict(id=entry['id'],**STOCK))
  content=self.store.backup().read_bytes()
  restore_backup(self.store,content)
  self.assertEqual(discover(self.store)[0]['origin'],'manual')
  self.assertEqual(lookup(self.store,2,'trading212',row),STOCK)
 def test_provider_rate_limit_stops_following_network_calls(self):
  request=Request('https://query1.finance.yahoo.com/test')
  error=HTTPError(request.full_url,429,'limited',{'Retry-After':'120'},None)
  with patch('provider.urlopen',side_effect=error) as network:
   for key in ('first','second'):
    with self.assertRaises(ProviderBusy):_payload(request,1,self.store,'test',key,10)
   self.assertEqual(network.call_count,1)
  with patch('provider.urlopen',side_effect=AssertionError('network')):
   with self.assertRaises(ProviderBusy):_payload(request,1,Store(self.tmp.name),'test','third',10)

 def test_old_schema_eight_backup_restores_without_registry(self):
  import sqlite3
  self.remember();backup=self.store.backup()
  from contextlib import closing
  with closing(sqlite3.connect(backup)) as db:
   db.execute('DROP TABLE instrument_mappings');db.execute('PRAGMA user_version=8');db.commit()
  restore_backup(self.store,backup.read_bytes())
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM instrument_mappings').fetchone()[0],0)
 def test_provider_pause_is_returned_without_trying_more_queries(self):
  with patch('imports.matching.search_stocks',side_effect=ProviderBusy('Even wachten')) as search:
   result=resolve_instrument(self.store,self.batch,'ASML|EUR')
  self.assertTrue(result['retry_later']);self.assertEqual(search.call_count,1)
