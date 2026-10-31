"""Persistent ledger and quotes; amounts are stored as decimal strings."""
import sqlite3
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from uuid import uuid4
from threading import RLock
from contextlib import contextmanager, closing
from history import daily_values, with_dividends, portfolio_values
from migrations import migrate, SCHEMA_VERSION

def now():
    return datetime.now(timezone.utc).isoformat()

def positive(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > Decimal('1e15'):
            raise ValueError('Gebruik een positief getal kleiner dan 10^15.')
        return str(number)
    except InvalidOperation as exc:
        raise ValueError('Ongeldig getal; gebruik een punt als decimaalteken.') from exc

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'portfolio.sqlite3'
        self.lock = RLock()
        migrate(self.path)

    @contextmanager
    def connect(self):
        with self.lock:
            with self._connect() as db:
                yield db

    @contextmanager
    def read(self):
        # SQLite gives readers a committed snapshot. A provider request holding
        # the application writer lock must not block cached dashboard reads.
        with self._connect() as db:yield db

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, data):
        symbol = str(data.get('symbol', '')).strip().upper()
        exchange = str(data.get('exchange', '')).strip().upper()
        currency = str(data.get('currency', '')).strip().upper()
        name = str(data.get('name', '')).strip()
        if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}', symbol) or not re.fullmatch(r'[A-Z0-9 _-]{1,40}', exchange):
            raise ValueError('Vul een geldig symbool en een beurs in.')
        if not re.fullmatch(r'[A-Z]{3}', currency) or not 1 <= len(name) <= 100:
            raise ValueError('Vul een naam en drieletterige valutacode in.')
        day = date.fromisoformat(data['purchased_on'])
        if day > date.today():
            raise ValueError('Aankoopdatum mag niet in de toekomst liggen.')
        with self.connect() as db:
            account_id=int(data.get('account_id',1));self.require_account(db,account_id)
            side=data.get('side','BUY')
            if side not in ('BUY','SELL'):raise ValueError('Ongeldig transactietype.')
            trade_time=str(data.get('trade_time',''))
            if trade_time:datetime.fromisoformat(trade_time.replace('Z','+00:00'))
            db.execute('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (symbol, exchange, name, positive(data['quantity']), positive(data['price']), currency, day.isoformat(), now(),account_id,side,trade_time))
            if side=='SELL':
                lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(account_id,symbol,exchange,currency))]
                daily_values(lots,[],[])

    @staticmethod
    def require_account(db,account_id):
        if not db.execute('SELECT 1 FROM broker_accounts WHERE id=?',(account_id,)).fetchone():raise ValueError('Brokeraccount niet gevonden.')

    def add_account(self,data):
        name=str(data.get('name','')).strip();broker=str(data.get('broker','')).strip()
        if not 1<=len(name)<=80 or not 1<=len(broker)<=80:raise ValueError('Vul een accountnaam en bedrijf in (maximaal 80 tekens).')
        with self.connect() as db:
            db.execute('INSERT INTO broker_accounts(name,broker,created_at) VALUES(?,?,?)',(name,broker,now()))

    def quote(self, symbol, exchange, currency, price, timestamp, source):
        stamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Koerstijd mist tijdzone.')
        with self.connect() as db:
            db.execute('INSERT INTO quotes VALUES(NULL,?,?,?,?,?,?,?)',
                       (symbol, exchange, currency, positive(price), stamp.isoformat(), now(), source))

    def add_dividend(self, data):
        symbol, exchange, currency = (str(data.get(k, '')).strip().upper() for k in ('symbol', 'exchange', 'currency'))
        day = date.fromisoformat(data['paid_on'])
        amount = positive(data['amount'])
        note = str(data.get('note', '')).strip()
        if day > date.today() or len(note) > 200:
            raise ValueError('Controleer betaaldatum en notitie.')
        with self.connect() as db:
            account_id=int(data.get('account_id',1));self.require_account(db,account_id)
            lot = db.execute('SELECT MIN(purchased_on) AS first FROM purchases WHERE symbol=? AND exchange=? AND currency=? AND account_id=?',
                             (symbol, exchange, currency,account_id)).fetchone()
            if not lot['first'] or day.isoformat() < lot['first']:
                raise ValueError('Kies een bestaand aandeel en een betaaldatum vanaf de eerste aankoop.')
            db.execute('INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at,account_id) VALUES(?,?,?,?,?,?,?,?)',
                       (symbol, exchange, currency, amount, day.isoformat(), note, now(),account_id))

    def state(self):
        with self.read() as db:
            db.execute('BEGIN')
            revision=db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]
            settings=dict(db.execute("SELECT key,value FROM app_settings WHERE key NOT LIKE 'dashboard_layout:%'"))
            purchases = [dict(row) for row in db.execute('SELECT * FROM purchases ORDER BY purchased_on,id')]
            quotes = [dict(row) for row in db.execute('SELECT * FROM quotes ORDER BY quoted_at,id')]
            daily = [dict(row) for row in db.execute('SELECT * FROM daily_prices ORDER BY day')]
            dividends = [dict(row) for row in db.execute('SELECT * FROM dividends ORDER BY paid_on,id')]
            charges=[dict(r) for r in db.execute('SELECT id,account_id,category,amount,currency,paid_on,included_in_net FROM charges ORDER BY paid_on,id')]
            accounts=[dict(r) for r in db.execute('SELECT * FROM broker_accounts ORDER BY id')]
            categories=[dict(r) for r in db.execute('SELECT * FROM instrument_categories')]
            manual=[dict(r) for r in db.execute('SELECT * FROM instrument_valuations')]
        from valuations import apply_final_prices,missing_diagnostics
        quotes,daily=apply_final_prices(quotes,daily,manual)
        category_map={(r['symbol'],r['exchange'],r['currency']):r for r in categories}
        account_names={a['id']:a for a in accounts}
        for row in purchases:row['account_name']=account_names[row['account_id']]['name']
        groups = {}
        for p in purchases:
            key = (p['account_id'],p['symbol'], p['exchange'], p['currency'])
            account=account_names[p['account_id']]
            groups.setdefault(key,dict(account_id=key[0],symbol=key[1],exchange=key[2],currency=key[3],categories=category_map.get((key[1],key[2],key[3]),{}),name=p['name'],account_name=account['name'],broker=account['broker'],quote=None))
        # Index once instead of scanning every price/payment for every holding.
        listing=lambda row:tuple(row[k] for k in ('symbol','exchange','currency'))
        purchases_by_position={};daily_by_listing={};quotes_by_listing={};income_by_position={}
        for row in purchases:purchases_by_position.setdefault((row['account_id'],*listing(row)),[]).append(row)
        for row in daily:daily_by_listing.setdefault(listing(row),[]).append(row)
        for row in quotes:quotes_by_listing.setdefault(listing(row),[]).append(row)
        for row in dividends:income_by_position.setdefault((row['account_id'],*listing(row)),[]).append(row)
        positions = []
        for key,group in groups.items():
            instrument=key[1:];observations=quotes_by_listing.get(instrument,[])
            group['quote']=observations[-1] if observations else None
            chart = daily_values(purchases_by_position[key],daily_by_listing.get(instrument,[]),observations)
            income = income_by_position.get(key,[])
            chart = with_dividends(chart, income)
            received = sum((Decimal(d['amount']) for d in income), Decimal(0))
            last=chart[-1];quantity,cost,realised=Decimal(last['quantity']),Decimal(last['cost']),Decimal(last['realised'])
            value = quantity * Decimal(group['quote']['price']) if group['quote'] else (Decimal(0) if not quantity else None)
            positions.append({**group, 'dividend': str(received), 'realised':str(realised),'total_gain': str(value - cost +realised+ received) if value is not None else None,
                              'history': chart, 'quantity': str(quantity), 'cost': str(cost),
                              'value': str(value) if value is not None else None,
                              'gain': str(value - cost+realised) if value is not None else None})
        missing_diagnostics(self,positions)
        return dict(charges=charges,instrument_categories=categories,purchases=purchases, positions=positions, quotes=quotes, dividends=dividends, portfolios=portfolio_values(positions),
                    accounts=accounts,settings=settings, database_version=SCHEMA_VERSION,data_revision=revision)

    def history_start(self,symbol,exchange,currency,start):
        with self.connect() as db:
            sync=db.execute('SELECT start FROM history_sync WHERE symbol=? AND exchange=? AND currency=?',(symbol,exchange,currency)).fetchone()
            last=db.execute('SELECT MAX(day) FROM daily_prices WHERE symbol=? AND exchange=? AND currency=?',(symbol,exchange,currency)).fetchone()[0]
        if not sync or sync['start']>start or not last:return start
        from datetime import timedelta
        return max(start,(date.fromisoformat(last)-timedelta(days=7)).isoformat())

    def settings(self):
        with self.read() as db:
            return dict(db.execute('SELECT key,value FROM app_settings').fetchall())

    def save_settings(self, data):
        value = data.get('default_range')
        if value not in ('1W','1M','3M','6M','YTD','1Y','ALL'):
            raise ValueError('Ongeldige standaardperiode.')
        with self.connect() as db:
            db.execute("UPDATE app_settings SET value=? WHERE key='default_range'", (value,))

    def history_needed(self, symbol, exchange, currency, start):
        with self.connect() as db:
            row = db.execute('SELECT start,synced_on FROM history_sync WHERE symbol=? AND exchange=? AND currency=?',
                             (symbol, exchange, currency)).fetchone()
        return not row or row['start'] > start or row['synced_on'] != date.today().isoformat()

    def save_history(self, symbol, exchange, currency, start, rows):
        validated = [(symbol, exchange, currency, date.fromisoformat(r['day']).isoformat(), positive(r['price'])) for r in rows]
        with self.connect() as db:
            db.executemany('INSERT OR REPLACE INTO daily_prices VALUES(?,?,?,?,?)', validated)
            db.execute('INSERT OR REPLACE INTO history_sync VALUES(?,?,?,?,?)',
                       (symbol, exchange, currency, min(start,db.execute('SELECT COALESCE(MIN(start),?) FROM history_sync WHERE symbol=? AND exchange=? AND currency=?',(start,symbol,exchange,currency)).fetchone()[0]), date.today().isoformat()))

    def backup(self):
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        path = folder / ('portfolio-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-' + uuid4().hex[:8] + '.sqlite3')
        with self.connect() as source, closing(sqlite3.connect(path)) as target:
            source.backup(target)
        for old in sorted(folder.glob('portfolio-*.sqlite3'))[:-30]:
            old.unlink()
        return path
