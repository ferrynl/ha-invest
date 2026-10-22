import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from instruments import details,save_categories
from restore import restore_backup
from imports.service import preview
from imports.registry import remember
from imports.partial import commit_partial
from test_corporate_actions import HEADER,BUY,CLOSE,OPEN,CAPITAL,STOCK

class InstrumentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
  batch=preview(self.store,2,'trading212','test.csv',HEADER+BUY+CLOSE+OPEN+CAPITAL)
  for row in batch['rows']:
   if row.get('currency'):remember(self.store,2,'trading212',row,STOCK)
  commit_partial(self.store,batch['batch_id'])
  self.store.add_dividend(dict(**STOCK,account_id=2,amount='5',paid_on='2026-10-04'))
  self.store.add(dict(**STOCK,account_id=1,quantity='1',price='100',purchased_on='2026-10-01'))
 def test_details_are_scoped_and_include_split_capital_dividend_and_actual_prices(self):
  self.store.quote(STOCK['symbol'],STOCK['exchange'],STOCK['currency'],'140','2026-10-05T10:00:00+00:00','test')
  with self.store.connect() as db:db.execute('INSERT INTO daily_prices VALUES(?,?,?,?,?)',(STOCK['symbol'],STOCK['exchange'],STOCK['currency'],'2026-10-01','120'))
  result=details(self.store,STOCK,'2')
  self.assertEqual({r['type'] for r in result['events']},{'BUY','SPLIT','DIVIDEND','CAPITAL_RETURN'})
  self.assertTrue(all(r['account_id']==2 for r in result['events']))
  self.assertEqual(result['prices'],[dict(day='2026-10-01',price='120')])
  self.assertEqual(result['quote']['price'],'140')
  self.assertEqual(len(details(self.store,STOCK,'all')['events']),len(result['events'])+1)
 def test_categories_shared_across_accounts_and_survive_restart_and_restore(self):
  values=dict(sector='Technologie',country='Nederland',asset_type='Aandeel',category='Groei')
  save_categories(self.store,dict(**STOCK,**values))
  self.assertEqual(details(Store(self.tmp.name),STOCK,'1')['categories']['category'],'Groei')
  positions=self.store.state()['positions'];self.assertTrue(all(p['categories']['sector']=='Technologie' for p in positions))
  backup=self.store.backup().read_bytes();save_categories(self.store,dict(**STOCK,category='Anders'))
  restore_backup(self.store,backup)
  self.assertEqual(details(self.store,STOCK,'2')['categories']['category'],'Groei')
  with self.store.connect() as db:
   db.execute("UPDATE instrument_categories SET asset_type='Invalid'")
  bad=self.store.backup().read_bytes()
  with self.assertRaises(ValueError):restore_backup(self.store,bad)
  self.assertEqual(len(self.store.state()['purchases']),3)
 def test_pending_source_events_remain_distinct_from_booked_transactions(self):
  unknown=BUY.replace('Market buy','Unknown conversion').replace(',buy,',',pending,')
  batch=preview(self.store,2,'trading212','pending.csv',HEADER+unknown);commit_partial(self.store,batch['batch_id'])
  events=details(self.store,STOCK,'2')['events']
  pending=next(e for e in events if e['kind']=='issue')
  self.assertEqual(pending['status'],'Te beoordelen')
  self.assertEqual(pending['day'],'2026-10-01')
  self.assertNotIn('issue',{e['kind'] for e in details(self.store,STOCK,'2',include_pending=False)['events']})
  self.assertEqual(len(self.store.state()['purchases']),3)
 def test_scoped_deletion_preserves_shared_categories_and_full_reset_clears_them(self):
  import transactions
  save_categories(self.store,dict(**STOCK,category='Groei'))
  snapshot=transactions.reset_preview(self.store,2)
  transactions.reset(self.store,dict(account_id=2,revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  self.assertEqual(details(self.store,STOCK,1)['categories']['category'],'Groei')
  snapshot=transactions.reset_preview(self.store,'all')
  self.assertEqual(snapshot['counts']['instrument_categories'],1)
  transactions.reset(self.store,dict(account_id='all',revision=snapshot['revision'],confirmation='VERWIJDEREN'))
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM instrument_categories').fetchone()[0],0)
 def test_invalid_and_unknown_categories_cannot_be_saved(self):
  for value in [dict(category='a'*81),dict(country='bad\nvalue'),dict(asset_type='Guess'),dict(sector=[]),dict(symbol='OTHER')]:
   with self.subTest(value=value),self.assertRaises(ValueError):save_categories(self.store,{**STOCK,**value})
  self.assertEqual(details(self.store,STOCK)['categories']['sector'],'')
 def test_uncertain_capital_mapping_is_not_attached_to_wrong_listing(self):
  with self.store.connect() as db:db.execute("UPDATE instrument_mappings SET symbol='OTHER'")
  self.assertNotIn('CAPITAL_RETURN',{e['type'] for e in details(self.store,STOCK,'2')['events']})

import test_transactions as transaction_test_support

class InstrumentHttpTests(unittest.TestCase):
 setUp=transaction_test_support.TransactionHttpTests.setUp
 tearDown=transaction_test_support.TransactionHttpTests.tearDown
 request=transaction_test_support.TransactionHttpTests.request
 def test_categories_require_admin_csrf_and_invalidate_state(self):
  query='/api/instrument?symbol=ASML.AS&exchange=AMSTERDAM&currency=EUR&account_id=all'
  self.assertEqual(self.request(query)[0],200)
  self.cache.get(self.store.state)
  self.assertEqual(self.request('/api/instrument/categories',dict(**STOCK,sector='Technologie'))[0],200)
  self.assertEqual(self.request('/api/state')[1]['positions'][0]['categories']['sector'],'Technologie')
  self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test');csrf=self.auth.user(token)['csrf']
  self.assertEqual(self.request(query)[0],401)
  self.assertEqual(self.request('/api/instrument/categories',dict(**STOCK,category='Groei'),token)[0],403)
  self.assertEqual(self.request('/api/instrument/categories',dict(**STOCK,category='Groei'),token,csrf)[0],200)
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
  pending=BUY.replace('Market buy','Unknown conversion').replace(',buy,',',pending,')
  batch=preview(self.store,2,'trading212','pending.csv',HEADER+BUY+pending)
  for row in batch['rows']:
   if row.get('currency'):remember(self.store,2,'trading212',row,STOCK)
  commit_partial(self.store,batch['batch_id'])
  self.assertIn('issue',{e['kind'] for e in self.request(query,token=token)[1]['events']})
  with self.store.connect() as db:db.execute("UPDATE users SET role='basic'")
  self.assertEqual(self.request(query,token=token)[0],200)
  self.assertNotIn('issue',{e['kind'] for e in self.request(query,token=token)[1]['events']})
  self.assertEqual(self.request('/api/instrument/categories',dict(**STOCK,category='Other'),token,csrf)[0],403)
