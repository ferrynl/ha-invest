import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from storage import Store
from cache import StateCache,memory_size
from resource_stats import ResourceMonitor,process_memory

class ResourceTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.store=Store(temp.name);self.cache=StateCache(store=self.store)
  self.store.add(dict(symbol='TEST',exchange='TEST',currency='EUR',name='Test',quantity='2',price='100',purchased_on='2024-01-02'))
 def test_streamed_compact_state_preserves_all_native_totals_and_selected_histories(self):
  from dashboard import compact
  self.store.quote('TEST','TEST','EUR','110','2026-11-01T10:00:00+00:00','test')
  full=self.store.state();small=self.store.state(compact_view=True)
  self.assertEqual(small,compact(full))
  self.assertEqual(list(self.store.position_histories(small))[0]['history'],full['positions'][0]['history'])
  self.store.add_account(dict(name='Other',broker='Test'))
  self.assertEqual(self.store.state(compact_view=True,account='2')['positions'],[])
 def test_dense_intraday_quotes_stay_out_of_overview_cache(self):
  with self.store.connect() as db:
   db.executemany('INSERT INTO quotes VALUES(NULL,?,?,?,?,?,?,?)',[('TEST','TEST','EUR',str(100+i),'2026-11-01T'+str(i%24).zfill(2)+':00:00+00:00','2026-11-01T00:00:00+00:00','test') for i in range(4000)])
  full=self.store.state();small=self.cache.derived('state-compact:all',lambda:self.store.state(compact_view=True))
  self.assertEqual(small['quotes'],[])
  self.assertEqual(small['positions'][0]['value'],full['positions'][0]['value'])
  self.assertEqual(small['portfolios'],full['portfolios'])
  with self.store.read() as db:
   observations,daily=self.store.history_inputs(db,('TEST','TEST','EUR'))
  self.assertEqual(len(observations),1)
  self.assertIn('state-compact:all',self.cache.entries)
  self.assertEqual(self.cache.derived('state-compact:all',lambda:self.fail('Should reuse cache')),small)
 def test_specialist_reports_preserve_results_using_only_required_dates(self):
  from performance import overview as performance
  from dividend_dashboard import overview as dividend
  self.store.quote('TEST','TEST','EUR','110','2026-11-01T10:00:00+00:00','test')
  self.store.add_dividend(dict(symbol='TEST',exchange='TEST',currency='EUR',amount='3',paid_on='2024-06-01'))
  full=self.store.state();small=self.store.state(compact_view=True)
  self.assertEqual(performance(self.store,full),performance(self.store,self.store.sampled_state(small,'annual')))
  self.assertEqual(dividend(full),dividend(self.store.sampled_state(small,'dividend')))
 def test_cache_reports_rejections_durations_and_current_builds(self):
  def build():
   active=self.cache.statistics()['active'];self.assertEqual(active[0]['view'],'test')
   return {'value':'x'*1000}
  with patch('cache.MEMORY_BUDGET',50):self.cache.derived('test:scope',build)
  stats=self.cache.statistics();self.assertEqual(stats['active'],[])
  self.assertEqual(stats['measurements'][0]['oversized'],1)
  self.assertEqual(stats['measurements'][0]['builds'],1)
  self.assertNotIn('scope',str(stats))
 def test_report_streaming_matches_complete_history_without_retaining_positions(self):
  from reports import combined
  self.store.quote('TEST','TEST','EUR','110','2026-11-01T10:00:00+00:00','test')
  full=combined(self.store,self.store.state(),include_history=True)
  streamed=combined(self.store,self.store.state(compact_view=True),include_history=True,stream_history=True)
  normal=lambda rows:[{k:v for k,v in p.items() if k!='history_loaded'} for p in rows]
  self.assertEqual(normal(full['positions']),normal(streamed['positions']))
  for before,after in zip(full['history']['history'],streamed['history']['history']):
   for field in ('day','value','cost','dividend','count','skipped'):self.assertEqual(before[field],after[field])
 def test_startup_prunes_only_obsolete_dashboard_caches(self):
  with self.store.connect() as db:
   db.execute("INSERT INTO api_cache VALUES('dashboard:old:state','key','{}',0,9999999999)")
   db.execute("INSERT INTO api_cache VALUES('provider','key','{}',0,9999999999)")
  self.cache.bind(self.store)
  with self.store.read() as db:names=[r[0] for r in db.execute('SELECT namespace FROM api_cache')]
  self.assertNotIn('dashboard:old:state',names);self.assertIn('provider',names)
  self.assertEqual(len(self.store.state()['purchases']),1)
 def test_stream_does_not_mix_revisions(self):
  snapshot=self.store.state(compact_view=True)
  self.store.quote('TEST','TEST','EUR','120','2026-11-01T10:00:00+00:00','test')
  with self.assertRaises(ValueError):list(self.store.position_histories(snapshot))
 def test_background_warm_only_builds_current_totals(self):
  import server,home_euro
  original=self.store.state
  def small_only(**kwargs):
   self.assertTrue(kwargs.get('compact_view'));return original(**kwargs)
  with patch.object(server,'store',self.store),patch.object(server,'state_cache',self.cache),patch.object(self.store,'state',side_effect=small_only),patch('home_euro.prepare_portfolio_rates'),patch('home_euro.overview',wraps=home_euro.overview) as calculate:
   server.warm_dashboard()
  self.assertFalse(calculate.call_args.kwargs['include_history'])
  value=self.cache.entries['home-euro-compact:all'][1]
  self.assertEqual(value['chart_status'],'pending');self.assertEqual(len(value['portfolios'][0]['history']),1)
 def test_cache_budget_counts_python_objects_and_skips_oversized_serialization(self):
  value={'rows':[{'value':str(n)} for n in range(100)]}
  self.assertGreater(memory_size(value),len(__import__('json').dumps(value))*5)
  with patch('cache.MEMORY_BUDGET',500),patch('cache.json.dumps',side_effect=AssertionError('No huge serialization')):
   self.assertEqual(self.cache.derived('large',lambda:value),value)
  self.assertNotIn('large',self.cache.entries)
 def test_stats_are_local_bounded_and_do_not_build_portfolio(self):
  backups=self.store.root/'backups';backups.mkdir();(backups/'example.sqlite3').write_bytes(b'x'*123)
  monitor=ResourceMonitor(self.store,self.cache)
  with patch.object(self.store,'state',side_effect=AssertionError('No portfolio build')):
   result=monitor.snapshot()
  self.assertEqual(result['storage']['backup_bytes'],123)
  self.assertEqual(result['storage']['rows']['purchases'],1)
  self.assertGreater(result['storage']['estimated_daily_points'],1)
  self.assertNotIn('TEST',__import__('json').dumps(result))
  self.assertIn('app_version',result['diagnostics'])
  self.assertGreater(result['storage']['database_bytes'],0)
  self.assertEqual(result['cache']['budget_bytes'],64*1024*1024)
  with patch.object(monitor,'disk',side_effect=AssertionError('Storage scan is throttled')):monitor.snapshot()
  memory=process_memory();self.assertTrue(memory is None or memory>0)
 def test_linux_memory_breakdown_uses_bytes_and_exposes_no_raw_status(self):
  from resource_stats import process_details
  with patch('resource_stats.sys.platform','linux'),patch('resource_stats.Path.read_text',return_value='VmHWM: 2048 kB\nRssAnon: 1024 kB\nRssFile: 256 kB\nVmSwap: 32 kB\nName: secret\n'):
   self.assertEqual(process_details(),dict(peak_bytes=2097152,anonymous_bytes=1048576,file_bytes=262144,swap_bytes=32768))

import test_transactions as support
class ResourceHttpTests(unittest.TestCase):
 setUp=support.TransactionHttpTests.setUp
 tearDown=support.TransactionHttpTests.tearDown
 request=support.TransactionHttpTests.request
 def test_standard_home_and_report_requests_never_build_full_state(self):
  original=self.store.state
  def small_only(*args,**kwargs):
   self.assertTrue(kwargs.get('compact_view'),'Full state constructed for standard page')
   return original(*args,**kwargs)
  with patch.object(self.store,'state',side_effect=small_only):
   for path in ('/api/state?compact=1','/api/home/euro?compact=1','/api/home/euro/history','/api/stocks','/api/reports/combined','/api/reports/combined?history=1','/api/reports/history','/api/reports/performance','/api/dividends/overview','/api/dividends/overview?combined=1'):
    self.assertEqual(self.request(path)[0],200,path)
 def test_admin_authorization_is_checked_on_every_resource_request(self):
  self.auth.enable('owner','Long-test-password-2026')
  self.assertEqual(self.request('/api/resource-stats')[0],401)
  owner=self.auth.login('owner','Long-test-password-2026','test')
  self.assertEqual(self.request('/api/resource-stats',token=owner)[0],200)
  self.auth.save_user(dict(username='reader',password='Long-test-password-2026',role='basic',active=True))
  reader=self.auth.login('reader','Long-test-password-2026','test')
  self.assertEqual(self.request('/api/resource-stats',token=reader)[0],403)
