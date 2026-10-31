"""HTTP boundary: authorization is enforced here, independent of page visibility."""
import gzip
import hashlib
import hmac
import json
import re
import sqlite3
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from provider import search_stocks,listing as resolve_listing
from restore import restore_backup
from security import verify_password,SESSION_TTL
from version import APP_VERSION
from i18n import localize,LANGUAGES
from updates import check_updates
from feedback import overview as feedback_overview
from imports import ADAPTERS
from imports.service import preview as import_preview,open_preview
from imports.partial import commit_partial,list_issues,resolve_issue
from imports.matching import resolve_instrument
from imports.registry import discover as mapping_list,edit as mapping_edit
from imports import trading212_api
import transactions
import instruments
from history import portfolio_values
from diagnostics import read_logs,record,DiagnosticError,ActionError
from forex import overview as fx_overview,convert as fx_convert,history as fx_history

def make_handler(store,auth,cache,status,interval,refresh_lock,refresh_requested,integration_options=None,enable_demo=True):
    cache.bind(store)
    def home_euro(account,compact_view=False):
        from home_euro import overview
        def build():
            snapshot=cache.get(store.state)
            result={**overview(store,snapshot,account,fetch_rates=False),'data_revision':snapshot['data_revision']}
            if compact_view:
                from dashboard import compact
                result=compact(result)
            return result
        return cache.derived(('home-euro-compact:' if compact_view else 'home-euro:')+str(account),build)
    static=Path(__file__).parent/'static'
    assets={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/reports.css':('reports.css','text/css')}
    assets['/fonts/Roboto.ttf']=('fonts/Roboto.ttf','font/ttf')
    assets['/world-countries.json']=('world-countries.json','application/json; charset=utf-8')
    for flag in (static/'flags').glob('*.svg'):assets['/flags/'+flag.name]=('flags/'+flag.name,'image/svg+xml')
    for name in ('feedback','i18n','translations','loading','dashboard-layout','home','app','pages','chart','chart-view','access','imports','logs','currencies','import-mappings','import-issues','transactions','popups','table-filters','stock-detail','category-status','dividends','stocks','reports','report-charts','conversions','performance'):
        assets['/'+name+'.js']=(name+'.js','text/javascript; charset=utf-8')
    assets['/country-map.js']=('country-map.js','text/javascript; charset=utf-8')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def token(self):
            try:
                cookie=SimpleCookie(self.headers.get('Cookie',''))
                return cookie['homeinvest_session'].value if 'homeinvest_session' in cookie else ''
            except Exception:return ''
        def cookie(self,token):
            path=self.headers.get('X-Ingress-Path','/')
            if not re.fullmatch(r'/[a-zA-Z0-9_./-]*',path):path='/'
            path=path.rstrip('/')+'/'
            secure=self.headers.get('X-Forwarded-Proto','').split(',')[0].strip()=='https' or self.headers.get('Origin','').startswith('https://')
            return f'homeinvest_session={token}; Path={path}; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL if token else 0}'+('; Secure' if secure else '')
        def respond(self,content,code=200,kind='application/json',filename=None,cookie=None,etag=False,public=False):
            if kind=='application/json':
                language=self.headers.get('X-HomeInvest-Language','nl')
                content=json.dumps(localize(content,language),separators=(',',':')).encode()
            compressible=public or (self.command=='GET' and kind=='application/json' and urlsplit(self.path).path not in ('/api/session','/api/users'))
            compressed=compressible and 'gzip' in [part.strip().lower() for part in self.headers.get('Accept-Encoding','').split(',')]
            if compressed:content=gzip.compress(content,mtime=0)
            digest='"'+hashlib.sha256(content).hexdigest()+'"' if etag else None
            if digest and self.headers.get('If-None-Match')==digest:code=304;content=b''
            self.send_response(code)
            self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)))
            self.send_header('Cache-Control','private, max-age=86400, immutable' if public else 'no-store')
            if compressible:self.send_header('Vary','Accept-Encoding')
            if compressed:self.send_header('Content-Encoding','gzip')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://www.google.com https://t0.gstatic.com https://t1.gstatic.com https://t2.gstatic.com https://t3.gstatic.com; object-src 'none'; base-uri 'self'; form-action 'self'")
            if digest:self.send_header('ETag',digest)
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            if cookie is None:cookie=getattr(self,'renew_cookie',None)
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers()
            if content:self.wfile.write(content)
        def allowed(self,user,admin=False):
            if not user:self.respond({'error':'Meld je aan om Home Invest te gebruiken.'},401);return False
            if admin and user['role']!='admin':self.respond({'error':'Alleen een admin heeft toegang tot deze functie.'},403);return False
            return True
        def do_GET(self):
            path=urlsplit(self.path).path
            if path in assets:
                name,kind=assets[path];content=(static/name).read_bytes()
                if path=='/style.css':content+=b'\n'+(static/'reports.css').read_bytes()
                if path=='/':
                    language=(auth.user(self.token()) or {}).get('language','')
                    content=content.replace(b'__ASSET_VERSION__',APP_VERSION.encode()).replace(b'__ACCOUNT_LANGUAGE__',(language if language in LANGUAGES else '').encode())
                return self.respond(content,kind=kind,etag=path!='/',public=path!='/')
            user=auth.user(self.token())
            self.renew_cookie=self.cookie(self.token()) if user and user.get('csrf') else None
            if path=='/api/session':return self.respond({'enabled':auth.enabled(),'user':user})
            if not self.allowed(user,admin=path.startswith('/api/portfolio/') or path in ('/api/home-assistant','/api/users','/api/backup','/api/export','/api/imports','/api/imports/mappings','/api/imports/issues','/api/logs')):return
            if path=='/api/feedback':
                try:return self.respond(feedback_overview(store))
                except ValueError as error:return self.respond({'error':str(error)},503)
            if path=='/api/export':
                if not auth.enabled():return self.respond({'error':'Alleen een admin heeft toegang tot deze functie.'},403)
                from exports import export
                query=parse_qs(urlsplit(self.path).query)
                format=query.get('format',['csv'])[0]
                try:
                    content,kind=export(store,query.get('account_id',['all'])[0],format)
                    return self.respond(content,kind=kind,filename='home-invest.'+format)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldige aanvraag of brokeraccount.'},400)
            if path=='/api/account/dashboard':
                from dashboard_layout import read
                try:return self.respond(read(store,user,self.headers.get('X-HomeInvest-Profile','personal')))
                except ValueError as error:return self.respond({'error':str(error)},400)
            if path=='/api/portfolio/conversions':
                from conversions import overview
                return self.respond(overview(store))
            if path=='/api/portfolio/conversion-backup':
                from conversions import safety_backup
                try:
                    backup=safety_backup(store,parse_qs(urlsplit(self.path).query).get('name',[''])[0])
                    return self.respond(backup.read_bytes(),kind='application/vnd.sqlite3',filename=backup.name)
                except ValueError as error:return self.respond({'error':str(error)},400)
            if path=='/api/home-assistant':
                from ha_export import overview,configuration,valid_token
                summary=overview(store,cache)
                return self.respond({'summary':summary,'configuration':configuration(summary['currencies']),'enabled':valid_token((integration_options or {}).get('home_assistant_token',''))})
            if path in ('/api/transactions','/api/transactions/changes','/api/portfolio/delete-preview','/api/portfolio/deletion-backup'):
                query=parse_qs(urlsplit(self.path).query)
                try:
                    if path=='/api/transactions':return self.respond(transactions.ledger(store,query.get('account_id',['all'])[0]))
                    if path=='/api/transactions/changes':return self.respond(transactions.changes(store,query.get('kind',[''])[0],query.get('id',['0'])[0]))
                    if path=='/api/portfolio/delete-preview':return self.respond(transactions.reset_preview(store,query.get('account_id',['all'])[0]))
                    backup=transactions.deletion_backup(store,query.get('name',[''])[0])
                    return self.respond(backup.read_bytes(),kind='application/vnd.sqlite3',filename=backup.name)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldige aanvraag of brokeraccount.'},400)
            if path=='/api/instruments/categories':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.category_overview(store,query.get('account_id',['all'])[0]),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount.'},400)
            if path=='/api/instrument/company':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.company(store,{k:query.get(k,[''])[0] for k in ('symbol','exchange','currency')},query.get('account_id',['all'])[0]))
                except (ValueError,TypeError):return self.respond({'error':'Aandeel of brokeraccount niet gevonden.'},400)
            if path=='/api/instrument':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.details(store,{k:query.get(k,[''])[0] for k in ('symbol','exchange','currency')},query.get('account_id',['all'])[0],include_pending=user['role']=='admin'))
                except (ValueError,TypeError):return self.respond({'error':'Aandeel of brokeraccount niet gevonden.'},400)
            if path=='/api/logs':
                if not auth.enabled():return self.respond({'error':'Schakel gebruikersbeveiliging in en meld je aan als admin om logs te bekijken.'},403)
                query=parse_qs(urlsplit(self.path).query)
                try:result=read_logs(store,query.get('level',[''])[0],query.get('source',[''])[0],int(query.get('before',['0'])[0]),query.get('q',[''])[0])
                except ValueError:return self.respond({'error':'Ongeldig logfilter.'},400)
                return self.respond(result,filename='home-invest-logs.json' if query.get('download')==['1'] else None)
            if path=='/api/users':return self.respond({'users':auth.list_users()})
            if path=='/api/fx/history':
                currency=parse_qs(urlsplit(self.path).query).get('currency',['USD'])[0]
                try:return self.respond(fx_history(store,currency))
                except ValueError as error:return self.respond({'error':str(error)},400)
            if path=='/api/fx':
                from datetime import date
                day=parse_qs(urlsplit(self.path).query).get('day',[date.today().isoformat()])[0]
                try:return self.respond(fx_overview(store,day))
                except ValueError as error:return self.respond({'error':str(error)},400)
            if path=='/api/imports/issues':return self.respond(list_issues(store))
            if path=='/api/imports/mappings':return self.respond({'mappings':mapping_list(store)})
            if path=='/api/imports':
                with store.connect() as db:batches=[dict(r) for r in db.execute('SELECT id,account_id,provider,filename,status,created_at FROM import_batches ORDER BY id DESC LIMIT 50')]
                return self.respond({'providers':[{'id':key,'name':value['name'],'formats':value['formats']} for key,value in ADAPTERS.items()],'batches':batches})
            if path=='/api/dividends/overview':
                from dividend_dashboard import overview,euro_overview
                account=parse_qs(urlsplit(self.path).query).get('account_id',['all'])[0]
                try:return self.respond(cache.derived('dividend-euro:'+str(account),lambda:euro_overview(store,cache.get(store.state),account,fetch_rates=False)) if parse_qs(urlsplit(self.path).query).get('combined')==['1'] else cache.derived('dividend:'+str(account),lambda:overview(cache.get(store.state),account)),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount.'},400)
            if path=='/api/stocks':
                from stocks_dashboard import overview
                account=parse_qs(urlsplit(self.path).query).get('account_id',['all'])[0]
                try:return self.respond(overview(store,cache.get(store.state),account))
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount.'},400)
            if path=='/api/home/euro':
                from dashboard import compact
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    result=home_euro(account,compact_view=query.get('compact')==['1'])
                    return self.respond(result,etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
            if path=='/api/reports/combined':
                from reports import combined as report_combined
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    instrument=query.get('instrument',[''])[0];selection=json.loads(instrument) if instrument else None
                    currency=query.get('currency',[''])[0];with_history=query.get('history')==['1']
                    key='reports-combined:'+json.dumps([account,selection,currency,with_history],separators=(',',':'))
                    return self.respond(cache.derived(key,lambda:report_combined(store,cache.get(store.state),account,selection,currency,with_history)),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
                except Exception as error:
                    reference=record(store,'ERROR','reports','combined_failed','Totaal in euro berekenen mislukt.',{'error_type':type(error).__name__})
                    message='Totaal in euro berekenen mislukt.'+' · Log-ID '+reference
                    return self.respond({'error':message},500)
            if path=='/api/reports/performance':
                from performance import overview
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    instrument=query.get('instrument',[''])[0];selection=json.loads(instrument) if instrument else None
                    currency=query.get('currency',[''])[0]
                    key='performance:'+json.dumps([account,selection,currency],separators=(',',':'))
                    result=cache.derived(key,lambda:overview(store,cache.get(store.state),account,selection,currency))
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
                except Exception as error:
                    reference=record(store,'ERROR','reports','performance_failed','Rendementsrapport berekenen mislukt.',{'error_type':type(error).__name__})
                    message='Rendementsrapport berekenen mislukt.'+' · Log-ID '+reference
                    return self.respond({'error':message},500)
                return self.respond(result,etag=True)
            if path=='/api/reports/history':
                from reports import history as report_history
                query=parse_qs(urlsplit(self.path).query)
                account=query.get('account_id',['all'])[0]
                instrument=query.get('instrument',[''])[0]
                currency=query.get('currency',[''])[0]
                try:
                    selection=json.loads(instrument) if instrument else None
                    key='reports-history:'+json.dumps([account,selection,currency],separators=(',',':'))
                    return self.respond(cache.derived(key,lambda:report_history(cache.get(store.state),account,selection,currency)),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
            if path=='/api/home/history':
                from dashboard import histories
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    selections=json.loads(query.get('positions',['[]'])[0])
                    combined=query.get('combined')==['1']
                    def selected_histories():
                        snapshot=cache.get(store.state)
                        if combined:
                            histories(snapshot,account,selections)  # validate before work
                            selected={tuple(row[k] for k in ('account_id','symbol','exchange','currency')) for row in selections}
                            members=[p for p in snapshot['positions'] if tuple(p[k] for k in ('account_id','symbol','exchange','currency')) in selected]
                            from home_euro import overview
                            converted=overview(store,{**snapshot,'positions':members},account,fetch_rates=False)
                            snapshot={**snapshot,'positions':converted['positions']}
                        return histories(snapshot,account,selections)
                    key='home-selected-history:'+json.dumps([account,combined,selections],separators=(',',':'))
                    return self.respond(cache.derived(key,selected_histories),etag=True)
                except (ValueError,TypeError,KeyError):return self.respond({'error':'Kies één tot zes bestaande posities in dit brokeraccount.'},400)
            if path=='/api/state':
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                def state_view():
                    state=cache.get(store.state)
                    if account!='all':
                        account_id=int(account)
                        if not any(a['id']==account_id for a in state['accounts']):raise LookupError()
                        state={**state,**{key:[r for r in state[key] if r['account_id']==account_id] for key in ('purchases','dividends','positions')}}
                        state['portfolios']=portfolio_values(state['positions'])
                    from dashboard import compact
                    return compact(state) if query.get('compact')==['1'] else state
                try:state=cache.derived('state-compact:'+account,state_view) if query.get('compact')==['1'] else state_view()
                except ValueError:return self.respond({'error':'Ongeldig brokeraccount.'},400)
                except LookupError:return self.respond({'error':'Brokeraccount niet gevonden.'},404)
                return self.respond({**{k:v for k,v in state.items() if k!='quotes'},'status':status,'refresh_minutes':interval//60,'app_version':APP_VERSION},etag=True)
            if path=='/api/backup':
                backup=store.backup();return self.respond(backup.read_bytes(),kind='application/vnd.sqlite3',filename=backup.name)
            if path=='/api/listing':
                symbol=parse_qs(urlsplit(self.path).query).get('symbol',[''])[0].upper()
                if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',symbol):return self.respond({'error':'Ongeldig symbool.'},400)
                try:return self.respond(resolve_listing(symbol,store=store))
                except Exception:return self.respond({'error':'De notering of koersvaluta kon niet worden gecontroleerd. Probeer later opnieuw.'},502)
            if path=='/api/search':
                query=parse_qs(urlsplit(self.path).query).get('q',[''])[0]
                if not 2<=len(query.strip())<=80:return self.respond({'error':'Typ minimaal twee en maximaal 80 tekens.'},400)
                try:return self.respond({'results':search_stocks(query,store=store)})
                except Exception:return self.respond({'error':'Zoeken bij Yahoo lukt nu niet. Probeer het opnieuw.'},502)
            self.respond({'error':'Niet gevonden'},404)
        def do_POST(self):
            path=urlsplit(self.path).path
            # Consume bounded request bodies before replying, including on denied
            # requests. Closing with unread bytes can reset browser connections.
            try:
                length=int(self.headers.get('Content-Length','0'))
                limit=25*1024*1024 if path=='/api/restore' else 8*1024*1024 if path=='/api/imports/preview' else 65536
                if not 0<length<=limit:raise ValueError('Bestand of aanvraag is te groot of leeg.')
                self.connection.settimeout(30)
                body=self.rfile.read(length)
                if len(body)!=length:raise ValueError('Upload niet volledig ontvangen.')
            except (ValueError,TimeoutError):
                return self.respond({'error':'Bestand of aanvraag is te groot, leeg of onvolledig.'},400)
            expected='application/octet-stream' if path=='/api/restore' else 'application/json'
            if self.headers.get('X-Portfolio-Request')!='1' or self.headers.get('Content-Type')!=expected:
                return self.respond({'error':'Ongeldige aanvraag.'},403)
            user=auth.user(self.token())
            self.renew_cookie=self.cookie(self.token()) if user and user.get('csrf') else None
            if path!='/api/auth/login':
                if not self.allowed(user,admin=path.startswith('/api/portfolio/') or path in ('/api/transactions/edit','/api/instrument/categories','/api/instrument/valuation') or path in ('/api/settings','/api/restore','/api/users','/api/auth/enable','/api/auth/disable','/api/accounts','/api/updates') or path.startswith('/api/imports/')):return
                if auth.enabled() and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf'] or ''):
                    return self.respond({'error':'Ongeldige sessiebeveiliging. Meld je opnieuw aan.'},403)
            try:
                if path=='/api/restore':
                    if self.headers.get('X-Confirm-Restore')!='yes':raise ValueError('Bevestig het terugzetten van de portefeuille.')
                    with refresh_lock:
                        result=restore_backup(store,body);cache.invalidate()
                        auth.clear_sessions()
                    refresh_requested.set()
                    return self.respond({'ok':True,'restored':result},cookie=self.cookie(''))
                data=json.loads(body)
                if not isinstance(data,dict):raise ValueError('Ongeldige aanvraag.')
                if path=='/api/account/dashboard':
                    from dashboard_layout import save
                    return self.respond(save(store,user,self.headers.get('X-HomeInvest-Profile','personal'),data))
                if path=='/api/account/language':
                    return self.respond({'language':auth.set_language(user,data.get('language'))})
                if path=='/api/instrument/valuation':
                    from valuations import save as save_valuation
                    with refresh_lock:
                        result=save_valuation(store,data);cache.invalidate()
                    refresh_requested.set()
                    return self.respond(result)
                if path in ('/api/portfolio/conversion-preview','/api/portfolio/conversion'):
                    from conversions import preview,commit
                    with refresh_lock:
                        try:result=preview(store,data) if path.endswith('-preview') else commit(store,data,user['username'])
                        except OSError:return self.respond({'error':'De veiligheidsback-up kon niet worden gemaakt. De omboeking is niet opgeslagen.'},500)
                        if not path.endswith('-preview'):cache.invalidate();refresh_requested.set()
                    return self.respond(result)
                if path=='/api/instrument/categories':
                    with refresh_lock:
                        result=instruments.save_categories(store,data);cache.invalidate()
                    return self.respond(result)
                if path=='/api/transactions/edit':
                    with refresh_lock:
                        result=transactions.edit(store,data,user['username']);cache.invalidate()
                    refresh_requested.set()
                    return self.respond(result)
                if path=='/api/portfolio/delete':
                    with refresh_lock:
                        try:result=transactions.reset(store,data)
                        except OSError:return self.respond({'error':'De veiligheidsback-up kon niet worden gemaakt. Er is niets verwijderd.'},500)
                        cache.invalidate()
                    refresh_requested.set()
                    return self.respond(result)
                if path=='/api/fx/convert':return self.respond(fx_convert(store,data['amount'],data['from'],data['to'],data['day']))
                if path.startswith('/api/imports/trading212/'):
                    if not auth.enabled():raise ValueError('Schakel eerst gebruikersbeveiliging in bij Instellingen om API-sleutels te beheren.')
                    account_id=int(data['account_id'])
                    action=path.rsplit('/',1)[-1]
                    try:
                        if action=='save':result=trading212_api.save_connection(store,account_id,data.get('key'),data.get('secret'),data.get('environment'))
                        elif action=='status':result=trading212_api.connection_status(store,account_id)
                        elif action=='forget':result=trading212_api.forget(store,account_id)
                        elif action=='cancel':result=trading212_api.cancel(store,account_id)
                        elif action=='start':result=trading212_api.start(store,account_id,data['start'],data['end'],data.get('dividends',True))
                        elif action=='poll':result=trading212_api.poll(store,account_id)
                        else:return self.respond({'error':'Niet gevonden'},404)
                    except OSError:return self.respond({'error':'Verbinding kon niet veilig worden opgeslagen of gelezen.'},500)
                    return self.respond(result)
                if path=='/api/updates':
                    try:return self.respond(check_updates(store))
                    except Exception:return self.respond({'error':'Versiecontrole niet beschikbaar. Probeer later opnieuw of bekijk GitHub.'},502)
                if path=='/api/accounts':
                    store.add_account(data);cache.invalidate();return self.respond({'ok':True},201)
                if path=='/api/imports/mappings':return self.respond(mapping_edit(store,data))
                if path=='/api/imports/preview':
                    result=import_preview(store,int(data['account_id']),str(data['provider']),str(data['filename']),str(data['csv']))
                    return self.respond(result)
                if path=='/api/imports/commit':
                    result=commit_partial(store,int(data['batch_id']));cache.invalidate();refresh_requested.set();return self.respond(result)
                if path=='/api/imports/issues/resolve':
                    result=resolve_issue(store,data);cache.invalidate();refresh_requested.set();return self.respond(result)
                if path=='/api/imports/resolve':return self.respond(resolve_instrument(store,int(data['batch_id']),str(data['key'])))
                if path=='/api/imports/open':return self.respond(open_preview(store,int(data['batch_id'])))
                if path=='/api/auth/login':
                    if not auth.enabled():raise ValueError('Gebruikersbeveiliging is niet ingeschakeld.')
                    token=auth.login(data.get('username',''),data.get('password',''),self.client_address[0])
                    return self.respond({'ok':True},cookie=self.cookie(token))
                if path=='/api/auth/enable':
                    auth.enable(data.get('username',''),data.get('password',''));cache.invalidate()
                    token=auth.login(data.get('username',''),data.get('password',''),self.client_address[0])
                    return self.respond({'ok':True},cookie=self.cookie(token))
                if path=='/api/auth/disable':
                    with store.connect() as db:
                        row=db.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
                        if not row or not verify_password(data.get('password',''),row['password_hash']):raise ValueError('Huidig adminwachtwoord onjuist.')
                        db.execute("UPDATE app_settings SET value='false' WHERE key='auth_enabled'")
                    auth.clear_sessions()
                    cache.invalidate();return self.respond({'ok':True},cookie=self.cookie(''))
                if path=='/api/auth/logout':
                    auth.logout(self.token());return self.respond({'ok':True},cookie=self.cookie(''))
                if path=='/api/auth/password':
                    if user['id'] is None:raise ValueError('Schakel gebruikers eerst in.')
                    auth.change_password(user['id'],data.get('current',''),data.get('password',''),data.get('username'))
                    return self.respond({'ok':True},cookie=self.cookie(''))
                if path=='/api/users':
                    if not auth.enabled():raise ValueError('Schakel gebruikers eerst in.')
                    auth.save_user(data);return self.respond({'ok':True})
                if path=='/api/settings':store.save_settings(data)
                elif path=='/api/dividends':store.add_dividend(data)
                elif path=='/api/purchases':store.add(data);refresh_requested.set()
                else:return self.respond({'error':'Niet gevonden'},404)
                cache.invalidate();self.respond({'ok':True},201 if path!='/api/settings' else 200)
            except PermissionError as error:self.respond({'error':str(error)},429)
            except ValueError as error:
                if not isinstance(error,DiagnosticError):record(store,'WARNING','fx' if path.startswith('/api/fx') else 'web','request_rejected',str(error) if isinstance(error,ActionError) else 'Aanvraag afgewezen.',{'endpoint':path,'error_type':type(error).__name__,'code':error.code if isinstance(error,ActionError) else None})
                self.respond({'error':str(error)},400)
            except (KeyError,TypeError,sqlite3.Error):
                record(store,'ERROR','web','request_failed','Aanvraag kon niet worden verwerkt.',{'endpoint':path})
                self.respond({'error':'Aanvraag mislukt. Controleer velden, wachtwoord (12–128 tekens), rollen of het back-upbestand.'},400)
    if enable_demo:
        from demo import profile_handler
        from cache import StateCache
        import threading
        return profile_handler(Handler,store,auth,lambda demo:make_handler(demo,auth,StateCache(store=demo),{'message':'Voorbeeldportefeuille · providerkoersen mogelijk vertraagd · fictieve transacties en historie','last_attempt':None},interval,threading.Lock(),threading.Event(),None,enable_demo=False))
    return Handler
