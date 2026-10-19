"""Persistent ledger and quotes; amounts are stored as decimal strings."""
import sqlite3
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from uuid import uuid4
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
        migrate(self.path)

    @contextmanager
    def connect(self):
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
            db.execute('INSERT INTO purchases VALUES(NULL,?,?,?,?,?,?,?,?)',
                       (symbol, exchange, name, positive(data['quantity']), positive(data['price']), currency, day.isoformat(), now()))

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
            lot = db.execute('SELECT MIN(purchased_on) AS first FROM purchases WHERE symbol=? AND exchange=? AND currency=?',
                             (symbol, exchange, currency)).fetchone()
            if not lot['first'] or day.isoformat() < lot['first']:
                raise ValueError('Kies een bestaand aandeel en een betaaldatum vanaf de eerste aankoop.')
            db.execute('INSERT INTO dividends VALUES(NULL,?,?,?,?,?,?,?)',
                       (symbol, exchange, currency, amount, day.isoformat(), note, now()))

    def state(self):
        with self.connect() as db:
            purchases = [dict(row) for row in db.execute('SELECT * FROM purchases ORDER BY purchased_on,id')]
            quotes = [dict(row) for row in db.execute('SELECT * FROM quotes ORDER BY quoted_at,id')]
            daily = [dict(row) for row in db.execute('SELECT * FROM daily_prices ORDER BY day')]
            dividends = [dict(row) for row in db.execute('SELECT * FROM dividends ORDER BY paid_on,id')]
        groups = {}
        for p in purchases:
            key = (p['symbol'], p['exchange'], p['currency'])
            group = groups.setdefault(key, dict(symbol=key[0], exchange=key[1], currency=key[2], name=p['name'], quantity=Decimal(0), cost=Decimal(0), quote=None))
            group['quantity'] += Decimal(p['quantity'])
            group['cost'] += Decimal(p['quantity']) * Decimal(p['price'])
        for q in quotes:
            key = (q['symbol'], q['exchange'], q['currency'])
            if key in groups:
                groups[key]['quote'] = q
        positions = []
        for group in groups.values():
            def matches(row):
                return all(row[k] == group[k] for k in ('symbol', 'exchange', 'currency'))
            chart = daily_values([p for p in purchases if matches(p)], [d for d in daily if matches(d)], [q for q in quotes if matches(q)])
            income = [d for d in dividends if matches(d)]
            chart = with_dividends(chart, income)
            received = sum((Decimal(d['amount']) for d in income), Decimal(0))
            value = group['quantity'] * Decimal(group['quote']['price']) if group['quote'] else None
            positions.append({**group, 'dividend': str(received), 'total_gain': str(value - group['cost'] + received) if value is not None else None,
                              'history': chart, 'quantity': str(group['quantity']), 'cost': str(group['cost']),
                              'value': str(value) if value is not None else None,
                              'gain': str(value - group['cost']) if value is not None else None})
        return dict(purchases=purchases, positions=positions, quotes=quotes, dividends=dividends, portfolios=portfolio_values(positions),
                    settings=self.settings(), database_version=SCHEMA_VERSION)

    def settings(self):
        with self.connect() as db:
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
                       (symbol, exchange, currency, start, date.today().isoformat()))

    def backup(self):
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        path = folder / ('portfolio-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-' + uuid4().hex[:8] + '.sqlite3')
        with self.connect() as source, closing(sqlite3.connect(path)) as target:
            source.backup(target)
        for old in sorted(folder.glob('portfolio-*.sqlite3'))[:-30]:
            old.unlink()
        return path
