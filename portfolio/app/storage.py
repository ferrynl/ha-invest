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

def valid_position_income(rows):
    valid=[]
    for row in rows:
        try:
            date.fromisoformat(row['paid_on'])
            if Decimal(row['amount']).is_finite():valid.append(row)
        except (ArithmeticError,ValueError,TypeError,KeyError):
            continue
    return valid


class PortfolioRevisionChanged(ValueError):
    pass


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
        if day.year<1900:raise ValueError('Gebruik een transactiedatum vanaf 1900. Controleer het volledige jaartal.')
        if day > date.today():
            raise ValueError('Aankoopdatum mag niet in de toekomst liggen.')
        from charges import manual_components,book_manual_trade
        components=manual_components(data,currency)
        fx_trace=None
        eur_price=str(data.get('price_eur') if data.get('price_eur') is not None else '').strip()
        if eur_price:
            if currency=='EUR':raise ValueError('EUR-invoer is alleen beschikbaar bij een andere handelsvaluta.')
            from forex import convert
            fx_trace=convert(self,positive(eur_price),'EUR',currency,day.isoformat())
            price=positive(fx_trace['converted'])
            if str(data.get('price') if data.get('price') is not None else '').strip() and Decimal(positive(data['price']))!=Decimal(price):raise ValueError('De omrekening is niet actueel. Reken de EUR-prijs opnieuw om.')
        else:price=positive(data['price'])

        with self.connect() as db:
            account_id=int(data.get('account_id',1));self.require_account(db,account_id)
            side=data.get('side','BUY')
            if side not in ('BUY','SELL'):raise ValueError('Ongeldig transactietype.')
            trade_time=str(data.get('trade_time',''))
            if trade_time:datetime.fromisoformat(trade_time.replace('Z','+00:00'))
            trade_id=db.execute('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (symbol, exchange, name, positive(data['quantity']), price, currency, day.isoformat(), now(),account_id,side,trade_time)).lastrowid
            if side=='SELL':
                lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(account_id,symbol,exchange,currency))]
                daily_values(lots,[],[])
            if components or fx_trace:book_manual_trade(db,dict(db.execute('SELECT * FROM purchases WHERE id=?',(trade_id,)).fetchone()),components,fx_trace)

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
        if day.year<1900:raise ValueError('Gebruik een transactiedatum vanaf 1900. Controleer het volledige jaartal.')
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

    def state(self,compact_view=False,account='all'):
        with self.read() as db:
            result=self._state(db,compact_view,account)
        from valuations import missing_diagnostics
        missing_diagnostics(self,result['positions'])
        return result

    def compact_state_with_euro_rates(self,account):
        with self.read() as db:
            snapshot=self._state(db,True,account)
            rates=[dict(row) for row in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR'")]
        return snapshot,rates

    def dividend_state(self,account='all'):
        with self.read() as db:
            return self._state(db,True,account,dividend_history=True)

    def _state(self,db,compact_view,account,dividend_history=False):
        db.execute('BEGIN')
        revision=db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]
        settings=dict(db.execute("SELECT key,value FROM app_settings WHERE key NOT LIKE 'dashboard_layout:%'"))
        purchases = [dict(row) for row in db.execute('SELECT * FROM purchases ORDER BY purchased_on,id')]
        quotes = [] if compact_view else [dict(row) for row in db.execute('SELECT * FROM quotes ORDER BY quoted_at,id')]
        daily = [] if compact_view else [dict(row) for row in db.execute('SELECT * FROM daily_prices ORDER BY day')]
        dividends = [dict(row) for row in db.execute('SELECT * FROM dividends ORDER BY paid_on,id')]
        charges=[dict(r) for r in db.execute('SELECT id,account_id,category,amount,currency,paid_on,included_in_net FROM charges ORDER BY paid_on,id')]
        accounts=[dict(r) for r in db.execute('SELECT * FROM broker_accounts ORDER BY id')]
        categories=[dict(r) for r in db.execute('SELECT * FROM instrument_categories')]
        from fund_holdings import all_saved
        fund_compositions=all_saved(db)
        manual=[dict(r) for r in db.execute('SELECT * FROM instrument_valuations')]
        from valuations import apply_final_prices
        paused={tuple(row) for row in db.execute('SELECT symbol,exchange,currency FROM instrument_quote_pauses')}
        quotes,daily=apply_final_prices(quotes,daily,manual)
        category_map={(r['symbol'],r['exchange'],r['currency']):r for r in categories}
        account_names={a['id']:a for a in accounts}
        for row in purchases:row['account_name']=account_names[row['account_id']]['name']
        groups = {}
        for p in purchases:
            key = (p['account_id'],p['symbol'], p['exchange'], p['currency'])
            broker_account=account_names[p['account_id']]
            groups.setdefault(key,dict(account_id=key[0],symbol=key[1],exchange=key[2],currency=key[3],categories=category_map.get((key[1],key[2],key[3]),{}),name=p['name'],account_name=broker_account['name'],broker=broker_account['broker'],quote=None))
        # Index once instead of scanning every price/payment for every holding.
        listing=lambda row:tuple(row[k] for k in ('symbol','exchange','currency'))
        purchases_by_position={};daily_by_listing={};quotes_by_listing={};income_by_position={}
        for row in purchases:purchases_by_position.setdefault((row['account_id'],*listing(row)),[]).append(row)
        for row in daily:daily_by_listing.setdefault(listing(row),[]).append(row)
        for row in quotes:quotes_by_listing.setdefault(listing(row),[]).append(row)
        for row in dividends:income_by_position.setdefault((row['account_id'],*listing(row)),[]).append(row)
        from history import PortfolioAccumulator
        from dashboard import daily_moves
        accumulator=PortfolioAccumulator() if compact_view and not dividend_history else None
        if account!='all' and not any(str(a['id'])==str(account) for a in accounts):raise LookupError('Brokeraccount niet gevonden.')
        positions = []
        moves_by_listing = {}
        for key,group in groups.items():
            if account!='all' and str(key[0])!=str(account):continue
            instrument=key[1:]
            if compact_view:
                observations,prices=self.history_inputs(db,instrument)
            else:observations=quotes_by_listing.get(instrument,[]);prices=daily_by_listing.get(instrument,[])
            group['quote']=observations[-1] if observations else None
            group['quote_paused']=instrument in paused
            income = valid_position_income(income_by_position.get(key,[]))
            try:
                chart = daily_values(purchases_by_position[key],prices,observations)
                chart = with_dividends(chart, income)
                received = sum((Decimal(d['amount']) for d in income), Decimal(0))
                last=chart[-1];quantity,cost,realised=Decimal(last['quantity']),Decimal(last['cost']),Decimal(last['realised'])
                if not all(number.is_finite() for number in (quantity,cost,realised)):
                    raise ValueError()
                value = quantity * Decimal(group['quote']['price']) if group['quote'] else (Decimal(0) if not quantity else None)
                if value is not None and not value.is_finite():raise ValueError()
                positions.append({**group, 'dividend': str(received), 'realised':str(realised),'total_gain': str(value - cost +realised+ received) if value is not None else None,
                                  'history': chart, 'quantity': str(quantity), 'cost': str(cost),
                                  'value': str(value) if value is not None else None,
                                  'gain': str(value - cost+realised) if value is not None else None})
            except (ArithmeticError,ValueError,TypeError,KeyError,IndexError):
                # Preserve the identity and raw ledger rows for report diagnostics.
                positions.append({**group,'history':[],'invalid_position':True,'quantity':None,
                                  'cost':None,'realised':None,'dividend':None,'value':None,
                                  'gain':None,'total_gain':None})
                continue
            if not dividend_history and quantity > 0 and instrument not in paused:
                if instrument not in moves_by_listing:
                    moves_by_listing[instrument] = daily_moves(db,instrument,group['quote'],prices)
                positions[-1]['daily_moves'] = moves_by_listing[instrument]
            if dividend_history:
                payment_days={row['paid_on'] for row in income_by_position.get(key,[])}
                positions[-1]['history']=[point for point in chart[:-1] if point['day'] in payment_days]+chart[-1:]
            elif accumulator is not None:
                accumulator.add(positions[-1]);positions[-1]['history']=chart[-1:];positions[-1]['history_loaded']=False
        scoped=lambda rows:[r for r in rows if account=='all' or str(r['account_id'])==str(account)]
        result=dict(fund_compositions=fund_compositions,charges=charges,instrument_categories=categories,purchases=scoped(purchases), positions=positions, quotes=[] if compact_view else quotes, dividends=scoped(dividends), portfolios=[] if dividend_history else accumulator.result() if accumulator else portfolio_values(positions),
                    accounts=accounts,settings=settings, database_version=SCHEMA_VERSION,data_revision=revision)
        suspicious=sorted({row['purchased_on'] for row in purchases if row['purchased_on']<'1900-01-01'})
        if suspicious:result['history_date_issues']=suspicious
        if compact_view:result['compact']=True
        return result

    def position_histories(self,snapshot,account='all',skip_invalid=False):
        """Yield a single complete position; never materialise all daily histories."""
        trades={};income={}
        identity=lambda r:tuple(r[k] for k in ('account_id','symbol','exchange','currency'))
        for row in snapshot['purchases']:trades.setdefault(identity(row),[]).append(row)
        for row in snapshot['dividends']:income.setdefault(identity(row),[]).append(row)
        with self.read() as db:
            db.execute('BEGIN')
            if db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]!=snapshot['data_revision']:
                raise PortfolioRevisionChanged('De portefeuille is gewijzigd. Vernieuw het overzicht.')
            for p in snapshot['positions']:
                if account!='all' and str(p['account_id'])!=str(account):continue
                listing=tuple(p[k] for k in ('symbol','exchange','currency'))
                if p.get('invalid_position'):
                    yield p
                    continue
                quotes,daily=self.history_inputs(db,listing)
                try:
                    history=with_dividends(daily_values(trades[identity(p)],daily,quotes),valid_position_income(income.get(identity(p),[])))
                except (ArithmeticError,ValueError,TypeError,KeyError,IndexError):
                    if not skip_invalid:raise
                    yield {**p,'history':[],'invalid_position':True}
                    continue
                yield {**p,'history':history}

    def sampled_state(self,snapshot,mode,account='all'):
        """Retain only annual boundaries or dividend dates for specialist reports."""
        payments={}
        for row in snapshot['dividends']:
            key=tuple(row[k] for k in ('account_id','symbol','exchange','currency'))
            payments.setdefault(key,set()).add(row['paid_on'])
        positions=[]
        for p in self.position_histories(snapshot,account,skip_invalid=mode in ('annual','dividend')):
            if mode=='annual':
                from performance import annual_points
                points=annual_points(p['history'])
            else:
                key=tuple(p[k] for k in ('account_id','symbol','exchange','currency'))
                needed=payments.get(key,set())
                points=[point for point in p['history'] if point['day'] in needed]
                if p['history'] and (not points or points[-1]['day']!=p['history'][-1]['day']):points.append(p['history'][-1])
            positions.append({**p,'history':points})
        return {**snapshot,'positions':positions}

    @staticmethod
    def history_inputs(db,listing):
        daily=[dict(r) for r in db.execute('SELECT * FROM daily_prices WHERE symbol=? AND exchange=? AND currency=? ORDER BY day',listing)]
        quotes=[dict(r) for r in db.execute("""SELECT * FROM (
            SELECT quotes.*,ROW_NUMBER() OVER (PARTITION BY substr(quoted_at,1,10) ORDER BY quoted_at DESC,id DESC) AS rank
            FROM quotes WHERE symbol=? AND exchange=? AND currency=?
        ) WHERE rank=1 ORDER BY quoted_at,id""",listing)]
        for row in quotes:row.pop('rank',None)
        manual=[dict(r) for r in db.execute('SELECT * FROM instrument_valuations WHERE symbol=? AND exchange=? AND currency=?',listing)]
        from valuations import apply_final_prices
        return apply_final_prices(quotes,daily,manual)

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

    def backup(self,retain=True):
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        path = folder / ('portfolio-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-' + uuid4().hex[:8] + '.sqlite3')
        with self.connect() as source, closing(sqlite3.connect(path)) as target:
            source.backup(target)
        if retain:
            keep=5 if self.settings().get('backup_retention')=='5' else 30
            for old in sorted(folder.glob('portfolio-*.sqlite3'))[:-keep]:
                if not old.is_symlink() and old.resolve().parent==folder.resolve():old.unlink()
        return path
