"""Explicit, account-scoped TMX merger, without changing imported transactions."""
import hashlib
import hmac
import json
import re
from datetime import date
from decimal import Decimal,InvalidOperation
from uuid import uuid4
from history import daily_values
from storage import positive,now
from transactions import scope

SOURCE=('TMX.AS','AMSTERDAM','EUR')
TARGET=('TDT.AS','AMSTERDAM','EUR')
RATIO=Decimal('0.937630')
NOTICE='https://www.vaneck.com/globalassets/home/media/managedassets/etf-europe/news-and-media/market-announcements/merger-exchange-ratio-for-the-merger-amx-aex-_1-oct2025.pdf'

def overview(store):
    with store.connect() as db:
        accounts=[dict(r) for r in db.execute('SELECT DISTINCT a.* FROM broker_accounts a JOIN purchases p ON p.account_id=a.id WHERE p.symbol=? AND p.exchange=? AND p.currency=?',SOURCE)]
        events=[dict(r) for r in db.execute("SELECT p.*,a.name AS account_name FROM purchases p JOIN broker_accounts a ON a.id=p.account_id WHERE p.transfer_id<>'' ORDER BY p.id DESC")]
    return dict(accounts=accounts,events=events,ratio=str(RATIO),notice=NOTICE)

def preview_db(db,data):
    account=scope(db,data.get('account_id'))
    if account is None:raise ValueError('Kies één brokeraccount voor de omboeking.')
    day=date.fromisoformat(str(data.get('day','')))
    if day<date(2025,10,1) or day>date.today():raise ValueError('Kies een omboekdatum vanaf 1 oktober 2025 tot en met vandaag.')
    trades=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND exchange=? AND currency=? AND symbol IN (?,?) ORDER BY id',(account,SOURCE[1],SOURCE[2],SOURCE[0],TARGET[0]))]
    old=[r for r in trades if r['symbol']==SOURCE[0]]
    if not old:raise ValueError('Geen TMX-transacties gevonden in dit brokeraccount.')
    if any(r['purchased_on']>day.isoformat() for r in old):raise ValueError('Er staan TMX-transacties na de omboekdatum. Controleer eerst de datum en de historie.')
    if any(r['transfer_id'] for r in old):raise ValueError('TMX is in dit brokeraccount al omgeboekt.')
    point=daily_values(old,[],[],today=day,summary_only=True)[-1]
    quantity=Decimal(point['quantity'])
    if quantity<=0:raise ValueError('Er is geen open TMX-positie om te boeken.')
    received=positive(data['quantity']) if str(data.get('quantity','')).strip() else str(quantity*RATIO)
    positive(received)
    label=db.execute('SELECT name FROM broker_accounts WHERE id=?',(account,)).fetchone()[0]
    result=dict(account_id=account,account_name=label,day=day.isoformat(),old_quantity=str(quantity),quantity=received,cost=point['cost'],invested=point['invested'],ratio=str(Decimal(received)/quantity))
    result['revision']=hashlib.sha256(json.dumps([trades,result],sort_keys=True).encode()).hexdigest()
    return result

def preview(store,data):
    with store.connect() as db:return preview_db(db,data)

def commit(store,data,actor):
    with store.lock:
        with store.connect() as db:review=preview_db(db,data)
        if not hmac.compare_digest(str(data.get('revision','')),review['revision']):raise ValueError('De omboeking is gewijzigd. Controleer eerst een nieuw voorbeeld.')
        backup=store.backup();folder=store.root/'backups'/'conversions';folder.mkdir(exist_ok=True)
        backup=backup.rename(folder/('before-conversion-'+backup.name))
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if preview_db(db,data)['revision']!=review['revision']:raise ValueError('De omboeking is gewijzigd. Controleer eerst een nieuw voorbeeld.')
            identifier=uuid4().hex
            for instrument,side,units,name in ((SOURCE,'SELL',review['old_quantity'],'VanEck AMX UCITS ETF'),(TARGET,'BUY',review['quantity'],'VanEck AEX UCITS ETF')):
                # Price is an unused positive placeholder: transfers move book cost,
                # never sale proceeds or new capital. The UI hides this field.
                cursor=db.execute('INSERT INTO purchases(symbol,exchange,currency,name,side,quantity,price,purchased_on,trade_time,account_id,created_at,transfer_id,transfer_cost,transfer_invested) VALUES(?,?,?,?,?,?,?, ?,?,?,?,?,?,?)',(*instrument,name,side,units,'1',review['day'],review['day']+'T23:59:59',review['account_id'],now(),identifier,review['cost'],review['invested']))
                row=dict(db.execute('SELECT * FROM purchases WHERE id=?',(cursor.lastrowid,)).fetchone())
                db.execute('INSERT INTO transaction_edits(kind,record_id,account_id,before_payload,after_payload,changed_by,created_at) VALUES(?,?,?,?,?,?,?)',('trade',row['id'],review['account_id'],json.dumps(dict(id=row['id'],account_id=review['account_id'])),json.dumps(row),actor,now()))
            for instrument in (SOURCE,TARGET):
                lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(review['account_id'],*instrument))]
                daily_values(lots,[],[])
        return dict(ok=True,backup_name=backup.name,**review)

def validate_pairs(rows):
    pairs={}
    for row in rows:
        if not row['transfer_id']:
            if row['transfer_cost'] or row['transfer_invested']:raise ValueError('Ongeldige omboeking in back-up.')
            continue
        if not re.fullmatch('[a-f0-9]{32}',row['transfer_id']) or row['split_before']:raise ValueError('Ongeldige omboeking in back-up.')
        for field in ('transfer_cost','transfer_invested'):
            try:value=Decimal(row[field])
            except (InvalidOperation,TypeError,ValueError):raise ValueError('Ongeldige omboeking in back-up.') from None
            if not value.is_finite() or value<0 or value>Decimal('1e30'):raise ValueError('Ongeldige omboeking in back-up.')
        pairs.setdefault(row['transfer_id'],[]).append(row)
    for pair in pairs.values():
        if len(pair)!=2:raise ValueError('Ongeldige omboeking in back-up.')
        out,inc=sorted(pair,key=lambda r:r['side'],reverse=True)
        if out['side']!='SELL' or inc['side']!='BUY' or tuple(out[k] for k in ('symbol','exchange','currency'))!=SOURCE or tuple(inc[k] for k in ('symbol','exchange','currency'))!=TARGET or any(out[k]!=inc[k] for k in ('account_id','purchased_on','trade_time','transfer_cost','transfer_invested')):raise ValueError('Ongeldige omboeking in back-up.')

def safety_backup(store,name):
    if not re.fullmatch(r'before-conversion-portfolio-[0-9TZ]+-[a-f0-9]{8}\.sqlite3',name):raise ValueError('Ongeldige veiligheidsback-up.')
    path=store.root/'backups'/'conversions'/name
    if not path.is_file():raise ValueError('Veiligheidsback-up niet gevonden.')
    return path
