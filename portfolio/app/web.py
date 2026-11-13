"""HTTP boundary: authorization is enforced here, independent of page visibility."""
import gzip
import hashlib
import hmac
import json
import os
import shutil
import re
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote,urlsplit,parse_qs
from pathlib import Path
from provider import search_stocks,listing as resolve_listing,quote_symbol
from restore import restore_backup
from backup_crypto import LIMIT as BACKUP_LIMIT, OVERHEAD, decrypt, encrypt
from security import verify_password,SESSION_TTL
import passkeys
from version import APP_VERSION
from i18n import localize,LANGUAGES
from updates import check_updates
from feedback_client import overview as feedback_overview,connect as feedback_connect,enqueue as feedback_enqueue
from imports import ADAPTERS
from imports.listings import BROKER_LISTINGS
from imports.service import preview as import_preview,open_preview
from imports.partial import commit_partial,list_issues,resolve_issue
from imports.matching import resolve_instrument
from imports.registry import discover as mapping_list,edit as mapping_edit
from imports import trading212_api
from storage import PortfolioRevisionChanged
import transactions
import broker_accounts
import instruments
from history import portfolio_values
from diagnostics import read_logs,record,DiagnosticError,ActionError
from forex import overview as fx_overview,convert as fx_convert,history as fx_history

def make_handler(store,auth,cache,status,interval,refresh_lock,refresh_requested,integration_options=None,enable_demo=True):
    from logo_cache import LogoCache
    def logo_error(group,stage,error_type,status):
        record(store,'WARNING','logos','logo_cache_failed','Logo ophalen of opslaan mislukt.',
               {'group':group,'stage':stage,'error_type':error_type,'http_status':status})
    logos=LogoCache(store.root,logo_error)
    cache.bind(store)
    from resource_stats import ResourceMonitor
    resources=ResourceMonitor(store,cache)
    def compact_state():return cache.derived('state-compact:all',lambda:store.state(compact_view=True))
    def home_euro(account,compact_view=False,chart_only=False):
        from home_euro import compact_overview,overview
        def build():
            if compact_view:
                return compact_overview(store,compact_state(),account)
            for attempt in range(2):
                snapshot=compact_state() if chart_only else cache.get(store.state)
                try:
                    result=overview(store,snapshot,account,fetch_rates=False,
                                    retain_history=not chart_only,skip_invalid=True,allow_missing_value=True,
                                    expected_revision=snapshot['data_revision'],
                                    positions=store.position_histories(snapshot,account,skip_invalid=True) if chart_only else None)
                    break
                except PortfolioRevisionChanged:
                    if attempt:raise
            result['data_revision']=snapshot['data_revision']
            if chart_only:return {k:result[k] for k in ('portfolios','data_revision','as_of','excluded')}
            return result
        return cache.derived(('home-euro-chart:' if chart_only else 'home-euro-compact:' if compact_view else 'home-euro:')+str(account),build)
    static=Path(__file__).parent/'static'
    assets={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/reports.css':('reports.css','text/css')}
    for name, kind in (
        ('app-icon.png', 'image/png'),
        ('home-invest-icon.png', 'image/png'),
        ('favicon.ico', 'image/vnd.microsoft.icon'),
    ):
        assets['/branding/' + name] = ('branding/' + name, kind)
    assets['/login-market.svg']=('login-market.svg','image/svg+xml')
    assets['/fonts/Roboto.ttf']=('fonts/Roboto.ttf','font/ttf')
    assets['/world-countries.json']=('world-countries.json','application/json; charset=utf-8')
    for media in (static/'broker-media').glob('*.png'):assets['/broker-media/'+media.name]=('broker-media/'+media.name,'image/png')
    for logo in (static/'company-logos').glob('*.png'):assets['/company-logos/'+logo.name]=('company-logos/'+logo.name,'image/png')
    for flag in (static/'flags').glob('*.svg'):assets['/flags/'+flag.name]=('flags/'+flag.name,'image/svg+xml')
    for name in ('brokers','feedback','i18n','translations','loading','dashboard-layout','home','app','pages','chart','chart-view','access','imports','logs','currencies','import-mappings','import-issues','transactions','popups','table-filters','stock-detail','category-status','dividends','stocks','funds','tasks','resource-stats','maintenance','backup-files','reports','charges','purchase-fx','report-charts','conversions','performance'):
        assets['/'+name+'.js']=(name+'.js','text/javascript; charset=utf-8')
    assets['/country-map.js']=('country-map.js','text/javascript; charset=utf-8')
    class Handler(BaseHTTPRequestHandler):
        timeout = 15

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
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'")
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
        def confirm_sensitive(self,user):
            if not auth.enabled():
                return
            from urllib.parse import unquote
            password=unquote(self.headers.get('X-Confirm-Password',''))
            auth.verify_credentials(user['username'],password,self.client_address[0])

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
            if path=='/api/passkeys':
                try:return self.respond(passkeys.list_keys(store,user)) if self.allowed(user) else None
                except ValueError as error:return self.respond({'error':str(error)},400)
            if not self.allowed(user,admin=path.startswith('/api/accounts/') or path.startswith('/api/portfolio/') or path=='/api/charges/export' or path in ('/api/home-assistant','/api/users','/api/backup','/api/export','/api/imports','/api/imports/mappings','/api/imports/issues','/api/logs','/api/resource-stats','/api/health-center')):return
            if path=='/api/company-logo':
                query=parse_qs(urlsplit(self.path).query)
                image=logos.get(query.get('group',[''])[0],query.get('domain',[''])[0])
                return self.respond(image or b'',200 if image else 404,kind='image/png',etag=bool(image))
            if path in ('/api/accounts/edit','/api/accounts/delete-preview'):
                query=parse_qs(urlsplit(self.path).query)
                try:
                    account_id=query.get('account_id',[''])[0]
                    if path.endswith('/edit'):return self.respond(broker_accounts.overview(store,account_id))
                    return self.respond(transactions.reset_preview(store,int(account_id)))
                except (ValueError,TypeError):return self.respond({'error':'Ongeldige aanvraag of brokeraccount.'},400)
            if path=='/api/feedback':
                try:return self.respond(feedback_overview(store,integration_options,user))
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
            if path in ('/api/backup','/api/portfolio/file','/api/portfolio/conversion-backup','/api/portfolio/deletion-backup') and auth.enabled():
                return self.respond({'error':'Bevestig het downloaden vanuit de app.'},403)
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
            if path=='/api/tasks/etf':
                if not self.allowed(user,admin=True):return
                from fund_tasks import status as task_status
                return self.respond(task_status(store))
            if path=='/api/instruments/categories':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.category_overview(store,query.get('account_id',['all'])[0]),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount.'},400)
            if path=='/api/stocks/movers':
                from dashboard import MOVER_PERIODS,stock_movers
                query=parse_qs(urlsplit(self.path).query)
                account=query.get('account_id',['all'])[0]
                try:
                    period=int(query.get('days',['1'])[0])
                    if period not in MOVER_PERIODS or (account!='all' and str(int(account))!=account):
                        raise ValueError()
                    return self.respond(cache.derived(f'stock-movers:{account}:{period}',lambda:stock_movers(store,compact_state(),account,period)))
                except PortfolioRevisionChanged:return self.respond({'error':'De portefeuille is gewijzigd. Vernieuw het overzicht.'},409)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldige aanvraag of brokeraccount.'},400)
            if path=='/api/instrument/holdings':
                from fund_holdings import saved,KNOWN
                query=parse_qs(urlsplit(self.path).query)
                try:
                    key=instruments.owned_key(store,{k:query.get(k,[''])[0] for k in ('symbol','exchange','currency')},query.get('account_id',['all'])[0])
                    return self.respond(dict(composition=saved(store,key),source_url=KNOWN.get(key,'')))
                except (ValueError,TypeError):return self.respond({'error':'Aandeel of brokeraccount niet gevonden.'},400)
            if path=='/api/instrument/fundamentals':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.fundamentals(store,{k:query.get(k,[''])[0] for k in ('symbol','exchange','currency')},query.get('account_id',['all'])[0]))
                except (ValueError,TypeError):return self.respond({'error':'Aandeel of brokeraccount niet gevonden.'},400)
            if path=='/api/instrument/company':
                query=parse_qs(urlsplit(self.path).query)
                try:return self.respond(instruments.company(store,{k:query.get(k,[''])[0] for k in ('symbol','exchange','currency')},query.get('account_id',['all'])[0]))
                except (ValueError,TypeError):return self.respond({'error':'Aandeel of brokeraccount niet gevonden.'},400)
            if path in ('/api/fund/constituent','/api/fund/constituent/company'):
                import constituents
                query=parse_qs(urlsplit(self.path).query)
                data={k:query.get(k,[''])[0] for k in ('symbol','exchange','currency','holding','as_of','holding_name','holding_isin','holding_symbol')}
                try:return self.respond((constituents.company if path.endswith('/company') else constituents.details)(store,data,query.get('account_id',['all'])[0]))
                except (ValueError,TypeError):return self.respond({'error':'Onderliggende belegging niet gevonden. Open deze opnieuw vanuit de ETF.'},400)
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
                return self.respond({'providers':[{'id':key,'name':value['name'],'formats':value['formats']} for key,value in ADAPTERS.items() if not value.get('any_broker')],'batches':batches})
            if path=='/api/dividends/overview':
                from dividend_dashboard import overview,euro_overview
                query=parse_qs(urlsplit(self.path).query)
                account=query.get('account_id',['all'])[0]
                combined=query.get('combined')==['1']
                slot=('dividend-euro:' if combined else 'dividend:')+account
                stage='cache'
                def build():
                    nonlocal stage
                    stage='history'
                    try:snapshot=store.dividend_state(account)
                    except LookupError as error:
                        if type(error) is not LookupError:raise
                        raise ActionError('Ongeldig brokeraccount.') from None
                    stage='forecast'
                    return euro_overview(store,snapshot,account,fetch_rates=False) if combined else overview(snapshot,account)
                try:
                    result=cache.derived(slot,build)
                    return self.respond(result,etag=True)
                except ActionError as error:
                    return self.respond({'error':str(error)},400)
                except Exception as error:
                    reference=record(store,'ERROR','dividend','dividend_overview_failed',
                                     'Het dividendoverzicht kon niet worden geladen.',
                                     {'stage':stage,'combined':combined,'scope':'all' if account=='all' else 'broker',
                                      'error_type':type(error).__name__})
                    return self.respond({'error':'Het dividendoverzicht kon niet worden geladen.','log_id':reference},503)
            if path=='/api/stocks':
                from stocks_dashboard import overview
                account=parse_qs(urlsplit(self.path).query).get('account_id',['all'])[0]
                try:return self.respond(overview(store,compact_state(),account))
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount.'},400)
            if path=='/api/stocks/sector-benchmark':
                from stocks_dashboard import overview
                from sector_benchmark import compare
                query=parse_qs(urlsplit(self.path).query)
                account=query.get('account_id',['all'])[0];sector=query.get('sector',[''])[0]
                try:
                    positions=overview(store,compact_state(),account)['positions']
                    return self.respond(compare(store,positions,sector))
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
            if path in ('/api/home/euro','/api/home/euro/history'):
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    result=home_euro(account,compact_view=query.get('compact')==['1'] and path=='/api/home/euro',chart_only=path.endswith('/history'))
                    return self.respond(result,etag=True)
                except PortfolioRevisionChanged:
                    return self.respond({'error':'De portefeuille is gewijzigd. Vernieuw het overzicht.'},409)
                except (LookupError,ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
                except Exception as error:
                    reference=record(store,'ERROR','market','home_euro_failed','Het euro-overzicht kon niet worden geladen.',{'error_type':type(error).__name__,'chart':path.endswith('/history')})
                    return self.respond({'error':'Het euro-overzicht kon niet worden geladen.','log_id':reference},503)
            if path in ('/api/reports/charges','/api/charges/export'):
                if path.endswith('/export') and not auth.enabled():return self.respond({'error':'Alleen een admin heeft toegang tot deze functie.'},403)
                from charges import report as charge_report,export_csv as charge_csv
                query=parse_qs(urlsplit(self.path).query)
                try:
                    result=charge_report(store,query.get('account_id',['all'])[0],query.get('year',[''])[0],query.get('currency',[''])[0],query.get('view',['all'])[0])
                    if path.endswith('/export'):return self.respond(charge_csv(result),kind='text/csv; charset=utf-8',filename='home-invest-charges.csv')
                    return self.respond(result)
                except (ValueError,TypeError,KeyError) as error:return self.respond({'error':str(error)},400)
            if path=='/api/reports/combined':
                from reports import combined as report_combined
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    instrument=query.get('instrument',[''])[0];selection=json.loads(instrument) if instrument else None
                    currency=query.get('currency',[''])[0];with_history=query.get('history')==['1']
                    key='reports-combined:'+json.dumps([account,selection,currency,with_history],separators=(',',':'))
                    return self.respond(cache.derived(key,lambda:report_combined(store,compact_state(),account,selection,currency,with_history,stream_history=True)),etag=True)
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
                    result=cache.derived(key,lambda:overview(store,store.sampled_state(compact_state(),'annual',account),account,selection,currency))
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
                    return self.respond(cache.derived(key,lambda:report_history({**compact_state(),'positions':store.position_histories(compact_state(),account,skip_invalid=True)},account,selection,currency)),etag=True)
                except (ValueError,TypeError):return self.respond({'error':'Ongeldig brokeraccount of onvolledige gegevens.'},400)
            if path=='/api/home/history':
                from dashboard import histories
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                try:
                    selections=json.loads(query.get('positions',['[]'])[0])
                    combined=query.get('combined')==['1']
                    def selected_histories():
                        snapshot=compact_state()
                        histories(snapshot,account,selections)
                        selected={tuple(row[k] for k in ('account_id','symbol','exchange','currency')) for row in selections}
                        members=[p for p in snapshot['positions'] if tuple(p[k] for k in ('account_id','symbol','exchange','currency')) in selected]
                        snapshot={**snapshot,'positions':list(store.position_histories({**snapshot,'positions':members},account))}
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
            if path=='/api/health-center':
                from health_center import snapshot
                return self.respond(snapshot(store,auth))
            if path=='/api/resource-stats':return self.respond(resources.snapshot())
            if path=='/api/state':
                query=parse_qs(urlsplit(self.path).query);account=query.get('account_id',['all'])[0]
                def state_view():
                    if query.get('compact')==['1']:
                        if account!='all':int(account)
                        return store.state(compact_view=True,account=account)
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
            if path=='/api/portfolio/files':
                from backup_files import inventory
                return self.respond(inventory(store))
            if path=='/api/portfolio/file':
                from backup_files import file_path
                try:
                    with store.lock:
                        backup=file_path(store,parse_qs(urlsplit(self.path).query).get('name',[''])[0])
                        stream=backup.open('rb')
                except (ValueError,OSError):return self.respond({'error':'Back-upbestand niet gevonden.'},404)
                # Stream large files without reading the entire backup into RAM.
                with stream:
                    import os,shutil
                    self.send_response(200)
                    self.send_header('Content-Type','application/octet-stream')
                    self.send_header('Content-Length',str(os.fstat(stream.fileno()).st_size))
                    self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(backup.name,safe=''))
                    self.send_header('Cache-Control','no-store')
                    self.send_header('X-Content-Type-Options','nosniff')
                    self.end_headers()
                    try:shutil.copyfileobj(stream,self.wfile,1024*1024)
                    except (BrokenPipeError,ConnectionResetError):pass
                return
            if path=='/api/backup':
                backup=store.backup();return self.respond(backup.read_bytes(),kind='application/vnd.sqlite3',filename=backup.name)
            if path=='/api/listing':
                symbol=parse_qs(urlsplit(self.path).query).get('symbol',[''])[0].upper()
                if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',symbol):return self.respond({'error':'Ongeldig symbool.'},400)
                known=BROKER_LISTINGS[('trading212','US2017123041')]
                if symbol==known['symbol']:return self.respond(known)
                try:return self.respond(resolve_listing(symbol,store=store))
                except Exception:return self.respond({'error':'De notering of koersvaluta kon niet worden gecontroleerd. Probeer later opnieuw.'},502)
            if path=='/api/search':
                query=parse_qs(urlsplit(self.path).query).get('q',[''])[0].strip()
                if not 2<=len(query)<=80:return self.respond({'error':'Typ minimaal twee en maximaal 80 tekens.'},400)
                ticker=query.upper()
                with store.connect() as db:
                    rows = db.execute(
                        """SELECT symbol, exchange, currency, MAX(name) AS name
                           FROM purchases WHERE symbol = ? COLLATE NOCASE
                           OR substr(symbol, 1, length(?) + 1) = (? || '.') COLLATE NOCASE
                           GROUP BY symbol, exchange, currency ORDER BY exchange, currency""",
                        (ticker,ticker,ticker),
                    ).fetchall()
                results = [dict(row) for row in rows if row['symbol'].upper() in
                           (ticker, quote_symbol(ticker,row['exchange']))]
                # A bare ticker can resolve to a different exchange on Yahoo.
                queries=[query]
                amsterdam=quote_symbol(ticker,'AMSTERDAM')
                if re.fullmatch(r'[A-Z0-9-]{2,12}',ticker) and not any(
                    row['exchange']=='AMSTERDAM' for row in results
                ):
                    queries.insert(0,amsterdam)
                failed=False
                seen={(row['symbol'].upper(),row['exchange']) for row in results}
                for term in queries:
                    try:
                        remote=search_stocks(term,store=store)
                    except Exception:
                        failed=True
                        continue
                    for row in remote:
                        if term!=query and (row['symbol'].upper()!=amsterdam or row['exchange']!='AMSTERDAM'):
                            continue
                        key=(row['symbol'].upper(),row['exchange'])
                        if key not in seen:
                            seen.add(key)
                            results.append(row)
                if failed and not results:
                    return self.respond({'error':'Zoeken bij Yahoo lukt nu niet. Probeer het opnieuw.'},502)
                return self.respond({'results':results})
            self.respond({'error':'Niet gevonden'},404)
        def do_POST(self):
            path=urlsplit(self.path).path
            try:
                length=int(self.headers.get('Content-Length','0'))
                limit=BACKUP_LIMIT+OVERHEAD if path in ('/api/restore','/api/restore-preview') else 12*1024*1024 if path=='/api/instrument/holdings' else 8*1024*1024 if path=='/api/imports/preview' else 65536
                if not 0<length<=limit:raise ValueError('Bestand of aanvraag is te groot of leeg.')
            except (ValueError,TimeoutError):
                return self.respond({'error':'Bestand of aanvraag is te groot, leeg of onvolledig.'},400)
            expected='application/octet-stream' if path in ('/api/restore','/api/restore-preview') else 'application/json'
            if self.headers.get('X-Portfolio-Request')!='1' or self.headers.get('Content-Type')!=expected:
                return self.respond({'error':'Ongeldige aanvraag.'},403)
            user=auth.user(self.token())
            self.renew_cookie=self.cookie(self.token()) if user and user.get('csrf') else None
            if path not in ('/api/auth/login','/api/passkey/login/begin','/api/passkey/login/finish'):
                if not self.allowed(user,admin=path.startswith('/api/accounts/') or path.startswith('/api/portfolio/') or path in ('/api/health-action','/api/feedback/connect','/api/transactions/edit','/api/instrument/categories','/api/instrument/valuation','/api/instrument/holdings','/api/tasks/etf') or path in ('/api/purchases','/api/dividends','/api/settings','/api/backup-download','/api/restore','/api/restore-preview','/api/users','/api/auth/enable','/api/auth/disable','/api/accounts','/api/updates') or path.startswith('/api/imports/') or path.startswith('/api/charges/')):return
                if auth.enabled() and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf'] or ''):
                    return self.respond({'error':'Ongeldige sessiebeveiliging. Meld je opnieuw aan.'},403)
            try:
                deadline=time.monotonic()+30
                body=bytearray()
                while len(body)<length:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise TimeoutError
                    self.connection.settimeout(min(remaining,self.timeout))
                    chunk=self.rfile.read1(min(65536,length-len(body)))
                    if not chunk:raise ValueError('Upload niet volledig ontvangen.')
                    body.extend(chunk)
                if time.monotonic()>deadline:raise TimeoutError
            except (ValueError,TimeoutError):
                return self.respond({'error':'Bestand of aanvraag is te groot, leeg of onvolledig.'},400)
            finally:
                self.connection.settimeout(self.timeout)
            try:
                if path=='/api/restore-preview':
                    from urllib.parse import unquote
                    with store.lock:
                        content=decrypt(bytes(body),unquote(self.headers.get('X-Backup-Password','')))
                        return self.respond(restore_backup(store,content,preview=True))
                if path=='/api/restore':
                    if self.headers.get('X-Confirm-Restore')!='yes':raise ValueError('Bevestig het terugzetten van de portefeuille.')
                    self.confirm_sensitive(user)
                    from urllib.parse import unquote
                    with refresh_lock,store.lock:
                        content=decrypt(bytes(body),unquote(self.headers.get('X-Backup-Password','')))
                        result=restore_backup(store,content);cache.invalidate()
                        auth.clear_sessions()
                    refresh_requested.set()
                    return self.respond({'ok':True,'restored':result},cookie=self.cookie(''))
                data=json.loads(body)
                if not isinstance(data,dict):raise ValueError('Ongeldige aanvraag.')
                if path=='/api/health-action':
                    if data.get('action')=='refresh':
                        refresh_requested.set()
                        return self.respond({'ok':True},202)
                    if data.get('action')=='cache':
                        cache.invalidate()
                        return self.respond({'ok':True})
                    return self.respond({'error':'Ongeldige aanvraag.'},400)
                if path=='/api/backup-download':
                    self.confirm_sensitive(user)
                    from backup_files import file_path
                    from conversions import safety_backup
                    password=data.get('password')
                    name=data.get('name','')
                    kind=data.get('kind','backup')
                    with store.lock:
                        if kind=='file':
                            backup=file_path(store,name)
                        elif kind=='conversion':
                            backup=safety_backup(store,name)
                        elif kind=='deletion':
                            backup=transactions.deletion_backup(store,name)
                        elif kind=='backup':
                            backup=store.backup()
                        else:
                            raise ValueError('Ongeldige back-upsoort.')
                        if password and backup.stat().st_size>BACKUP_LIMIT:
                            raise ValueError('Deze back-up is groter dan 25 MB.')
                        if password:
                            content=encrypt(backup.read_bytes(),password)
                            return self.respond(content,kind='application/octet-stream',filename=backup.name+'.hib')
                        stream=backup.open('rb')
                    with stream:
                        self.send_response(200)
                        self.send_header('Content-Type','application/octet-stream')
                        self.send_header('Content-Length',str(os.fstat(stream.fileno()).st_size))
                        self.send_header('Cache-Control','no-store')
                        self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(backup.name,safe=''))
                        self.send_header('X-Content-Type-Options','nosniff')
                        if self.renew_cookie:self.send_header('Set-Cookie',self.renew_cookie)
                        self.end_headers()
                        shutil.copyfileobj(stream,self.wfile,65536)
                    return
                if path=='/api/portfolio/file-restore-preview':
                    from backup_files import reviewed_file
                    with store.lock:
                        selected=reviewed_file(store,data)
                        return self.respond(restore_backup(store,source_path=selected,preview=True))
                if path in ('/api/portfolio/file-delete','/api/portfolio/file-restore'):
                    from backup_files import reviewed_file
                    restoring=path.endswith('file-restore')
                    if restoring:self.confirm_sensitive(user)
                    if data.get('confirmation')!=('RESTORE' if restoring else 'DELETE'):raise ValueError('Bevestig de bestandsactie.')
                    if not refresh_lock.acquire(blocking=False):return self.respond({'error':'Er loopt een achtergrondtaak. Probeer het later opnieuw.'},409)
                    try:
                        with store.lock:
                            selected=reviewed_file(store,data)
                            if restoring:
                                result=restore_backup(store,source_path=selected);cache.invalidate();auth.clear_sessions()
                            else:selected.unlink()
                    except OSError:
                        return self.respond({'error':'De bestandsactie is mislukt. Vernieuw het overzicht.'},400)
                    finally:refresh_lock.release()
                    with resources.lock:resources.storage=None
                    if restoring:
                        refresh_requested.set()
                        return self.respond({'ok':True,'restored':result},cookie=self.cookie(''))
                    return self.respond({'ok':True})
                if path in ('/api/portfolio/cleanup-preview','/api/portfolio/cleanup'):
                    from maintenance import preview as cleanup_preview,clean as cleanup_run
                    if path.endswith('-preview'):return self.respond(cleanup_preview(store,data))
                    if not refresh_lock.acquire(blocking=False):return self.respond({'error':'Er loopt een achtergrondtaak. Probeer het opschonen straks opnieuw.'},409)
                    try:result=cleanup_run(store,cache,data)
                    except OSError as error:
                        record(store,'ERROR','system','cleanup_failed','Opschonen kon niet worden afgerond.',{'error_type':type(error).__name__})
                        return self.respond({'error':'Opschonen kon niet worden afgerond. Controleer de logs en eventuele herstelback-up.'},503)
                    finally:refresh_lock.release()
                    with resources.lock:resources.storage=None
                    return self.respond(result)
                if path in ('/api/feedback/connect','/api/feedback/submit'):
                    try:
                        result=feedback_connect(store,integration_options,data) if path.endswith('/connect') else feedback_enqueue(store,integration_options,user,data)
                        return self.respond(result,202 if path.endswith('/submit') else 200)
                    except OSError:return self.respond({'error':'De melding of verbinding kon niet veilig worden opgeslagen.'},503)
                if path=='/api/account/dashboard':
                    from dashboard_layout import save
                    return self.respond(save(store,user,self.headers.get('X-HomeInvest-Profile','personal'),data))
                if path=='/api/account/language':
                    return self.respond({'language':auth.set_language(user,data.get('language'))})
                if path=='/api/tasks/etf':
                    from fund_tasks import start,cancel
                    if data.get('action') not in (None,'cancel'):raise ValueError('Kies een geldige ETF-taak.')
                    result=cancel(store) if data.get('action')=='cancel' else start(store,cache,data.get('mode','all'))
                    return self.respond(result,202)
                if path=='/api/instrument/holdings':
                    from fund_holdings import refresh
                    key=instruments.owned_key(store,data,data.get('account_id','all'))
                    with refresh_lock:
                        try:result=refresh(store,key,url=data.get('source_url'),as_of=data.get('as_of',''),content=data.get('csv'))
                        except (OSError,UnicodeError):return self.respond({'error':'ETF-bron ophalen mislukt. Opgeslagen samenstelling blijft behouden.'},503)
                        cache.invalidate()
                    refresh_requested.set()
                    return self.respond(dict(composition=result))
                if path=='/api/instrument/valuation':
                    from valuations import save as save_valuation
                    with refresh_lock:
                        result=save_valuation(store,data);cache.invalidate()
                    refresh_requested.set()
                    return self.respond(result)
                if path=='/api/portfolio/settlement':
                    from valuations import settle
                    with refresh_lock:
                        result=settle(store,data);cache.invalidate()
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
                    with store.lock:
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
                        if action in ('save','forget'):self.confirm_sensitive(user)
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
                if path in ('/api/accounts/edit','/api/accounts/delete'):
                    try:
                        with broker_accounts.mutation(store,trading212_api._lock):
                            if path.endswith('/edit'):result=broker_accounts.edit(store,data)
                            else:result=transactions.reset(store,data,remove_account=True)
                            cache.invalidate()
                    except broker_accounts.BusyAccountError as error:return self.respond({'error':str(error)},409)
                    except OSError:return self.respond({'error':'De rekening kon niet veilig worden verwijderd. Controleer de back-up en probeer opnieuw.'},500)
                    if path.endswith('/delete'):refresh_requested.set()
                    return self.respond(result)
                if path=='/api/accounts':
                    store.add_account(data);cache.invalidate();return self.respond({'ok':True},201)
                if path=='/api/imports/mappings':return self.respond(mapping_edit(store,data))
                if path=='/api/charges/fx':
                    from charges import refresh_fx
                    result=refresh_fx(store,data.get('account_id','all'),data.get('year',''),data.get('currency',''),data.get('view','all'));cache.invalidate();return self.respond(result)
                if path=='/api/charges/save':
                    import csv,io
                    from imports.charge_csv import FIELDS,parse_csv as parse_charge_csv
                    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerow({key:str(data.get(key,'')) for key in FIELDS})
                    parsed=parse_charge_csv(stream.getvalue())
                    if parsed[0].get('error'):raise ValueError(parsed[0]['error'])
                    batch=import_preview(store,int(data['account_id']),'charges','manual-charge.csv',stream.getvalue())
                    result=commit_partial(store,batch['batch_id']);cache.invalidate();refresh_requested.set();return self.respond(result)
                if path=='/api/imports/preview':
                    result=import_preview(store,int(data['account_id']),str(data['provider']),str(data['filename']),str(data['csv']))
                    return self.respond(result)
                if path=='/api/imports/commit':
                    result=commit_partial(store,int(data['batch_id']));cache.invalidate();refresh_requested.set();return self.respond(result)
                if path=='/api/imports/issues/resolve':
                    result=resolve_issue(store,data);cache.invalidate();refresh_requested.set();return self.respond(result)
                if path=='/api/imports/resolve':return self.respond(resolve_instrument(store,int(data['batch_id']),str(data['key'])))
                if path=='/api/imports/open':return self.respond(open_preview(store,int(data['batch_id'])))
                if path=='/api/passkey/login/begin':
                    if not auth.enabled():raise ValueError('Schakel gebruikersbeveiliging in.')
                    return self.respond(passkeys.begin_login(store,self.headers.get('Origin','')))
                if path=='/api/passkey/login/finish':
                    token=passkeys.finish_login(store,auth,data.get('ceremony_id'),data.get('credential'))
                    return self.respond({'ok':True},cookie=self.cookie(token))
                if path=='/api/passkey/register/begin':
                    result=passkeys.begin_registration(store,user,self.token(),data.get('password',''),self.headers.get('Origin',''))
                    return self.respond(result)
                if path=='/api/passkey/register/finish':
                    return self.respond(passkeys.finish_registration(store,user,self.token(),data.get('ceremony_id'),data.get('credential'),data.get('label','')))
                if path=='/api/passkey/delete':
                    return self.respond(passkeys.delete_key(store,user,data.get('id'),data.get('password','')))
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
            except sqlite3.OperationalError as error:
                # A busy database may have accepted an earlier write. Do not
                # automatically retry a financial POST or record into the locked DB.
                busy = getattr(error, 'sqlite_errorcode', None) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                busy = busy or 'locked' in str(error).lower() or 'busy' in str(error).lower()
                if busy:
                    return self.respond({'error':'Database is tijdelijk bezet. Controleer eerst of de transactie is opgeslagen voordat je opnieuw probeert.'},503)
                record(store,'ERROR','web','request_failed','Aanvraag kon niet worden verwerkt.',{'endpoint':path})
                return self.respond({'error':'Aanvraag mislukt. Controleer de gegevens en probeer opnieuw.'},400)
            except (KeyError,TypeError,sqlite3.Error):
                record(store,'ERROR','web','request_failed','Aanvraag kon niet worden verwerkt.',{'endpoint':path})
                self.respond({'error':'Aanvraag mislukt. Controleer velden, wachtwoord (12–128 tekens), rollen of het back-upbestand.'},400)
    if enable_demo:
        from demo import profile_handler
        from cache import StateCache
        import threading
        return profile_handler(Handler,store,auth,lambda demo:make_handler(demo,auth,StateCache(store=demo),{'message':'Voorbeeldportefeuille · providerkoersen mogelijk vertraagd · fictieve transacties en historie','last_attempt':None},interval,threading.Lock(),threading.Event(),None,enable_demo=False))
    return Handler
