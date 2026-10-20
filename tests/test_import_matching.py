import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from imports.service import preview,commit,open_preview
from imports.matching import resolve_instrument

CSV='Action,Time (UTC),ISIN,Ticker,Name,ID,No. of shares,Price / share,Currency (Price / share)\nMarket buy,2026-01-01 10:00:00,NL0010273215,ASML,ASML,1,1,100,EUR\n'
STOCK={'symbol':'ASML.AS','exchange':'AMSTERDAM','currency':'EUR','name':'ASML'}
class MatchingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add_account({'name':'Broker','broker':'Trading 212'})
  self.batch=preview(self.store,2,'trading212','test.csv',CSV)['batch_id']
  blocker=patch('imports.matching.listing',side_effect=ValueError('not available'));blocker.start();self.addCleanup(blocker.stop)
 def test_isin_auto_resolution_is_saved_and_commits_without_user_mappings(self):
  with patch('imports.matching.search_stocks',return_value=[STOCK]) as search,patch('imports.matching.fetch_quote',return_value=(100,'2026-01-01T00:00:00Z')):
   result=resolve_instrument(self.store,self.batch,'ASML|EUR')
   self.assertEqual(search.call_args.args[0],'NL0010273215');self.assertEqual(result['mapping'],STOCK)
  opened=open_preview(Store(self.tmp.name),self.batch);self.assertEqual(opened['rows'][0]['mapping'],STOCK)
  self.assertEqual(commit(self.store,self.batch,{})['imported'],1)
  next_batch=preview(self.store,2,'trading212','next.csv',CSV.replace(',1,1,100,',',2,1,100,'))['batch_id']
  with patch('imports.matching.search_stocks') as search:
   self.assertEqual(resolve_instrument(Store(self.tmp.name),next_batch,'ASML|EUR')['mapping'],STOCK);search.assert_not_called()
 def test_ticker_fallback_normalizes_broker_suffix_without_fuzzy_selection(self):
  batch=preview(self.store,2,'trading212','us.csv',CSV.replace('NL0010273215,ASML,ASML','US0378331005,AAPL_US_EQ,Apple').replace(',EUR',',USD'))['batch_id']
  stock={'symbol':'AAPL','exchange':'NASDAQ','currency':'USD','name':'Apple'}
  with patch('imports.matching.search_stocks',side_effect=[[],[stock]]) as search,patch('imports.matching.fetch_quote',return_value=(100,'')):
   result=resolve_instrument(self.store,batch,'AAPL_US_EQ|USD');self.assertEqual(result['mapping'],stock)
   self.assertEqual(search.call_args.args[0],'AAPL')
 def test_ambiguous_or_wrong_currency_never_picks_arbitrary_listing(self):
  with patch('imports.matching.search_stocks',return_value=[STOCK,{**STOCK,'symbol':'OTHER.AS'}]),patch('imports.matching.fetch_quote',return_value=(100,'')):
   # Exact ticker wins over unrelated hits.
   self.assertEqual(resolve_instrument(self.store,self.batch,'ASML|EUR')['mapping'],STOCK)
  with self.store.connect() as db:db.execute('DELETE FROM instrument_mappings')
  batch=preview(self.store,2,'trading212','wrong.csv',CSV.replace(',EUR',',USD'))['batch_id']
  with patch('imports.matching.search_stocks',return_value=[STOCK]),patch('imports.matching.fetch_quote',side_effect=ValueError('currency')):
   result=resolve_instrument(self.store,batch,'ASML|USD');self.assertIn('Bronvaluta',result['error'])
  with self.assertRaises(ValueError):commit(self.store,batch,{})
 def test_transient_provider_failure_can_be_retried(self):
  with patch('imports.matching.search_stocks',side_effect=OSError('offline')):self.assertIn('error',resolve_instrument(self.store,self.batch,'ASML|EUR'))
  with patch('imports.matching.search_stocks',return_value=[STOCK]),patch('imports.matching.fetch_quote',return_value=(100,'')):
   self.assertIn('mapping',resolve_instrument(self.store,self.batch,'ASML|EUR'))
 def test_actual_quote_currency_overrides_search_exchange_default(self):
  batch=preview(self.store,2,'trading212','usd.csv',CSV.replace(',EUR',',USD'))['batch_id']
  with patch('imports.matching.search_stocks',return_value=[STOCK]),patch('imports.matching.fetch_quote',return_value=(100,'')):
   result=resolve_instrument(self.store,batch,'ASML|USD');self.assertEqual(result['mapping']['currency'],'USD')
 def test_multiple_verified_listings_are_not_silently_selected(self):
  with patch('imports.matching.search_stocks',return_value=[STOCK,{**STOCK,'symbol':'ASML.DE','exchange':'XETRA'}]),patch('imports.matching.fetch_quote',return_value=(100,'')):
   self.assertIn('error',resolve_instrument(self.store,self.batch,'ASML|EUR'))
 def test_etf_search_supports_nyse_arca(self):
  from provider import search_stocks
  with patch('provider._payload',return_value={'quotes':[{'symbol':'VOO','exchange':'PCX','quoteType':'ETF','longname':'Vanguard S&P 500'}]}):
   results=search_stocks('ETF automatic matching test',store=self.store)
   self.assertEqual(results[0]['exchange'],'NYSEARCA');self.assertEqual(results[0]['currency'],'USD')
 def test_issuer_isin_catalogue_resolves_named_etfs_without_search_index(self):
  for isin,ticker,symbol,currency,exchange in [('IE00BK5BQT80','VWCE','VWCE.AS','EUR','AMSTERDAM'),('IE00B3XXRP09','VUSA','VUSA.AS','EUR','AMSTERDAM'),('IE00BK5BR733','VFEA','VFEA.DE','EUR','XETRA'),('IE00BYVTMV98','EQGB','EQGB.L','GBX','LONDON')]:
   batch=preview(self.store,2,'trading212','etf.csv',CSV.replace('NL0010273215,ASML,ASML',isin+','+ticker+','+ticker).replace(',EUR',','+currency))['batch_id']
   stock={'symbol':symbol,'currency':currency,'exchange':exchange,'name':ticker}
   with patch('imports.matching.listing',return_value=stock),patch('imports.matching.search_stocks') as search:
    result=resolve_instrument(self.store,batch,ticker+'|'+currency);self.assertEqual(result['mapping'],stock);search.assert_not_called()
 def test_foreign_settlement_currency_resolves_to_verified_quote_for_conversion(self):
  batch=preview(self.store,2,'trading212','foreign.csv',CSV.replace('NL0010273215,ASML,ASML','US0378331005,AAPL,Apple'))['batch_id']
  stock={'symbol':'AAPL','currency':'USD','exchange':'NASDAQ','name':'Apple'}
  with patch('imports.matching.search_stocks',return_value=[stock]),patch('imports.matching.fetch_quote',side_effect=ValueError('currency')),patch('imports.matching.listing',return_value=stock):
   result=resolve_instrument(self.store,batch,'AAPL|EUR');self.assertEqual(result['mapping']['currency'],'USD')

 def test_altria_and_sofina_isin_resolve_when_search_is_incomplete(self):
  for isin,ticker,symbol,currency,exchange in [('US02209S1033','MO','MO','USD','NYSE'),('BE0003717312','SOF','SOF.BR','EUR','BRUSSELS')]:
   batch=preview(self.store,2,'trading212','equity.csv',CSV.replace('NL0010273215,ASML,ASML',isin+','+ticker+','+ticker))['batch_id']
   stock=dict(symbol=symbol,currency=currency,exchange=exchange,name=ticker)
   with patch('imports.matching.listing',return_value=stock),patch('imports.matching.search_stocks') as search:
    self.assertEqual(resolve_instrument(self.store,batch,ticker+'|EUR')['mapping'],stock);search.assert_not_called()
 def test_brussels_listing_metadata_and_search_are_supported(self):
  from provider import listing,search_stocks
  meta=dict(symbol='SOF.BR',exchangeName='BRU',currency='EUR',longName='Sofina')
  with patch('provider._payload',return_value={'chart':{'result':[{'meta':meta}]}}):
   self.assertEqual(listing('SOF.BR')['exchange'],'BRUSSELS')
  with patch('provider._payload',return_value={'quotes':[dict(symbol='SOF.BR',exchange='BRU',quoteType='EQUITY')]}):
   self.assertEqual(search_stocks('Sofina Brussels regression')[0]['symbol'],'SOF.BR')

 def test_spanish_and_otc_isin_catalogue_resolves_reported_instruments(self):
  for isin,ticker,symbol,currency,exchange in [('ES0113860A34','SAB','SAB.MC','EUR','MADRID'),('ES0180907000','UNI','UNI.MC','EUR','MADRID'),('US88032Q1094','TCEHY','TCEHY','USD','OTC')]:
   batch=preview(self.store,2,'trading212','reported.csv',CSV.replace('NL0010273215,ASML,ASML',isin+','+ticker+','+ticker).replace(',EUR',','+currency))['batch_id']
   stock=dict(symbol=symbol,currency=currency,exchange=exchange,name=ticker)
   with patch('imports.matching.listing',return_value=stock),patch('imports.matching.search_stocks') as search:
    self.assertEqual(resolve_instrument(self.store,batch,ticker+'|'+currency)['mapping'],stock);search.assert_not_called()
