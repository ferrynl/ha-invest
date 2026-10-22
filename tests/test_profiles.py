import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from instruments import save_categories,details
from profiles import enrich_categories,normalize_profile,EmbeddedProfile,ProfileError
from restore import restore_backup
from diagnostics import read_logs
from migrations import MIGRATIONS

KEY=('ASML.AS','AMSTERDAM','EUR')
STOCK=dict(symbol=KEY[0],exchange=KEY[1],currency=KEY[2],name='ASML')
def payload(**profile):
 return {'quoteSummary':{'result':[{'price':{'symbol':'ASML.AS','exchange':'AMS','currency':'EUR','quoteType':'EQUITY'},'assetProfile':{'sector':'Technology','country':'Netherlands',**profile}}],'error':None}}

class ProfileTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
  self.store.add(dict(**STOCK,quantity='2',price='100',purchased_on='2026-10-01'))
 def test_api_fills_once_across_accounts_restart_and_backup_restore(self):
  self.store.add_account(dict(name='Broker',broker='Trading 212'))
  self.store.add(dict(**STOCK,account_id=2,quantity='1',price='100',purchased_on='2026-10-01'))
  with patch('profiles._download_profile',return_value=payload(companyOfficers=[{'name':'do-not-cache'}])) as api:
   self.assertTrue(enrich_categories(self.store,KEY));self.assertFalse(enrich_categories(self.store,KEY))
   self.assertFalse(enrich_categories(Store(self.tmp.name),KEY));api.assert_called_once()
  result=details(self.store,STOCK);self.assertEqual(result['categories']['sector'],'Technologie');self.assertEqual(result['categories']['country'],'Nederland');self.assertEqual(result['categories']['asset_type'],'Aandeel');self.assertEqual(result['category_sync']['status'],'complete')
  with self.store.connect() as db:cached=db.execute("SELECT payload FROM api_cache WHERE namespace='yahoo-profile-v1'").fetchone()[0]
  self.assertNotIn('do-not-cache',cached);self.assertEqual(set(json.loads(cached)),{'sector','country','asset_type'})
  restore_backup(self.store,self.store.backup().read_bytes())
  with patch('profiles._download_profile') as api:self.assertFalse(enrich_categories(self.store,KEY));api.assert_not_called()
 def test_manual_fields_and_concurrent_edits_win_over_api(self):
  save_categories(self.store,dict(**STOCK,sector='Mijn sector',category='Groei'))
  def fetch(symbol):
   save_categories(self.store,dict(**STOCK,sector='Mijn sector',country='Mijn land',category='Groei'))
   return payload()
  with patch('profiles._download_profile',side_effect=fetch):self.assertTrue(enrich_categories(self.store,KEY))
  categories=details(self.store,STOCK)['categories'];self.assertEqual(categories['sector'],'Mijn sector');self.assertEqual(categories['country'],'Mijn land');self.assertEqual(categories['asset_type'],'Aandeel');self.assertEqual(categories['category'],'Groei')
  save_categories(self.store,dict(**STOCK,sector='Mijn sector',country='',asset_type='Aandeel',category='Groei'))
  with self.store.connect() as db:db.execute('DELETE FROM instrument_category_sync')
  with patch('profiles._download_profile',return_value=payload()):enrich_categories(self.store,KEY)
  categories=details(self.store,STOCK)['categories'];self.assertEqual(categories['country'],'');self.assertEqual(categories['manual_country'],1)
 def test_partial_profile_keeps_missing_country_empty_and_is_not_refetched(self):
  value=payload(sector='',country='');value['quoteSummary']['result'][0]['price']['quoteType']='ETF'
  with patch('profiles._download_profile',return_value=value) as api:
   enrich_categories(self.store,KEY);enrich_categories(Store(self.tmp.name),KEY);api.assert_called_once()
  result=details(self.store,STOCK);self.assertEqual(result['categories']['asset_type'],'ETF');self.assertEqual(result['categories']['country'],'');self.assertEqual(result['category_sync']['status'],'partial')
 def test_wrong_listing_or_currency_is_rejected_without_writing_categories(self):
  for field,value in [('symbol','OTHER'),('currency','USD'),('exchange','NYQ')]:
   raw=payload();raw['quoteSummary']['result'][0]['price'][field]=value
   with self.subTest(field=field),self.assertRaises(ProfileError):normalize_profile(raw,KEY)
  with patch('profiles._download_profile',return_value={'quoteSummary':{'result':[]}}):self.assertFalse(enrich_categories(self.store,KEY))
  self.assertEqual(details(self.store,STOCK)['categories']['sector'],'')
 def test_http_rate_limit_backoff_and_logs_never_expose_session_material(self):
  error=HTTPError('https://query2.finance.yahoo.com/path?crumb=private-crumb',429,'private-message',{'Retry-After':'3600','Set-Cookie':'private-cookie'},io.BytesIO(b'private-body'))
  with patch('profiles._download_profile',side_effect=error) as api:
   self.assertFalse(enrich_categories(self.store,KEY));self.assertFalse(enrich_categories(self.store,KEY));api.assert_called_once()
  result=details(self.store,STOCK);self.assertEqual(result['category_sync']['status'],'retry');self.assertEqual(result['category_sync']['error_code'],'http_429')
  logs=json.dumps(read_logs(self.store));self.assertIn('http_429',logs)
  for secret in ['private-crumb','private-cookie','private-body','private-message']:self.assertNotIn(secret,logs)
  with self.store.connect() as db:
   db.execute("UPDATE instrument_category_sync SET retry_at='2000-01-01T00:00:00+00:00'");db.execute("DELETE FROM api_cache WHERE namespace='provider-cooldown'")
  with patch('profiles._download_profile',return_value=payload()):self.assertTrue(enrich_categories(self.store,KEY))
 def test_embedded_api_parser_requires_exact_host_ticker_and_status(self):
  def html(symbol,host='query1.finance.yahoo.com',status=200):
   wrapper=json.dumps({'status':status,'body':json.dumps(payload())})
   return '<script type="application/json" data-sveltekit-fetched data-url="https://'+host+'/v10/finance/quoteSummary/'+symbol+'?modules=assetProfile">'+wrapper+'</script>'
  for document in [html('OTHER'),html('ASML.AS','attacker.test'),html('ASML.AS',status=401)]:
   parser=EmbeddedProfile('ASML.AS');parser.feed(document);self.assertIsNone(parser.payload)
  parser=EmbeddedProfile('ASML.AS');parser.feed(html('ASML.AS'));self.assertEqual(normalize_profile(parser.payload,KEY)['country'],'Nederland')
 def test_legacy_backup_marks_existing_fields_manual_and_sync_backup_is_validated(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'legacy.sqlite3'
   with closing(sqlite3.connect(path)) as db:
    for version in range(1,14):
     for sql in MIGRATIONS[version]:db.execute(sql)
    db.execute('PRAGMA user_version=13')
    db.execute("INSERT INTO instrument_categories VALUES('ASML.AS','AMSTERDAM','EUR','Eigen sector','','','Groei','2026-10-01T00:00:00+00:00')")
    db.execute("INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES('ASML.AS','AMSTERDAM','ASML','2','100','EUR','2026-10-01','2026-10-01T00:00:00+00:00')")
    db.commit()
   restore_backup(self.store,path.read_bytes())
  with patch('profiles._download_profile',return_value=payload()):enrich_categories(self.store,KEY)
  value=details(self.store,STOCK)['categories'];self.assertEqual(value['sector'],'Eigen sector');self.assertEqual(value['country'],'Nederland');self.assertEqual(value['category'],'Groei')
  with self.store.connect() as db:db.execute("UPDATE instrument_category_sync SET retry_at='invalid'")
  with self.assertRaises(ValueError):restore_backup(self.store,self.store.backup().read_bytes())
 def test_background_refresh_automatically_backfills_existing_holdings(self):
  import server
  from cache import StateCache
  with patch.object(server,'store',self.store),patch.object(server,'state_cache',StateCache()),patch.object(server,'fetch_quote',return_value=('140','2026-10-22T10:00:00+00:00')),patch.object(server,'fetch_history',return_value=[dict(day='2026-10-01',price='100')]),patch('server.time.sleep'),patch('profiles._download_profile',return_value=payload()) as api:
   server.refresh();server.refresh();api.assert_called_once()
  self.assertEqual(details(self.store,STOCK)['category_sync']['status'],'complete')
