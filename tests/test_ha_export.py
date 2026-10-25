import http.client
import importlib
import os
import json
import sys
import tempfile
import threading
import unittest
from datetime import date,timedelta
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from ha_export import build,configuration,overview,make_export_handler,valid_token
from storage import Store
from cache import StateCache
from security import Auth
from web import make_handler


class ExportTests(unittest.TestCase):
    def position(self,currency,value,quantity='1'):
        return dict(currency=currency,value=value,quantity=quantity,quote={'quoted_at':'2026-10-24T12:00:00+00:00'})

    def test_all_accounts_and_currencies_are_summed_with_decimal(self):
        snapshot=dict(data_revision=7,positions=[self.position('EUR','100.01'),self.position('USD','110'),self.position('USD','220'),self.position('GBX','20000')])
        rates=[dict(base='EUR',quote='USD',day='2026-10-23',rate='1.1'),dict(base='EUR',quote='GBP',day='2026-10-23',rate='0.8')]
        result=build(snapshot,rates,date(2026,10,25))
        self.assertEqual(result['currencies']['USD']['value'],'330')
        self.assertEqual(Decimal(result['total_eur']['value']),Decimal('650.01'))
        self.assertEqual(result['total_eur']['positions'],4)
        self.assertTrue(result['total_eur']['complete'])
        self.assertEqual(result['total_eur']['fx_dates']['USD'],'2026-10-23')
        self.assertNotIn('positions',result)

    def test_missing_quotes_and_fx_never_become_a_false_total(self):
        snapshot=dict(data_revision=1,positions=[self.position('EUR','10'),self.position('USD',None),self.position('GBP','20')])
        result=build(snapshot,[],date(2026,10,25))
        self.assertEqual(result['currencies']['EUR']['value'],'10')
        self.assertIsNone(result['currencies']['USD']['value'])
        self.assertIsNone(result['total_eur']['value'])
        self.assertEqual(result['total_eur']['known_value'],'10')
        self.assertEqual(result['total_eur']['missing_quotes'],1)
        self.assertEqual(result['total_eur']['missing_fx'],1)

    def test_only_recent_non_future_positive_rates_are_used(self):
        snapshot=dict(data_revision=1,positions=[self.position('USD','100')])
        for day,rate in [('2026-10-26','1'),('2026-10-17','1'),('2026-10-25','0')]:
            result=build(snapshot,[dict(base='EUR',quote='USD',day=day,rate=rate)],date(2026,10,25))
            self.assertIsNone(result['total_eur']['value'])
        result=build(snapshot,[dict(base='EUR',quote='USD',day='2026-10-18',rate='2')],date(2026,10,25))
        self.assertEqual(result['total_eur']['value'],'50')

    def test_closed_and_empty_portfolios_are_zero_without_requiring_fx(self):
        for positions in [[],[self.position('USD','0','0')]]:
            result=build(dict(data_revision=1,positions=positions),[])
            self.assertEqual(result['total_eur']['value'],'0')
            self.assertTrue(result['total_eur']['complete'])

    def test_configuration_uses_one_request_and_never_guesses_unknown_as_zero(self):
        result=configuration(['USD','EUR','GBX','bad"currency'])
        self.assertEqual(result.count('resource:'),1)
        self.assertEqual(result.count('unique_id:'),4)
        self.assertIn('!secret home_invest_authorization',result)
        self.assertIn("else 'unknown'",result)
        self.assertNotIn('float(0)',result)
        self.assertNotIn('bad',result)

    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(tmp.name);self.cache=StateCache(store=self.store)

    def serve(self,handler):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def close():server.shutdown();server.server_close();worker.join()
        self.addCleanup(close)
        return server

    def request(self,server,method='GET',path='/api/ha/state',token=None):
        client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        try:
            client.request(method,path,headers={'Authorization':'Bearer '+token} if token is not None else {})
            response=client.getresponse();return response.status,json.loads(response.read()),dict(response.getheaders())
        finally:client.close()

    def test_export_requires_valid_bearer_and_cannot_read_or_mutate_dashboard(self):
        token='test-key-'+'x'*32;server=self.serve(make_export_handler(self.store,self.cache,token))
        for invalid in [None,'wrong',token+'x']:
            self.assertEqual(self.request(server,token=invalid)[0],401)
        status,result,headers=self.request(server,token=token)
        self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertNotIn(token,json.dumps(result));self.assertNotIn('Set-Cookie',headers)
        for path in ['/','/api/state','/api/backup','/api/users','/api/settings']:
            self.assertEqual(self.request(server,path=path,token=token)[0],404)
        for method in ['POST','PUT','PATCH','DELETE']:
            self.assertEqual(self.request(server,method=method,token=token)[0],405)

    def test_disabled_or_short_token_never_opens_export(self):
        for token in ['', 'short','x'*31,'x'*129,'x'*31+' ',None]:self.assertFalse(valid_token(token))
        server=self.serve(make_export_handler(self.store,self.cache,''))
        self.assertEqual(self.request(server,token='')[0],401)

    def test_export_is_durable_offline_and_changes_after_quote_update(self):
        self.store.add(dict(symbol='TEST',exchange='AMS',currency='EUR',name='Test',quantity='2',price='10',purchased_on=date.today().isoformat()))
        self.store.quote('TEST','AMS','EUR','11','2026-10-24T12:00:00+00:00','Test')
        with patch('forex.load_json',side_effect=AssertionError('No external requests')):
            result=overview(self.store,self.cache);self.assertEqual(result['total_eur']['value'],'22')
            restarted=Store(self.store.root)
            with patch.object(restarted,'state',side_effect=AssertionError('Should read database cache')):
                self.assertEqual(overview(restarted,StateCache(store=restarted)),result)
            self.store.quote('TEST','AMS','EUR','12','2026-10-25T12:00:00+00:00','Test')
            self.assertEqual(overview(self.store,self.cache)['total_eur']['value'],'24')

    def test_setup_requires_admin_and_never_returns_token(self):
        auth=Auth(self.store);token='secret'+'x'*32
        server=self.serve(make_handler(self.store,auth,self.cache,{},900,threading.Lock(),threading.Event(),{'home_assistant_token':token}))
        status,result,_=self.request(server,path='/api/home-assistant')
        self.assertEqual(status,200);self.assertTrue(result['enabled']);self.assertNotIn(token,json.dumps(result))
        with patch.object(auth,'user',return_value={'role':'basic','username':'test'}):
            self.assertEqual(self.request(server,path='/api/home-assistant')[0],403)
        with patch.object(auth,'user',return_value=None):
            self.assertEqual(self.request(server,path='/api/home-assistant')[0],401)

    def test_server_starts_export_only_with_valid_key_and_survives_port_conflict(self):
        with patch.dict(os.environ,{'DATA_DIR':str(self.store.root)}):
            module=importlib.import_module('server')
        with patch.object(module,'options',{'home_assistant_token':''}),patch.object(module,'ThreadingHTTPServer') as create:
            self.assertIsNone(module.start_export());create.assert_not_called()
        with patch.object(module,'options',{'home_assistant_token':'x'*32}),patch.object(module,'ThreadingHTTPServer',side_effect=OSError('busy')):
            with self.assertLogs(level='ERROR'):self.assertIsNone(module.start_export())
        with patch.object(module,'options',{'home_assistant_token':'x'*32}),patch.object(module,'store',self.store),patch.object(module,'state_cache',self.cache),patch.dict(os.environ,{'BIND':'127.0.0.1','HA_EXPORT_PORT':'0'}):
            http=module.start_export()
            try:self.assertEqual(self.request(http,token='x'*32)[0],200)
            finally:http.shutdown();http.server_close()


if __name__=='__main__':unittest.main()
