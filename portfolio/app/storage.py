"""Persistent ledger and quotes; amounts are stored as decimal strings."""
import sqlite3
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from contextlib import contextmanager, closing

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
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, exchange TEXT NOT NULL,
                    name TEXT NOT NULL, quantity TEXT NOT NULL, price TEXT NOT NULL,
                    currency TEXT NOT NULL, purchased_on TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, exchange TEXT NOT NULL,
                    currency TEXT NOT NULL, price TEXT NOT NULL, quoted_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL, source TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS quote_instrument ON quotes(symbol,exchange,currency,id);
                PRAGMA user_version=1;
            ''')

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

    def state(self):
        with self.connect() as db:
            purchases = [dict(row) for row in db.execute('SELECT * FROM purchases ORDER BY purchased_on,id')]
            quotes = [dict(row) for row in db.execute('SELECT * FROM quotes ORDER BY quoted_at,id')]
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
            value = group['quantity'] * Decimal(group['quote']['price']) if group['quote'] else None
            positions.append({**group, 'quantity': str(group['quantity']), 'cost': str(group['cost']),
                              'value': str(value) if value is not None else None,
                              'gain': str(value - group['cost']) if value is not None else None})
        return dict(purchases=purchases, positions=positions, quotes=quotes)

    def backup(self):
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        path = folder / ('portfolio-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.sqlite3')
        with self.connect() as source, closing(sqlite3.connect(path)) as target:
            source.backup(target)
        for old in sorted(folder.glob('portfolio-*.sqlite3'))[:-30]:
            old.unlink()
        return path
