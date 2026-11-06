import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from cache import StateCache
from dashboard import compact,stock_movers
from restore import restore_backup
from forex import prepare_rates,save_rates
from datetime import date,timedelta

class DashboardCacheTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(tmp.name)
  self.store.add(dict(symbol='TEST',exchange='NYSE',currency='USD',name='Example',quantity='2',price='100',purchased_on='2026-01-02'))
  self.cache=StateCache(0,store=self.store)
 def test_stock_movers_compare_periods_and_scope_to_selected_broker(self):
  self.store.add_account(dict(name='Other',broker='Other'))
  other=self.store.state(compact_view=True)['accounts'][-1]['id']
  self.store.add(dict(account_id=other,symbol='TEST',exchange='NYSE',currency='USD',name='Example',quantity='1',price='100',purchased_on='2026-01-02'))
  self.store.add(dict(account_id=other,symbol='LOSS',exchange='NYSE',currency='USD',name='Loser',quantity='1',price='100',purchased_on='2026-01-02'))
  for symbol,prices in [('TEST',('100','125','150')),('LOSS',('100','100','80'))]:
   self.store.save_history(symbol,'NYSE','USD','2026-01-02',[
    dict(day='2026-01-05',price=prices[0]),dict(day='2026-01-09',price=prices[1])])
   self.store.quote(symbol,'NYSE','USD',prices[2],'2026-01-12T18:00:00+00:00','test')
  snapshot=self.store.state(compact_view=True)
  today=date(2026,1,12)
  day=stock_movers(self.store,snapshot,'all',1,today)
  self.assertEqual(day['day'],'2026-01-12')
  self.assertEqual([(p['symbol'],float(p['change'])) for p in day['gainers']],[('TEST',20)])
  self.assertEqual([p['symbol'] for p in day['losers']],['LOSS'])
  week=stock_movers(self.store,snapshot,str(snapshot['accounts'][0]['id']),7,today)
  self.assertEqual([(p['symbol'],float(p['change'])) for p in week['gainers']],[('TEST',50)])
  self.assertEqual(week['losers'],[])
  self.assertEqual(stock_movers(self.store,snapshot,'all',30,today)['gainers'],[])
 def test_snapshot_survives_ram_expiry_and_restart_without_rebuilding(self):
  loader=Mock(wraps=self.store.state);first=self.cache.get(loader);self.assertEqual(self.cache.get(loader),first);loader.assert_called_once()
  restarted=StateCache(0,store=Store(self.store.root))
  self.assertEqual(restarted.get(Mock(side_effect=AssertionError('No rebuild'))),first)
  with self.store.connect() as db:
   namespaces=[r[0] for r in db.execute("SELECT namespace FROM api_cache WHERE namespace LIKE 'dashboard:%'")]
  self.assertEqual(len(namespaces),1)
 def test_direct_quote_and_ledger_mutations_invalidate_persisted_views(self):
  first=self.cache.get(self.store.state)
  self.store.quote('TEST','NYSE','USD','110','2026-10-24T00:00:00+00:00','test')
  second=self.cache.get(self.store.state);self.assertNotEqual(second['data_revision'],first['data_revision']);self.assertEqual(second['positions'][0]['value'],'220')
  self.store.add_dividend(dict(symbol='TEST',exchange='NYSE',currency='USD',amount='5',paid_on='2026-01-03'))
  self.assertEqual(self.cache.get(self.store.state)['positions'][0]['dividend'],'5')
 def test_cache_writes_and_session_activity_do_not_invalidate_financial_snapshots(self):
  first=self.cache.get(self.store.state)
  with self.store.connect() as db:
   db.execute("INSERT INTO api_cache VALUES('test','key','{}',0,1)")
   db.execute("DELETE FROM auth_sessions")
  loader=Mock(side_effect=AssertionError('Unrelated writes must not rebuild'))
  self.assertEqual(self.cache.get(loader),first)
 def test_restore_discards_derived_snapshots_and_preserves_real_financial_rows(self):
  self.cache.get(self.store.state);backup=self.store.backup().read_bytes()
  self.store.add(dict(symbol='OTHER',exchange='NYSE',currency='USD',name='Other',quantity='1',price='50',purchased_on='2026-01-02'))
  self.cache.get(self.store.state);restore_backup(self.store,backup)
  with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM api_cache WHERE namespace LIKE 'dashboard:%'").fetchone()[0],0)
  self.assertEqual([p['symbol'] for p in self.cache.get(self.store.state)['positions']],['TEST'])
 def test_corrupt_snapshot_is_rebuilt_and_slots_do_not_leak_between_databases(self):
  self.cache.get(self.store.state)
  with self.store.connect() as db:db.execute("UPDATE api_cache SET payload='not-valid' WHERE namespace LIKE 'dashboard:%'")
  fresh=StateCache(store=self.store);self.assertEqual(len(fresh.get(self.store.state)['positions']),1)
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);other=Store(tmp.name)
  self.cache.bind(other);self.assertEqual(self.cache.get(other.state)['positions'],[])
 def test_compact_payload_retains_total_graph_but_omits_unselected_daily_histories(self):
  for index in range(8):self.store.add(dict(symbol='EX'+str(index),exchange='NYSE',currency='USD',name='Example '+str(index),quantity='1',price='100',purchased_on='2024-01-02'))
  snapshot=self.cache.get(self.store.state);small=compact(snapshot)
  self.assertTrue(all(len(p['history'])==1 and p['history_loaded'] is False for p in small['positions']))
  self.assertEqual(small['portfolios'],snapshot['portfolios'])
  self.assertLess(len(json.dumps(small)),len(json.dumps(snapshot))*.25)
 def test_fx_fetches_only_the_missing_recent_range(self):
  save_rates(self.store,[dict(base='EUR',quote='USD',date='2020-01-02',rate='1.1')],date(2020,1,2))
  with patch('forex.load_json',return_value=[dict(base='EUR',quote='USD',date='2026-10-23',rate='1.2')]) as network:
   prepare_rates(self.store,[('USD','EUR','2020-01-02'),('USD','EUR','2026-10-23')])
  self.assertEqual(network.call_count,1);self.assertIn('from=2026-10-16',network.call_args.args[0]);self.assertNotIn('2020',network.call_args.args[0])
 def test_cached_read_is_not_blocked_by_a_provider_holding_the_writer_lock(self):
  import threading
  self.cache.get(self.store.state);held=threading.Event();release=threading.Event();finished=threading.Event()
  def provider():
   with self.store.lock:held.set();release.wait(3)
  def reader():
   self.cache.get(self.store.state);finished.set()
  writer=threading.Thread(target=provider);writer.start();self.assertTrue(held.wait(1))
  request=threading.Thread(target=reader);request.start()
  try:self.assertTrue(finished.wait(1),'Cached Home waited for an unrelated provider request')
  finally:release.set();writer.join();request.join()
 def test_snapshot_built_during_a_mutation_is_not_saved_as_current(self):
  def changing():
   old=self.store.state();self.store.quote('TEST','NYSE','USD','110','2026-10-24T00:00:00+00:00','test');return old
  old=self.cache.get(changing)
  current=self.cache.get(self.store.state)
  self.assertGreater(current['data_revision'],old['data_revision']);self.assertEqual(current['positions'][0]['value'],'220')
 def test_day_change_rebuilds_time_dependent_overview(self):
  self.cache.get(self.store.state)
  with patch('cache.date') as clock:
   clock.today.return_value=date.today()+timedelta(days=1)
   loader=Mock(wraps=self.store.state);self.cache.get(loader);loader.assert_called_once()
 def test_oversized_snapshots_are_not_retained_or_serialized(self):
  with patch('cache.MEMORY_BUDGET',1):
   first=self.cache.get(self.store.state);self.assertEqual(self.cache.entries,{})
   with self.store.read() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM api_cache WHERE namespace LIKE 'dashboard:%'").fetchone()[0],0)
   self.assertEqual(self.cache.get(self.store.state),first)

 def test_slow_report_does_not_block_cached_home_and_builds_once_per_slot(self):
  import threading
  self.cache.get(self.store.state);started=threading.Event();release=threading.Event();read_done=threading.Event();results=[];errors=[];calls=[]
  def slow():
   calls.append(1);started.set();release.wait(3);return {'report':True}
  def report():
   try:results.append(self.cache.derived('slow-report',slow))
   except Exception as error:errors.append(error)
  def home():
   try:self.cache.get(self.store.state)
   except Exception as error:errors.append(error)
   finally:read_done.set()
  first=threading.Thread(target=report);second=threading.Thread(target=report);first.start();self.assertTrue(started.wait(1));second.start();reader=threading.Thread(target=home);reader.start()
  try:self.assertTrue(read_done.wait(1),'A report held the shared dashboard cache lock')
  finally:release.set();first.join();second.join();reader.join()
  self.assertEqual(errors,[]);self.assertEqual(len(calls),1);self.assertEqual(results,[{'report':True},{'report':True}])
 def test_invalidated_inflight_build_is_not_saved_as_current(self):
  def invalidated():
   self.cache.invalidate();return {'obsolete':True}
  self.cache.derived('report',invalidated)
  self.assertNotIn('report',self.cache.entries)
  self.assertEqual(self.cache.derived('report',lambda:{'fresh':True}),{'fresh':True})

import test_transactions as support
class DashboardCacheHttpTests(unittest.TestCase):
 def test_euro_summary_and_chart_are_separate_and_reuse_small_summary_state(self):
  from home_euro import daily_values
  self.request('/api/state?compact=1')
  with patch('home_euro.daily_values',wraps=daily_values) as replay:
   code,summary=self.request('/api/home/euro?compact=1')
  self.assertEqual(code,200);self.assertEqual(summary['chart_status'],'pending')
  self.assertEqual(len(summary['portfolios'][0]['history']),1)
  self.assertTrue(all(call.kwargs.get('summary_only') for call in replay.call_args_list))
  with patch.object(self.cache,'get',side_effect=AssertionError('Summary must reuse compact state')):
   self.cache.entries.pop('home-euro-compact:all',None)
   with self.store.connect() as db:db.execute("DELETE FROM api_cache WHERE namespace LIKE 'dashboard:%:home-euro-compact:all'")
   self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
  code,chart=self.request('/api/home/euro/history')
  self.assertEqual(code,200);self.assertNotIn('positions',chart)
  self.assertGreater(len(chart['portfolios'][0]['history']),1)
  self.assertEqual(chart['data_revision'],summary['data_revision'])
 def test_euro_chart_retries_revision_change_and_isolates_invalid_history(self):
  from storage import PortfolioRevisionChanged
  import home_euro
  self.request('/api/state?compact=1')
  original=home_euro.overview
  attempts=[]
  def race(*args,**kwargs):
   attempts.append(kwargs['expected_revision'])
   if len(attempts)==1:raise PortfolioRevisionChanged()
   return original(*args,**kwargs)
  histories=self.store.position_histories
  def damaged(*args,**kwargs):
   for position in histories(*args,**kwargs):
    yield {**position,'symbol':'BAD','history':[]}
    yield position
  with patch('home_euro.overview',side_effect=race),patch.object(self.store,'position_histories',side_effect=damaged):
   code,chart=self.request('/api/home/euro/history')
  self.assertEqual(code,200)
  self.assertEqual(len(attempts),2)
  self.assertEqual([row['symbol'] for row in chart['excluded']],['BAD'])
  self.assertGreater(len(chart['portfolios'][0]['history']),1)

 def test_slow_chart_does_not_block_summary_request(self):
  import threading
  import home_euro
  self.request('/api/state?compact=1');started=threading.Event();release=threading.Event();result=[]
  original=home_euro.overview
  def slow(*args,**kwargs):
   if kwargs.get('include_history',True):started.set();release.wait(4)
   return original(*args,**kwargs)
  with patch('home_euro.overview',side_effect=slow):
   worker=threading.Thread(target=lambda:result.append(self.request('/api/home/euro/history')[0]));worker.start()
   try:
    self.assertTrue(started.wait(1));self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
    self.assertFalse(release.is_set())
   finally:release.set();worker.join()
  self.assertEqual(result,[200])
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_home_and_euro_load_offline_and_do_not_rebuild_unchanged_snapshots(self):
  with patch('forex.load_json',side_effect=AssertionError('No network from Home')) as network,patch('home_euro.prepare_rates') as rates:
   code,state=self.request('/api/state?compact=1');self.assertEqual(code,200)
   self.assertTrue(state['compact']);self.assertEqual(len(state['positions'][0]['history']),1)
   self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
   with patch.object(self.store,'state',side_effect=AssertionError('No rebuild')):
    self.assertEqual(self.request('/api/state?compact=1')[0],200);self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
   network.assert_not_called();rates.assert_not_called()
 def test_compact_views_are_cached_without_retaining_full_euro_histories(self):
  self.store.quote('ASML.AS','AMSTERDAM','EUR','110','2026-10-24T00:00:00+00:00','test')
  self.assertEqual(self.request('/api/state?compact=1')[0],200)
  self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
  self.assertIn('state-compact:all',self.cache.entries)
  result=self.cache.entries['home-euro-compact:all'][1]
  self.assertTrue(all(len(p['history'])==1 for p in result['positions']))
  self.assertNotIn('home-euro:all',self.cache.entries)
  with patch.object(self.store,'state',side_effect=AssertionError('Overview must use the small cached view')):
   self.assertEqual(self.request('/api/state?compact=1')[0],200)
   self.assertEqual(self.request('/api/home/euro?compact=1')[0],200)
 def test_history_is_limited_scoped_and_authenticated_even_when_cached(self):
  _,state=self.request('/api/state?compact=1');p=state['positions'][0]
  selection={k:p[k] for k in ('account_id','symbol','exchange','currency')}
  path='/api/home/history?'+urlencode(dict(account_id='all',positions=json.dumps([selection])))
  code,result=self.request(path);self.assertEqual(code,200);self.assertGreater(len(result['histories'][0]['history']),1)
  self.assertEqual(self.request('/api/home/history?'+urlencode(dict(positions=json.dumps([selection]*7))))[0],400)
  self.store.add_account(dict(name='Other',broker='Other'))
  self.assertEqual(self.request(path.replace('account_id=all','account_id=2'))[0],400)
  self.auth.enable('owner','Long-test-password-2026');self.assertEqual(self.request(path)[0],401)
 def test_authenticated_and_ha_home_reads_do_not_wait_for_provider_lock(self):
  import threading
  for enabled in (False,True):
   token=''
   if enabled:
    self.auth.enable('owner','Long-test-password-2026');token=self.auth.login('owner','Long-test-password-2026','test')
   self.cache.get(self.store.state)
   held=threading.Event();release=threading.Event();finished=threading.Event();results=[]
   def provider():
    with self.store.lock:held.set();release.wait(3)
   def reader():
    results.append(self.request('/api/state?compact=1',token=token)[0]);finished.set()
   writer=threading.Thread(target=provider);writer.start();self.assertTrue(held.wait(1))
   request=threading.Thread(target=reader);request.start()
   try:self.assertTrue(finished.wait(1),'Session validation or Home waited for the provider lock')
   finally:release.set();writer.join();request.join()
   self.assertEqual(results,[200])
