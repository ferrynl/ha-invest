"""HTTP boundary: authorization is enforced here, independent of page visibility."""
import hashlib
import hmac
import json
import re
import sqlite3
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from provider import search_stocks
from restore import restore_backup
from security import verify_password
from version import APP_VERSION
from updates import check_updates
from imports import ADAPTERS
from imports.service import preview as import_preview,commit as import_commit
from history import portfolio_values

def make_handler(store,auth,cache,status,interval,refresh_lock,refresh_requested):
    static=Path(__file__).parent/'static'
    assets={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css')}
    for name in ('app','pages','chart','chart-view','access','imports'):
        assets['/'+name+'.js']=(name+'.js','text/javascript')
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
            return f'homeinvest_session={token}; Path={path}; HttpOnly; SameSite=Strict; Max-Age={28800 if token else 0}'+('; Secure' if secure else '')
        def respond(self,content,code=200,kind='application/json',filename=None,cookie=None,etag=False,public=False):
            if kind=='application/json':content=json.dumps(content,separators=(',',':')).encode()
            digest='"'+hashlib.sha256(content).hexdigest()+'"' if etag else None
            if digest and self.headers.get('If-None-Match')==digest:code=304;content=b''
            self.send_response(code)
            self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)))
            self.send_header('Cache-Control','private, max-age=86400, immutable' if public else 'no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'")
            if digest:self.send_header('ETag',digest)
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
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
                if path=='/':content=content.replace(b'__ASSET_VERSION__',APP_VERSION.encode())
                return self.respond(content,kind=kind,etag=path!='/',public=path!='/')
            user=auth.user(self.token())
            if path=='/api/session':return self.respond({'enabled':auth.enabled(),'user':user})
            if not self.allowed(user,admin=path in ('/api/users','/api/backup','/api/imports')):return
            if path=='/api/users':return self.respond({'users':auth.list_users()})
            if path=='/api/imports':
                with store.connect() as db:batches=[dict(r) for r in db.execute('SELECT id,account_id,provider,filename,status,created_at FROM import_batches ORDER BY id DESC LIMIT 50')]
                return self.respond({'providers':[{'id':key,'name':value['name'],'formats':value['formats']} for key,value in ADAPTERS.items()],'batches':batches})
            if path=='/api/state':
                state=cache.get(store.state)
                account=parse_qs(urlsplit(self.path).query).get('account_id',['all'])[0]
                if account!='all':
                    try:account_id=int(account)
                    except ValueError:return self.respond({'error':'Ongeldig brokeraccount.'},400)
                    if not any(a['id']==account_id for a in state['accounts']):return self.respond({'error':'Brokeraccount niet gevonden.'},404)
                    state={**state,**{key:[r for r in state[key] if r['account_id']==account_id] for key in ('purchases','dividends','positions')}}
                    state['portfolios']=portfolio_values(state['positions'])
                # Raw quote observations are used internally; daily histories and
                # the latest quote are enough for the dashboard.
                return self.respond({**{k:v for k,v in state.items() if k!='quotes'},'status':status,'refresh_minutes':interval//60,'app_version':APP_VERSION},etag=True)
            if path=='/api/backup':
                backup=store.backup();return self.respond(backup.read_bytes(),kind='application/vnd.sqlite3',filename=backup.name)
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
            if path!='/api/auth/login':
                if not self.allowed(user,admin=path in ('/api/settings','/api/restore','/api/users','/api/auth/enable','/api/auth/disable','/api/accounts','/api/updates') or path.startswith('/api/imports/')):return
                if auth.enabled() and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf'] or ''):
                    return self.respond({'error':'Ongeldige sessiebeveiliging. Meld je opnieuw aan.'},403)
            try:
                if path=='/api/restore':
                    if self.headers.get('X-Confirm-Restore')!='yes':raise ValueError('Bevestig het terugzetten van de portefeuille.')
                    with refresh_lock:
                        result=restore_backup(store,body);cache.invalidate()
                        with auth.lock:auth.sessions.clear()
                    refresh_requested.set()
                    return self.respond({'ok':True,'restored':result},cookie=self.cookie(''))
                data=json.loads(body)
                if not isinstance(data,dict):raise ValueError('Ongeldige aanvraag.')
                if path=='/api/updates':
                    try:return self.respond(check_updates(store))
                    except Exception:return self.respond({'error':'Versiecontrole niet beschikbaar. Probeer later opnieuw of bekijk GitHub.'},502)
                if path=='/api/accounts':
                    store.add_account(data);cache.invalidate();return self.respond({'ok':True},201)
                if path=='/api/imports/preview':
                    result=import_preview(store,int(data['account_id']),str(data['provider']),str(data['filename']),str(data['csv']))
                    return self.respond(result)
                if path=='/api/imports/commit':
                    result=import_commit(store,int(data['batch_id']),data['mappings']);cache.invalidate();refresh_requested.set();return self.respond(result)
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
                    with auth.lock:auth.sessions.clear()
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
            except ValueError as error:self.respond({'error':str(error)},400)
            except (KeyError,TypeError,sqlite3.Error):
                self.respond({'error':'Aanvraag mislukt. Controleer velden, wachtwoord (12–128 tekens), rollen of het back-upbestand.'},400)
    return Handler
