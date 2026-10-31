"""Explicit ledger corrections and scoped resets, preserving import provenance."""
import hashlib
import hmac
import json
from datetime import date,datetime
from history import daily_values
from storage import now,positive

TABLES={'trade':'purchases','dividend':'dividends','capital':'capital_returns'}

def revision(row):
    return hashlib.sha256(json.dumps(dict(row),sort_keys=True).encode()).hexdigest()

def ledger(store,account='all'):
    with store.connect() as db:
        account_id=scope(db,account)
        accounts={r['id']:dict(r) for r in db.execute('SELECT * FROM broker_accounts')}
        rows=[]
        for kind,table in TABLES.items():
            clause='' if account_id is None else ' WHERE account_id=?'
            for source in db.execute('SELECT * FROM '+table+clause,() if account_id is None else (account_id,)):
                row=dict(source);broker=accounts[row['account_id']]
                rows.append(dict(row,kind=kind,revision=revision(row),account_name=broker['name'],broker=broker['broker'],day=row.get('purchased_on',row.get('paid_on')),type='TRANSFER' if row.get('transfer_id') else 'SPLIT' if row.get('split_before','') else row.get('side','DIVIDEND' if kind=='dividend' else 'CAPITAL_RETURN')))
        clause='' if account_id is None else ' WHERE account_id=?'
        from charges import FEES
        for source in db.execute('SELECT * FROM charges'+clause,() if account_id is None else (account_id,)):
            row=dict(source);broker=accounts[row['account_id']]
            rows.append(dict(row,kind='charge',revision=revision(row),account_name=broker['name'],broker=broker['broker'],day=row['paid_on'],symbol=row['ticker'],exchange='',name=row['description'],type='COST' if row['category'] in FEES else 'TAX'))
        return dict(transactions=sorted(rows,key=lambda r:(r['day'],r['id']),reverse=True))

def scope(db,value):
    if value=='all':return None
    account_id=int(value)
    if account_id<1:raise ValueError('Kies een bestaand brokeraccount of Alle accounts.')
    if not db.execute('SELECT 1 FROM broker_accounts WHERE id=?',(account_id,)).fetchone():raise ValueError('Brokeraccount niet gevonden.')
    return account_id

def edit(store,data,actor):
    kind=str(data.get('kind',''));table=TABLES.get(kind)
    if not table:raise ValueError('Onbekend transactietype.')
    record_id=int(data['id'])
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        source=db.execute('SELECT * FROM '+table+' WHERE id=?',(record_id,)).fetchone()
        if not source:raise ValueError('Transactie niet gevonden. Vernieuw het overzicht.')
        before=dict(source)
        if before.get('transfer_id'):raise ValueError('Een omboeking kan niet als losse aankoop of verkoop worden gewijzigd. Gebruik de herstelback-up om de omboeking terug te draaien.')
        if not hmac.compare_digest(str(data.get('revision','')),revision(before)):raise ValueError('Deze transactie is intussen gewijzigd. Vernieuw het overzicht en open de transactie opnieuw.')
        # Identity and account remain fixed, so source-ID deduplication stays valid.
        for field in ('account_id','symbol','exchange','currency','ticker','split_before'):
            if field in data and str(data[field])!=str(before.get(field,'')):raise ValueError('Brokeraccount, aandeel, valuta en splitsingscontrole kunnen hier niet worden verplaatst.')
        day=date.fromisoformat(str(data['day']))
        if day>date.today():raise ValueError('Transactiedatum mag niet in de toekomst liggen.')
        if kind=='trade':
            split=bool(before['split_before'])
            side=before['side'] if split else str(data.get('side',before['side']))
            if side not in ('BUY','SELL'):raise ValueError('Kies aankoop of verkoop.')
            quantity=positive(data['quantity']);price=before['price'] if split else positive(data['price'])
            clock=str(data.get('time',before['trade_time'][11:19] if before['trade_time'] else '')).strip()
            stamp=datetime.fromisoformat(day.isoformat()+'T'+clock).isoformat() if clock else ''
            if clock and (len(clock) not in (5,8) or any(c not in '0123456789:' for c in clock)):raise ValueError('Gebruik een tijd als 10:30 of 10:30:00.')
            db.execute('UPDATE purchases SET quantity=?,price=?,side=?,purchased_on=?,trade_time=? WHERE id=?',(quantity,price,side,day.isoformat(),stamp,record_id))
            lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(before['account_id'],before['symbol'],before['exchange'],before['currency']))]
            daily_values(lots,[],[])
        else:
            amount=positive(data['amount'])
            if kind=='dividend':
                note=str(data.get('note',before['note'])).strip()
                if len(note)>200:raise ValueError('Notitie mag maximaal 200 tekens bevatten.')
                db.execute('UPDATE dividends SET amount=?,paid_on=?,note=? WHERE id=?',(amount,day.isoformat(),note,record_id))
            else:db.execute('UPDATE capital_returns SET amount=?,paid_on=? WHERE id=?',(amount,day.isoformat(),record_id))
        after=dict(db.execute('SELECT * FROM '+table+' WHERE id=?',(record_id,)).fetchone())
        db.execute('INSERT INTO transaction_edits(kind,record_id,account_id,before_payload,after_payload,changed_by,created_at) VALUES(?,?,?,?,?,?,?)',(kind,record_id,before['account_id'],json.dumps(before),json.dumps(after),actor,now()))
    return dict(ok=True)

def changes(store,kind,record_id):
    if kind not in TABLES:raise ValueError('Onbekend transactietype.')
    with store.connect() as db:
        return dict(changes=[dict(r) for r in db.execute('SELECT * FROM transaction_edits WHERE kind=? AND record_id=? ORDER BY id DESC',(kind,int(record_id)))])

RESET_TABLES=('charges','transaction_edits','import_issues','import_fx','import_records','capital_returns','instrument_mappings','import_batches','dividends','purchases')
SHARED_TABLES=('instrument_valuations','instrument_category_sync','instrument_categories','quotes','daily_prices','history_sync','api_cache')

def reset_where(table,account_id):
    if account_id is None:return '',()
    if table in ('import_issues','import_fx'):return ' WHERE batch_id IN (SELECT id FROM import_batches WHERE account_id=?)',(account_id,)
    return ' WHERE account_id=?',(account_id,)

def reset_preview_db(db,account):
    account_id=scope(db,account)
    tables=RESET_TABLES+(SHARED_TABLES if account_id is None else ())
    digest=hashlib.sha256(str(account_id).encode());counts={}
    if account_id is not None:digest.update(json.dumps(dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(account_id,)).fetchone()),sort_keys=True).encode())
    for table in tables:
        where,args=reset_where(table,account_id)
        rows=[tuple(r) for r in db.execute('SELECT * FROM '+table+where,args)]
        counts[table]=len(rows)
        digest.update(json.dumps([table,rows],sort_keys=True).encode())
    label='Alle brokeraccounts' if account_id is None else db.execute('SELECT name FROM broker_accounts WHERE id=?',(account_id,)).fetchone()[0]
    return dict(account_id='all' if account_id is None else account_id,label=label,counts=counts,revision=digest.hexdigest())

def reset_preview(store,account):
    with store.connect() as db:return reset_preview_db(db,account)

def reset(store,data,remove_account=False):
    if data.get('confirmation')!='VERWIJDEREN':raise ValueError('Typ VERWIJDEREN om de gekozen gegevens te verwijderen.')
    with store.lock:
        with store.connect() as db:preview=reset_preview_db(db,data['account_id'])
        if not hmac.compare_digest(str(data.get('revision','')),preview['revision']):raise ValueError('De gegevens zijn intussen gewijzigd. Controleer eerst een nieuw verwijderoverzicht.')
        if remove_account and preview['account_id']=='all':raise ValueError('Kies één brokeraccount om te verwijderen.')
        if not remove_account and not any(preview['counts'].values()):raise ValueError('Er zijn geen gegevens om te verwijderen.')
        # Keep this copy outside routine backup rotation.
        backup=store.backup();folder=store.root/'backups'/'deletions';folder.mkdir(exist_ok=True)
        backup=backup.rename(folder/('before-delete-'+backup.name))
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=reset_preview_db(db,data['account_id'])
            if current['revision']!=preview['revision']:raise ValueError('De gegevens zijn intussen gewijzigd. Er is niets verwijderd.')
            account_id=None if data['account_id']=='all' else int(data['account_id'])
            for table in RESET_TABLES+(SHARED_TABLES if account_id is None else ()):
                where,args=reset_where(table,account_id);db.execute('DELETE FROM '+table+where,args)
            if remove_account:
                db.execute('DELETE FROM broker_accounts WHERE id=?',(account_id,))
                (store.root/'connections'/f'{account_id}.encrypted').unlink(missing_ok=True)
        store._mapping_discovered=False
        return dict(ok=True,deleted=preview['counts'],label=preview['label'],backup_name=backup.name)

def deletion_backup(store,name):
    import re
    if not re.fullmatch(r'before-delete-portfolio-[0-9TZ]+-[a-f0-9]{8}\.sqlite3',name):raise ValueError('Ongeldige veiligheidsback-up.')
    path=store.root/'backups'/'deletions'/name
    if not path.is_file():raise ValueError('Veiligheidsback-up niet gevonden.')
    return path
