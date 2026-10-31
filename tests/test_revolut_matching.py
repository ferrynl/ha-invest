import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from provider import ProviderBusy
from imports.matching import resolve

class RevolutMatchingTests(unittest.TestCase):
 def setUp(self):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
  self.store=Store(folder.name)
 def row(self,ticker,currency='USD',isin=''):
  return [dict(ticker=ticker,currency=currency,day='2026-01-01',raw={'ISIN':isin})]
 def test_exact_symbols_do_not_depend_on_search_index(self):
  for ticker in ('T','U','V','O','NFLX'):
   with self.subTest(ticker=ticker):
    stock=dict(symbol=ticker,exchange='NYSE',currency='USD',name=ticker)
    with patch('imports.matching.listing',return_value=stock) as listing,patch('imports.matching.search_stocks') as search:
     self.assertEqual(resolve(self.store,self.row(ticker),'revolut')['mapping'],stock)
     listing.assert_called_once_with(ticker,store=self.store);search.assert_not_called()
 def test_german_venue_codes_use_verified_eur_listing(self):
  for ticker in ('AIXA','2NN','VUSA','VWCE'):
   stock=dict(symbol=ticker+'.DE',exchange='XETRA',currency='EUR',name=ticker)
   with patch('imports.matching.listing',return_value=stock) as listing,patch('imports.matching.search_stocks') as search:
    self.assertEqual(resolve(self.store,self.row(ticker,'EUR'),'revolut')['mapping'],stock)
    listing.assert_called_once_with(ticker+'.DE',store=self.store);search.assert_not_called()
 def test_frankfurt_fallback_is_verified(self):
  stock=dict(symbol='AB2.F',exchange='FRANKFURT',currency='EUR',name='AB2')
  with patch('imports.matching.listing',side_effect=[ValueError('missing'),stock]) as listing:
   self.assertEqual(resolve(self.store,self.row('AB2','EUR'),'revolut')['mapping'],stock)
   self.assertEqual([call.args[0] for call in listing.call_args_list],['AB2.DE','AB2.F'])
 def test_wrong_currency_or_identity_cannot_be_accepted(self):
  for stock in (dict(symbol='SLD.DE',exchange='XETRA',currency='USD'),dict(symbol='OTHER.DE',exchange='XETRA',currency='EUR')):
   with patch('imports.matching.listing',return_value=stock),patch('imports.matching.search_stocks',return_value=[]):
    self.assertIn('error',resolve(self.store,self.row('SLD','EUR'),'revolut'))
 def test_isin_does_not_use_unqualified_ticker_shortcut(self):
  with patch('imports.matching.listing') as listing,patch('imports.matching.search_stocks',return_value=[]):
   self.assertIn('error',resolve(self.store,self.row('T',isin='US0000000000'),'revolut'))
   listing.assert_not_called()
 def test_provider_cooldown_is_respected(self):
  with patch('imports.matching.listing',side_effect=ProviderBusy('wait')),patch('imports.matching.search_stocks') as search:
   with self.assertRaises(ProviderBusy):resolve(self.store,self.row('T'),'revolut')
   search.assert_not_called()
 def test_failure_can_be_retried(self):
  with patch('imports.matching.listing',side_effect=ValueError('offline')),patch('imports.matching.search_stocks',return_value=[]):
   self.assertIn('error',resolve(self.store,self.row('T'),'revolut'))
  stock=dict(symbol='T',exchange='NYSE',currency='USD')
  with patch('imports.matching.listing',return_value=stock):
   self.assertEqual(resolve(self.store,self.row('T'),'revolut')['mapping'],stock)

 def test_wkn_uses_issuer_confirmed_symbol_and_validates_currency(self):
  stock=dict(symbol='ALV.DE',exchange='XETRA',currency='EUR',name='Allianz')
  with patch('imports.matching.listing',return_value=stock) as listing:
   self.assertEqual(resolve(self.store,self.row('840400','EUR'),'revolut')['mapping'],stock)
   listing.assert_called_once_with('ALV.DE',store=self.store)

 def test_historical_exact_revolut_ticker_does_not_need_current_quote(self):
  rows=self.row('EPIX');rows[0]['day']='2025-01-01'
  with patch('imports.matching.listing') as listing,patch('imports.matching.search_stocks') as search:
   self.assertEqual(resolve(self.store,rows,'revolut')['mapping']['symbol'],'EPIX')
   listing.assert_not_called();search.assert_not_called()
  rows[0]['day']='2026-01-01'
  with patch('imports.matching.listing',side_effect=ValueError('delisted')),patch('imports.matching.search_stocks',return_value=[]):
   self.assertIn('error',resolve(self.store,rows,'revolut'))
