import sys,tempfile,unittest,json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from forex import save_rates,get_rate,convert,prepare_rates,remember_coverage,overview,code
from imports.service import preview,commit
from restore import restore_backup

DAY='2026-10-12'
def rates(day=DAY):return [{'base':'EUR','quote':'USD','date':day,'rate':'1.2'},{'base':'EUR','quote':'GBP','date':day,'rate':'0.8'}]
CSV='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share),Total,Currency (Total)\nMarket buy,2026-10-12 10:00:00,US0378331005,AAPL,Apple,buy-1,2,10,EUR,20,EUR\nDividend (Ordinary),2026-10-13 10:00:00,US0378331005,AAPL,Apple,div-1,,,,2,EUR\n'

class ForexTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
 def test_decimal_cross_rates_pence_and_restart_cache(self):
  save_rates(self.store,rates(),__import__('datetime').date(2026,10,12))
  with patch('forex.load_json') as network:
   self.assertEqual(Decimal(convert(Store(self.tmp.name),'10','EUR','USD',DAY)['converted']),Decimal('12'))
   self.assertEqual(Decimal(convert(self.store,'100','GBX','GBP',DAY)['converted']),Decimal(1))
   self.assertEqual(Decimal(convert(self.store,'1','GBP','GBX',DAY)['converted']),Decimal(100))
   self.assertEqual(Decimal(convert(self.store,'120','USD','EUR',DAY)['converted']).quantize(Decimal('.000001')),Decimal('100.000000'))
   network.assert_not_called()
  self.assertEqual(code('GBp'),'GBX')
 def test_weekend_fallback_is_explicit_and_known_history_works_offline(self):
  from datetime import date
  save_rates(self.store,rates('2026-10-16'),date(2026,10,18));remember_coverage(self.store,['USD','GBP'],'2026-10-16','2026-10-18')
  with patch('forex.load_json') as network:
   result=convert(self.store,'10','EUR','USD','2026-10-18');self.assertEqual(result['rate_on'],'2026-10-16');network.assert_not_called()
  with patch('forex.load_json',return_value=rates('2026-10-19')) as network:
   result=convert(self.store,'10','EUR','USD','2026-10-19');self.assertEqual(result['rate_on'],'2026-10-19');network.assert_called_once()
 def test_missing_or_future_rate_never_becomes_one_to_one(self):
  from datetime import date,timedelta
  with patch('forex.load_json',return_value=[]),self.assertRaises(ValueError):convert(self.store,'10','USD','EUR',DAY)
  with self.assertRaises(ValueError):convert(self.store,'10','USD','EUR',(date.today()+timedelta(days=1)).isoformat())
  with self.assertRaises(ValueError):save_rates(self.store,[{'base':'EUR','quote':'USD','date':DAY,'rate':'0'}],date(2026,10,12))
 def test_import_preserves_originals_and_converts_price_and_dividend_by_trade_day(self):
  from datetime import date
  self.store.add_account({'name':'Broker','broker':'Trading 212'})
  batch=preview(self.store,2,'trading212','fx.csv',CSV)['batch_id']
  mapping={'symbol':'AAPL','exchange':'NASDAQ','currency':'USD','name':'Apple'}
  with self.store.connect() as db:
   rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(batch,)).fetchone()[0])
   for row in rows:row['mapping']=mapping
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch))
  save_rates(self.store,rates(),date(2026,10,12))
  save_rates(self.store,[{'base':'EUR','quote':'USD','date':'2026-10-13','rate':'1.25'}],date(2026,10,13))
  with patch('forex.load_json') as network:
   self.assertEqual(commit(self.store,batch,{})['imported'],2);network.assert_not_called()
  state=self.store.state();self.assertEqual(Decimal(state['purchases'][0]['price']),Decimal(12))
  self.assertEqual(state['purchases'][0]['currency'],'USD');self.assertEqual(Decimal(state['dividends'][0]['amount']),Decimal('2.5'))
  with self.store.connect() as db:
   audit=[dict(r) for r in db.execute('SELECT * FROM import_fx ORDER BY id')]
   self.assertEqual(audit[0]['original_amount'],'10');self.assertEqual(audit[0]['rate'],'1.2')
   original=json.loads(db.execute("SELECT raw FROM import_records WHERE external_id='id:buy-1:BUY'").fetchone()[0]);self.assertEqual(original['Price / share'],'10')
  snapshot=self.store.backup().read_bytes();restore_backup(self.store,snapshot)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM import_fx').fetchone()[0],2)
  self.assertEqual(commit(self.store,batch,{})['imported'],0)
 def test_missing_fx_rolls_back_all_financial_rows(self):
  self.store.add_account({'name':'Broker','broker':'Trading 212'});batch=preview(self.store,2,'trading212','fx.csv',CSV)['batch_id']
  with self.store.connect() as db:
   rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(batch,)).fetchone()[0])
   for row in rows:row['mapping']={'symbol':'AAPL','exchange':'NASDAQ','currency':'USD','name':'Apple'}
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch))
  with patch('forex.load_json',return_value=[]),self.assertRaises(ValueError):commit(self.store,batch,{})
  with self.store.connect() as db:
   for table in ['purchases','dividends','import_records','import_fx']:self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
 def test_historical_observations_are_not_silently_rewritten(self):
  from datetime import date
  save_rates(self.store,rates(),date(2026,10,12));changed=rates();changed[0]['rate']='2'
  save_rates(self.store,changed,date(2026,10,12));self.assertEqual(get_rate(self.store,'EUR','USD',DAY)['rate'],'1.2')
 def test_bulk_history_prepares_trade_dates_and_is_reused_after_restart(self):
  requests=[('EUR','USD','2026-10-12'),('USD','GBP','2026-10-13')]
  with patch('forex.load_json',return_value=rates()+rates('2026-10-13')) as network:
   prepare_rates(self.store,requests);network.assert_called_once()
   prepare_rates(Store(self.tmp.name),requests);network.assert_called_once()
  with patch('forex.load_json') as network:
   self.assertEqual(get_rate(self.store,'EUR','USD',DAY)['rate'],'1.2');network.assert_not_called()
 def test_gbp_quote_pence_are_not_treated_as_pounds(self):
  from provider import fetch_quote
  payload={'chart':{'result':[{'meta':{'symbol':'EQGB.L','exchangeName':'LSE','currency':'GBp','regularMarketPrice':50000,'regularMarketTime':1792164600}}]}}
  with patch('provider._payload',return_value=payload):
   price,_=fetch_quote('','EQGB.L','LONDON','GBX');self.assertEqual(price,50000)
   with self.assertRaises(ValueError):fetch_quote('','EQGB.L','LONDON','GBP')
 def test_overview_persists_currency_list_and_remains_useful_offline(self):
  catalog=[{'iso_code':'EUR','name':'Euro'},{'iso_code':'USD','name':'US Dollar'},{'iso_code':'GBP','name':'Pound sterling'}]
  with patch('forex.load_json',side_effect=[catalog,rates()]):
   data=overview(self.store,DAY);self.assertEqual(len(data['currencies']),4)
   self.assertEqual(next(r for r in data['currencies'] if r['code']=='GBX')['to_eur'],'0.0125')
  with self.store.connect() as db:db.execute("UPDATE api_cache SET expires_at=0 WHERE namespace='fx'")
  with patch('forex.load_json',side_effect=ValueError('offline')):
   data=overview(Store(self.tmp.name),DAY);self.assertEqual(len(data['currencies']),4);self.assertIsNotNone(data['error'])
 def test_dividend_only_import_uses_existing_purchase_listing_even_in_other_currency(self):
  from datetime import date
  from imports.matching import resolve_instrument
  self.store.add_account({'name':'Broker','broker':'Trading 212'})
  header,buy,dividend=CSV.strip().splitlines()
  buy=buy.replace(',10,EUR,20,EUR',',10,USD,20,USD')
  first=preview(self.store,2,'trading212','buy.csv',header+'\n'+buy+'\n')['batch_id']
  mapping={'symbol':'AAPL','exchange':'NASDAQ','currency':'USD','name':'Apple'}
  with self.store.connect() as db:
   rows=json.loads(db.execute('SELECT payload FROM import_batches WHERE id=?',(first,)).fetchone()[0]);rows[0]['mapping']=mapping
   db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),first))
  commit(self.store,first,{})
  second=preview(self.store,2,'trading212','dividend.csv',header+'\n'+dividend+'\n')['batch_id']
  with patch('imports.matching.search_stocks') as network:
   self.assertEqual(resolve_instrument(self.store,second,'AAPL|EUR')['mapping'],mapping);network.assert_not_called()
  save_rates(self.store,rates('2026-10-13'),date(2026,10,13))
  self.assertEqual(commit(self.store,second,{})['imported'],1)
  self.assertEqual(Decimal(self.store.state()['dividends'][0]['amount']),Decimal('2.4'))
 def test_empty_provider_reply_is_not_cached_as_historical_success(self):
  with patch('forex.load_json',return_value=[]),self.assertRaises(ValueError):convert(self.store,'10','EUR','USD',DAY)
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM api_cache WHERE namespace='fx'").fetchone()[0],0)
  with patch('forex.load_json',return_value=rates()):self.assertEqual(convert(self.store,'10','EUR','USD',DAY)['converted'],'12.0')
