import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,open_preview
from imports.partial import commit_partial
from imports.matching import resolve_instrument

HEADER='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total)\n'
class ImportEdgeCases(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.store=Store(self.tmp.name);self.store.add_account(dict(name='Broker',broker='Trading 212'))
 def preview(self,rows):return preview(self.store,2,'trading212','api.csv',HEADER+rows)
 def test_zero_price_keeps_currency_without_creating_empty_resolution_request(self):
  batch=self.preview('Market sell,2025-10-02 10:00:00,NL0009272756,TMX,AMX,zero,2,0,EUR,0,EUR\n')
  self.assertEqual(batch['rows'][0]['currency'],'EUR');self.assertEqual(batch['instruments'],[])
  with self.store.connect() as db:
   row=batch['rows'][0];row.pop('currency');row['error']='Aantal of prijs ontbreekt.'
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps([row]),batch['batch_id']))
  opened=open_preview(self.store,batch['batch_id'])
  self.assertEqual(opened['rows'][0]['currency'],'EUR');self.assertEqual(opened['instruments'],[])
  result=commit_partial(self.store,batch['batch_id']);self.assertEqual(result['pending'],1)
  self.assertEqual(self.store.state()['purchases'],[])
 def test_distribution_and_cvr_are_recognized_and_never_booked_as_cash_income(self):
  batch=self.preview('Stock distribution,2025-10-02 10:00:00,NL0009272749,TDT,AEX,d,2,0,EUR,0,EUR\nCustom stock distribution,2025-10-09 10:00:00,,EPIX.CVR,Right,c,2,0,USD,0,USD\n')
  self.assertEqual([r['kind'] for r in batch['rows']],['DISTRIBUTION','DISTRIBUTION'])
  self.assertEqual(batch['instruments'],[])
  result=commit_partial(self.store,batch['batch_id']);self.assertEqual(result['pending'],2)
  self.assertEqual(self.store.state()['purchases'],[]);self.assertEqual(self.store.state()['dividends'],[])
 def test_historical_delisted_securities_do_not_require_a_live_quote(self):
  for isin,ticker,currency,symbol in [('NL0009272756','TMX','EUR','TMX.AS'),('CA29668H7085','EPIX','USD','EPIX'),('US02919L8853','AREB','USD','AREB')]:
   with self.subTest(ticker=ticker):
    batch=self.preview(f'Market buy,2025-01-01 10:00:00,{isin},{ticker},Name,{ticker},2,100,{currency},200,{currency}\n')
    with patch('imports.matching.listing',side_effect=AssertionError('no live quote required')),patch('imports.matching.search_stocks',side_effect=AssertionError('no fuzzy search')):
     result=resolve_instrument(self.store,batch['batch_id'],ticker+'|'+currency)
    self.assertEqual(result['mapping']['symbol'],symbol)
    self.assertNotIn('price',result['mapping'])
 def test_post_delisting_trade_cannot_use_historical_fallback(self):
  batch=self.preview('Market buy,2026-01-01 10:00:00,CA29668H7085,EPIX,Name,new,2,100,USD,200,USD\n')
  with patch('imports.matching.listing',side_effect=ValueError('delisted')),patch('imports.matching.search_stocks',return_value=[]):
   self.assertIn('error',resolve_instrument(self.store,batch['batch_id'],'EPIX|USD'))
