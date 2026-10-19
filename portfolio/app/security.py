"""Password hashing, expiring server-side sessions and account administration."""
import hashlib
import hmac
import secrets
import re
import time
from threading import RLock
from datetime import datetime, timezone

ITERATIONS = 600_000
def password_hash(password):
    if not isinstance(password,str) or not 12 <= len(password) <= 128:
        raise ValueError('Gebruik een wachtwoord van 12 tot 128 tekens.')
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'

def verify_password(password, encoded):
    try:
        algorithm,rounds,salt,digest=encoded.split('$')
        if algorithm!='pbkdf2_sha256' or int(rounds)!=ITERATIONS or not isinstance(password,str) or len(password)>128:return False
        candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),int(rounds)).hex()
        return hmac.compare_digest(candidate,digest)
    except (ValueError,TypeError):return False

def username_value(value):
    value=str(value).strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,40}',value):raise ValueError('Gebruikersnaam: 3–40 letters, cijfers, punt, streepje of underscore.')
    return value

class Auth:
    def __init__(self,store):
        self.store=store
        self.lock=RLock()
        self.sessions={}
        self.failures={}
        self.dummy=password_hash(secrets.token_urlsafe(32))

    def enabled(self):return self.store.settings().get('auth_enabled')=='true'

    def user(self,token):
        if not self.enabled():return {'id':None,'username':'Home Assistant','role':'admin','csrf':None}
        key=hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            entry=self.sessions.get(key)
            if not entry:return None
            now=time.monotonic()
            if now-entry['seen']>1800 or now-entry['created']>28800:
                self.sessions.pop(key,None);return None
            with self.store.connect() as db:row=db.execute('SELECT id,username,role,active,revision FROM users WHERE id=?',(entry['user_id'],)).fetchone()
            if not row or not row['active'] or row['revision']!=entry['revision']:
                self.sessions.pop(key,None);return None
            entry['seen']=now
            return dict(id=row['id'],username=row['username'],role=row['role'],csrf=entry['csrf'])

    def login(self,username,password,peer):
        username=str(username).strip().lower()
        now=time.monotonic()
        with self.lock:
            self.failures={k:[t for t in ts if now-t<900] for k,ts in self.failures.items() if any(now-t<900 for t in ts)}
            keys=[('name',username),('peer',peer)]
            if any(len(self.failures.get(k,[]))>=10 for k in keys):raise PermissionError('Te veel inlogpogingen. Probeer over 15 minuten opnieuw.')
            with self.store.connect() as db:row=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            valid=verify_password(password,row['password_hash'] if row else self.dummy)
            if not valid or not row or not row['active']:
                for k in keys:self.failures.setdefault(k,[]).append(now)
                raise ValueError('Gebruikersnaam of wachtwoord onjuist.')
            self.failures.pop(('name',username),None)
            token=secrets.token_urlsafe(32)
            self.sessions={k:s for k,s in self.sessions.items() if now-s['seen']<=1800 and now-s['created']<=28800}
            if len(self.sessions)>=1000:raise PermissionError('Te veel actieve sessies.')
            self.sessions[hashlib.sha256(token.encode()).hexdigest()]=dict(user_id=row['id'],revision=row['revision'],created=now,seen=now,csrf=secrets.token_urlsafe(32))
            return token

    def logout(self,token):
        with self.lock:self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(),None)

    def enable(self,username,password):
        username=username_value(username);encoded=password_hash(password)
        with self.store.connect() as db:
            if db.execute("SELECT value FROM app_settings WHERE key='auth_enabled'").fetchone()[0]=='true':raise ValueError('Gebruikersbeveiliging is al ingeschakeld.')
            if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                row=db.execute("SELECT password_hash FROM users WHERE username=? AND role='admin' AND active=1",(username,)).fetchone()
                if not row or not verify_password(password,row['password_hash']):raise ValueError('Gebruik een bestaand actief adminaccount om opnieuw in te schakelen.')
            else:db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',(username,encoded,'admin',datetime.now(timezone.utc).isoformat()))
            db.execute("UPDATE app_settings SET value='true' WHERE key='auth_enabled'")

    def list_users(self):
        with self.store.connect() as db:return [dict(r) for r in db.execute('SELECT id,username,role,active FROM users ORDER BY username')]

    def save_user(self,data):
        role=data.get('role')
        if role not in ('admin','basic'):raise ValueError('Ongeldige rol.')
        active=data.get('active',True)
        if not isinstance(active,bool):raise ValueError('Ongeldige accountstatus.')
        user_id=data.get('id')
        encoded=password_hash(data['password']) if data.get('password') else None
        with self.store.connect() as db:
            if user_id is None:
                if not encoded:raise ValueError('Wachtwoord is verplicht.')
                username=username_value(data.get('username',''))
                if db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():raise ValueError('Gebruikersnaam bestaat al.')
                db.execute('INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)',(username,encoded,role,int(active),datetime.now(timezone.utc).isoformat()))
            else:
                row=db.execute('SELECT * FROM users WHERE id=?',(int(user_id),)).fetchone()
                if not row:raise ValueError('Gebruiker niet gevonden.')
                if row['role']=='admin' and row['active'] and (role!='admin' or not active):
                    if db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:raise ValueError('De laatste actieve admin moet behouden blijven.')
                db.execute('UPDATE users SET role=?,active=?,password_hash=?,revision=revision+1 WHERE id=?',(role,int(active),encoded or row['password_hash'],row['id']))

    def change_password(self,user_id,current,new,username=None):
        with self.store.connect() as db:row=db.execute('SELECT password_hash FROM users WHERE id=?',(user_id,)).fetchone()
        if not row or not verify_password(current,row['password_hash']):raise ValueError('Huidig wachtwoord onjuist.')
        encoded=password_hash(new) if new else row['password_hash']
        with self.store.connect() as db:
            if username is not None:
                name=username_value(username)
                if db.execute('SELECT 1 FROM users WHERE username=? AND id!=?',(name,user_id)).fetchone():raise ValueError('Gebruikersnaam bestaat al.')
                db.execute('UPDATE users SET username=?,password_hash=?,revision=revision+1 WHERE id=?',(name,encoded,user_id))
            else:db.execute('UPDATE users SET password_hash=?,revision=revision+1 WHERE id=?',(encoded,user_id))
