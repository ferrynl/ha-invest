import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'portfolio/app'))
sys.path.insert(0,str(ROOT/'scripts'))
from security import Auth
from storage import Store
from cache import StateCache
from web import make_handler
from i18n import localize,translate
from check_translations import check

class LanguageTests(unittest.TestCase):
    def test_all_interface_text_has_three_translations(self):self.assertEqual(check(),[])

    def test_only_interface_fields_are_translated(self):
        value={'error':'Ongeldige aanvraag.','message':'Ongeldige aanvraag. · Log-ID ABC-123','positions':[{'name':'Aandeel','account_name':'Instellingen','note':'Ongeldige aanvraag.','reason':'Geen actuele wisselkoers voor de verwachting'}]}
        result=localize(value,'es')
        self.assertEqual(result['error'],'Solicitud no válida.')
        self.assertEqual(result['message'],'Solicitud no válida. · Log-ID ABC-123')
        self.assertEqual(result['positions'][0]['name'],'Aandeel')
        self.assertEqual(result['positions'][0]['note'],'Ongeldige aanvraag.')
        self.assertEqual(result['positions'][0]['account_name'],'Instellingen')
        self.assertEqual(result['positions'][0]['reason'],'Sin tipo de cambio actual para la previsión')
        self.assertEqual(value['error'],'Ongeldige aanvraag.')
        self.assertEqual(translate('Ongeldige aanvraag.','fr'),'Ongeldige aanvraag.')

    def test_language_is_persistent_and_account_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);auth=Auth(store)
            self.assertEqual(auth.user('')['language'],'')
            auth.set_language(auth.user(''),'es')
            self.assertEqual(Auth(Store(folder)).user('')['language'],'es')
            auth.enable('owner','Long-test-password-2026')
            auth.save_user({'username':'reader','password':'Long-test-password-2026','role':'basic','active':True})
            owner=auth.login('owner','Long-test-password-2026','test')
            reader=auth.login('reader','Long-test-password-2026','test')
            auth.set_language(auth.user(owner),'en');auth.set_language(auth.user(reader),'nl')
            restarted=Auth(Store(folder))
            self.assertEqual(restarted.user(owner)['language'],'en')
            self.assertEqual(restarted.user(reader)['language'],'nl')
            with self.assertRaises(ValueError):auth.set_language(auth.user(reader),'fr')
            self.assertEqual(restarted.user(owner)['language'],'en')

    def test_language_endpoint_requires_auth_and_csrf_but_allows_basic(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);auth=Auth(store);auth.enable('owner','Long-test-password-2026')
            auth.save_user({'username':'reader','password':'Long-test-password-2026','role':'basic','active':True})
            token=auth.login('reader','Long-test-password-2026','test');csrf=auth.user(token)['csrf']
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(store,auth,StateCache(),{},900,threading.Lock(),threading.Event()))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            def request(language,session='',protection=''):
                connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)
                try:
                    connection.request('POST','/api/account/language',json.dumps({'language':language,'id':1}),{'Content-Type':'application/json','X-Portfolio-Request':'1','Cookie':'homeinvest_session='+session,'X-CSRF-Token':protection,'X-HomeInvest-Language':'es'})
                    response=connection.getresponse();return response.status,json.loads(response.read())
                finally:connection.close()
            try:
                self.assertEqual(request('en')[0],401)
                self.assertEqual(request('en',token)[0],403)
                self.assertEqual(request('es',token,csrf),(200,{'language':'es'}))
                self.assertEqual(request('fr',token,csrf)[0],400)
                self.assertEqual(auth.user(token)['language'],'es')
                with store.read() as db:self.assertEqual(db.execute("SELECT language FROM users WHERE username='owner'").fetchone()[0],'')
            finally:server.shutdown();server.server_close();worker.join()
