"""Short SQLite transactions; no network calls inside database transactions."""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager,closing
from pathlib import Path
from uuid import UUID, uuid4


class Rejected(Exception):
    def __init__(self, code, status=400, retry_after=0):
        self.code, self.status, self.retry_after = code, status, retry_after
        super().__init__(code)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def validate_submission(data):
    if not isinstance(data, dict) or set(data) != {'request_id', 'kind', 'title', 'description', 'version'}:
        raise Rejected('invalid_submission')
    try:
        if str(UUID(data['request_id'])) != data['request_id']: raise ValueError()
    except (ValueError, TypeError, AttributeError): raise Rejected('invalid_submission') from None
    if data['kind'] not in ('wish', 'bug'): raise Rejected('invalid_submission')
    for key, maximum in (('title', 120), ('description', 4000), ('version', 24)):
        value = data[key]
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
            raise Rejected('invalid_submission')
        if any(ord(c) < 32 and c not in '\n\t' for c in value): raise Rejected('invalid_submission')
    if '\n' in data['title'] or not re.fullmatch(r'\d+\.\d+\.\d+', data['version']):
        raise Rejected('invalid_submission')
    return {key: value.strip() for key, value in data.items()}


class RelayStore:
    def __init__(self, path, secret):
        self.path, self.secret = Path(path), secret
        if len(secret) < 32: raise ValueError('service_secret_too_short')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.db() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1): raise ValueError('unsupported_schema')
            if version == 0:
                db.executescript('''
                    CREATE TABLE invitations(hash TEXT PRIMARY KEY,expires REAL NOT NULL,installation TEXT);
                    CREATE TABLE installations(id TEXT PRIMARY KEY,credential_hash TEXT UNIQUE NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL);
                    CREATE TABLE limits(key TEXT PRIMARY KEY,count INTEGER NOT NULL,expires REAL NOT NULL);
                    CREATE TABLE jobs(id TEXT PRIMARY KEY,installation TEXT NOT NULL,request_id TEXT NOT NULL,payload_hash TEXT NOT NULL,payload TEXT NOT NULL,title TEXT NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,number INTEGER UNIQUE,created REAL NOT NULL,UNIQUE(installation,request_id));
                    CREATE INDEX queue ON jobs(state,created);
                    CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                    CREATE TABLE deliveries(id TEXT PRIMARY KEY,created REAL NOT NULL);
                    PRAGMA user_version=1;
                ''')
        with closing(sqlite3.connect(self.path)) as db: db.execute('PRAGMA journal_mode=WAL')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally: db.close()

    def keyed_hash(self, value):
        return hmac.new(self.secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def consume(db, key, maximum, seconds):
        now = time.time()
        db.execute('DELETE FROM limits WHERE expires<?', (now,))
        row = db.execute('SELECT count,expires FROM limits WHERE key=?', (key,)).fetchone()
        if row and row['count'] >= maximum: raise Rejected('rate_limited', 429, max(1, int(row['expires']-now)+1))
        if row: db.execute('UPDATE limits SET count=count+1 WHERE key=?', (key,))
        else: db.execute('INSERT INTO limits VALUES(?,1,?)', (key,now+seconds))

    def throttle(self, address, scope='requests', maximum=6000):
        # Committed independently, so rejected requests also consume capacity.
        with self.db() as db: self.consume(db, scope+':ip:'+self.keyed_hash(address), maximum, 3600)

    def invite(self, ttl=86400):
        if not 60 <= ttl <= 604800: raise ValueError('invalid_expiry')
        code = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('DELETE FROM invitations WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO invitations VALUES(?,?,NULL)', (self.keyed_hash(code),time.time()+ttl))
        return code

    def enroll(self, code, credential):
        if not isinstance(code,str) or not isinstance(credential,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',credential):
            raise Rejected('invalid_activation',403)
        with self.db() as db:
            row = db.execute('SELECT * FROM invitations WHERE hash=?', (self.keyed_hash(code),)).fetchone()
            if not row or row['expires'] < time.time(): raise Rejected('invalid_activation',403)
            if row['installation']:
                existing = db.execute('SELECT * FROM installations WHERE id=?', (row['installation'],)).fetchone()
                if existing and not existing['revoked'] and hmac.compare_digest(existing['credential_hash'],digest(credential)):
                    return existing['id']
                raise Rejected('invalid_activation',403)
            self.consume(db,'enroll:global',100,3600)
            identity = str(uuid4())
            db.execute('INSERT INTO installations VALUES(?,?,0,?)',(identity,digest(credential),time.time()))
            db.execute('UPDATE invitations SET installation=? WHERE hash=?',(identity,self.keyed_hash(code)))
            return identity

    def authenticate(self, credential):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',credential): raise Rejected('unauthorized',401)
        with self.db() as db:
            row = db.execute('SELECT id FROM installations WHERE credential_hash=? AND revoked=0',(digest(credential),)).fetchone()
            if not row: raise Rejected('unauthorized',401)
            return row['id']

    def submit(self, installation, data):
        data = validate_submission(data)
        payload = json.dumps(data,sort_keys=True,separators=(',',':'))
        with self.db() as db:
            active=db.execute('SELECT 1 FROM installations WHERE id=? AND revoked=0',(installation,)).fetchone()
            if not active: raise Rejected('unauthorized',401)
            old = db.execute('SELECT id,payload_hash,state FROM jobs WHERE installation=? AND request_id=?',(installation,data['request_id'])).fetchone()
            if old:
                if old['payload_hash'] != digest(payload): raise Rejected('idempotency_conflict',409)
                return {'id':old['id'],'state':old['state']}
            self.consume(db,'send:'+installation,5,86400)
            self.consume(db,'send:global',200,86400)
            if db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','sending','uncertain')").fetchone()[0]>=1000:
                raise Rejected('queue_full',503,3600)
            identity=str(uuid4())
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,\'queued\',NULL,?)',(identity,installation,data['request_id'],digest(payload),payload,data['title'],data['kind'],time.time()))
            return {'id':identity,'state':'queued'}

    def mine(self, installation):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT id,request_id,state,number FROM jobs WHERE installation=? ORDER BY created DESC LIMIT 100',(installation,))]

    def revoke(self, identity):
        with self.db() as db:
            if not db.execute('SELECT 1 FROM installations WHERE id=?',(identity,)).fetchone(): raise Rejected('not_found',404)
            db.execute('UPDATE installations SET revoked=1 WHERE id=?',(identity,))
            db.execute("UPDATE jobs SET state='blocked',payload='' WHERE installation=? AND state='queued'",(identity,))

    def recover(self):
        # A crash after GitHub accepted a POST has an ambiguous outcome. Never POST it again automatically.
        with self.db() as db: db.execute("UPDATE jobs SET state='uncertain' WHERE state='sending'")

    def claim(self):
        with self.db() as db:
            db.execute("UPDATE jobs SET state='blocked',payload='' WHERE state='queued' AND created<?",(time.time()-30*86400,))
            row=db.execute("SELECT jobs.* FROM jobs JOIN installations ON jobs.installation=installations.id WHERE state='queued' AND revoked=0 ORDER BY created LIMIT 1").fetchone()
            if row: db.execute("UPDATE jobs SET state='sending' WHERE id=?",(row['id'],))
            return dict(row) if row else None

    def prune(self):
        with self.db() as db:
            cutoff=time.time()-30*86400
            db.execute("UPDATE jobs SET state='blocked',payload='' WHERE state='queued' AND created<?",(cutoff,))
            db.execute("UPDATE jobs SET payload='' WHERE state='uncertain' AND created<? AND payload<>''",(cutoff,))

    def mark(self, identity, state, number=None):
        with self.db() as db:
            db.execute('UPDATE jobs SET state=?,number=COALESCE(?,number),payload=CASE WHEN ? IN (\'open\',\'closed\',\'blocked\') THEN \'\' ELSE payload END WHERE id=?',(state,number,state,identity))

    def get_meta(self, key, default=None):
        with self.db() as db:
            row=db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
            return json.loads(row['value']) if row else default

    def set_meta(self, key, value):
        with self.db() as db: db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,json.dumps(value)))

    def webhook(self, delivery, number, state):
        with self.db() as db:
            db.execute('DELETE FROM deliveries WHERE created<?',(time.time()-7*86400,))
            if db.execute('SELECT 1 FROM deliveries WHERE id=?',(delivery,)).fetchone(): return
            db.execute('INSERT INTO deliveries VALUES(?,?)',(delivery,time.time()))
            if state in ('open','closed'):
                db.execute("UPDATE jobs SET state=? WHERE number=? AND state IN ('open','closed')",(state,number))
            db.execute("INSERT OR REPLACE INTO meta VALUES('board_due','0')")
