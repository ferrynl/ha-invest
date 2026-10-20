import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,commit
from imports.trading212 import parse_csv
from persistent_cache import cached_json
from updates import check_updates
from restore import restore_backup

HEADER='Action,Time,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total),ID\n'
CSV=HEADER+'Market buy,2026-10-12 10:00:00,ASML,ASML,2,100,EUR,200,EUR,buy-1\nMarket sell,2026-10-13 10:00:00,ASML,ASML,1,150,EUR,150,EUR,sell-1\nDividend (Ordinary),2026-10-14 10:00:00,ASML,ASML,,,,2,EUR,div-1\nDeposit,2026-10-11 10:00:00,,,,,1000,EUR,deposit-1\n'
MAPPING={'ASML|EUR':dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',name='ASML')}

class ImportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name)
  self.store.add_account(dict(name='Invest',broker='Trading 212'))
 def test_preview_commit_sales_dividend_and_repeat_are_account_scoped(self):
  result=preview(self.store,2,'trading212','history.csv',CSV)
  self.assertEqual(self.store.state()['purchases'],[])
  self.assertEqual(commit(self.store,result['batch_id'],MAPPING)['imported'],3)
  self.assertEqual(commit(self.store,result['batch_id'],MAPPING)['imported'],0)
  self.store.quote('ASML.AS','AMSTERDAM','EUR','200','2026-10-16T15:30:00+00:00','test')
  position=self.store.state()['positions'][0]
  self.assertEqual(position['account_id'],2);self.assertEqual(position['quantity'],'1')
  self.assertEqual(position['cost'],'100');self.assertEqual(position['realised'],'50')
  self.assertEqual(position['total_gain'],'152')
  again=preview(self.store,2,'trading212','overlapping.csv',CSV)
  self.assertTrue(again['rows'][0]['duplicate'])
  self.assertEqual(commit(self.store,again['batch_id'],{})['imported'],0)
  self.store.add_account(dict(name='Tweede rekening',broker='Trading 212'))
  other=preview(self.store,3,'trading212','same.csv',CSV)
  self.assertEqual(commit(self.store,other['batch_id'],MAPPING)['imported'],3)
  self.assertEqual(len(self.store.state()['positions']),2)
 def test_time_utc_header_preserves_raw_columns_and_existing_import_identity(self):
  old=parse_csv(CSV);modern=parse_csv(CSV.replace('Action,Time,','Action,Time (UTC),'))
  for first,second in zip(old,modern):
   self.assertEqual(first.get('digest'),second.get('digest'));self.assertEqual(first.get('external_id'),second.get('external_id'))
   self.assertIn('Time (UTC)',second['raw']);self.assertNotIn('Time',second['raw'])
  imported=preview(self.store,2,'trading212','old.csv',CSV);commit(self.store,imported['batch_id'],MAPPING)
  again=preview(self.store,2,'trading212','api.csv',CSV.replace('Action,Time,','Action,Time (UTC),'))
  self.assertEqual(commit(self.store,again['batch_id'],{})['imported'],0)
 def test_conflicting_time_aliases_and_duplicate_headers_are_rejected(self):
  conflict=CSV.replace('Action,Time,','Action,Time (UTC),Time,').replace('2026-10-12 10:00:00,','2026-10-12 10:00:00,2026-10-12 11:00:00,')
  self.assertIn('verschillende transactietijden',parse_csv(conflict)[0]['error'])
  with self.assertRaises(ValueError):parse_csv('Action,Time,Time,Ticker,Name\n')
 def test_bad_sell_or_unknown_action_rolls_back_entire_batch(self):
  oversell=CSV.replace(',1,150,EUR,150,EUR,sell-1',',3,150,EUR,450,EUR,sell-1')
  result=preview(self.store,2,'trading212','bad.csv',oversell)
  with self.assertRaises(ValueError):commit(self.store,result['batch_id'],MAPPING)
  self.assertEqual(self.store.state()['purchases'],[])
  result=preview(self.store,2,'trading212','split.csv',CSV+'Stock split,2026-10-15 10:00:00,ASML,ASML,2,0,EUR,0,EUR,split-1\n')
  with self.assertRaises(ValueError):commit(self.store,result['batch_id'],MAPPING)
  self.assertEqual(self.store.state()['dividends'],[])
 def test_wrong_currency_and_conflicting_source_ids_are_rejected(self):
  result=preview(self.store,2,'trading212','history.csv',CSV)
  with self.assertRaises(ValueError):commit(self.store,result['batch_id'],{'ASML|EUR':{**MAPPING['ASML|EUR'],'currency':'USD'}})
  commit(self.store,result['batch_id'],MAPPING)
  changed=preview(self.store,2,'trading212','changed.csv',CSV.replace(',2,100,EUR',',2,101,EUR'))
  self.assertTrue(changed['rows'][0]['error'])
  with self.assertRaises(ValueError):commit(self.store,changed['batch_id'],MAPPING)
 def test_account_separation_and_backup_restore_keep_import_deduplication(self):
  result=preview(self.store,2,'trading212','history.csv',CSV);commit(self.store,result['batch_id'],MAPPING)
  self.store.add(dict(name='ASML',symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR',quantity='10',price='300',purchased_on='2026-10-12'))
  snapshot=self.store.backup().read_bytes()
  self.store.add_account(dict(name='Later',broker='Andere broker'))
  restore_backup(self.store,snapshot)
  state=self.store.state();self.assertEqual(len(state['accounts']),2)
  positions={p['account_id']:p for p in state['positions']}
  self.assertEqual(positions[1]['quantity'],'10');self.assertEqual(positions[1]['dividend'],'0')
  self.assertEqual(positions[2]['quantity'],'1');self.assertEqual(positions[2]['dividend'],'2')
  again=preview(self.store,2,'trading212','same.csv',CSV)
  self.assertEqual(commit(self.store,again['batch_id'],{})['imported'],0)
 def test_persistent_response_cache_survives_restart_and_expires(self):
  loader=Mock(return_value={'quotes':[{'symbol':'ASML.AS'}]})
  cached_json(self.store,'search','asml',604800,loader)
  restarted=Store(self.temp.name)
  cached_json(restarted,'search','asml',604800,loader);loader.assert_called_once()
  with self.store.connect() as db:db.execute("UPDATE api_cache SET expires_at=0")
  cached_json(restarted,'search','asml',604800,loader);self.assertEqual(loader.call_count,2)
 def test_yahoo_raw_search_payload_is_saved_and_reused_after_restart(self):
  from provider import search_stocks,_search_stocks
  payload={'quotes':[dict(symbol='ASML.AS',longname='ASML',exchange='AMS',quoteType='EQUITY')],'count':1}
  with patch('provider.urlopen') as request:
   request.return_value.__enter__.return_value.read.return_value=json.dumps(payload).encode()
   search_stocks('asml',store=self.store);_search_stocks.cache_clear()
   search_stocks('asml',store=Store(self.temp.name));request.assert_called_once()
  with self.store.connect() as db:raw=db.execute("SELECT payload FROM api_cache WHERE namespace='yahoo-search-v3'").fetchone()[0]
  self.assertEqual(json.loads(raw),payload)
 def test_update_check_is_read_only_and_cached_for_one_day(self):
  with patch('updates.urlopen') as request:
   request.return_value.__enter__.return_value.read.return_value=b'name: Home Invest\nversion: "99.0.0"\n'
   result=check_updates(self.store);self.assertTrue(result['available'])
   self.assertEqual(check_updates(Store(self.temp.name))['latest'],'99.0.0');request.assert_called_once()
 def test_csv_requires_expected_headers(self):
  with self.assertRaises(ValueError):parse_csv('foo,bar\n1,2\n')
 def test_old_history_is_kept_and_only_recent_window_is_requested(self):
  self.store.save_history('ASML.AS','AMSTERDAM','EUR','2020-01-01',[dict(day='2026-10-16',price='100')])
  self.assertEqual(self.store.history_start('ASML.AS','AMSTERDAM','EUR','2020-01-01'),'2026-10-09')
  self.assertEqual(self.store.history_start('ASML.AS','AMSTERDAM','EUR','2019-01-01'),'2019-01-01')
 def test_repeated_source_id_within_same_export_is_not_double_booked(self):
  rows=CSV.splitlines();duplicated='\n'.join([rows[0],rows[1],rows[1],*rows[2:]])+'\n'
  result=preview(self.store,2,'trading212','duplicate.csv',duplicated)
  self.assertEqual(commit(self.store,result['batch_id'],MAPPING)['imported'],3)
