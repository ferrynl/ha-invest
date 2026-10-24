"""Durable, account-scoped broker identities; editing never rewrites booked trades."""
import json
import re
from storage import now
from provider import listing

def identity(row):
    isin=str(row.get('raw',{}).get('ISIN','')).strip().upper()
    return ('isin:'+isin if isin else 'ticker:'+row['ticker'].strip().upper()),isin

def remember(store,account_id,provider,row,mapping=None,origin='automatic'):
    key,isin=identity(row)
    with store.connect() as db:
        db.execute('INSERT OR IGNORE INTO instrument_mappings(account_id,provider,identity,ticker,isin,source_currency,updated_at) VALUES(?,?,?,?,?,?,?)',
                   (account_id,provider,key,row['ticker'],isin,row['currency'],now()))
        if mapping:
            db.execute("UPDATE instrument_mappings SET symbol=?,exchange=?,currency=?,name=?,origin=?,updated_at=? WHERE account_id=? AND provider=? AND identity=? AND source_currency=? AND origin!='manual'",
                       (mapping['symbol'],mapping['exchange'],mapping['currency'],mapping.get('name',row.get('name',''))[:100],origin,now(),account_id,provider,key,row['currency']))

def lookup(store,account_id,provider,row):
    key,_=identity(row)
    with store.connect() as db:
        found=db.execute("SELECT symbol,exchange,currency,name FROM instrument_mappings WHERE account_id=? AND provider=? AND identity=? AND source_currency=? AND symbol!=''",(account_id,provider,key,row['currency'])).fetchone()
        if not found and key.startswith('isin:'):
            alternatives=db.execute("SELECT DISTINCT symbol,exchange,currency,name FROM instrument_mappings WHERE account_id=? AND provider=? AND identity=? AND symbol!=''",(account_id,provider,key)).fetchall()
            targets={(r['symbol'],r['exchange'],r['currency']) for r in alternatives}
            if len(targets)==1:found=alternatives[0]
    return dict(found) if found else None

def discover(store):
    # Backfill old previews and committed mappings locally; never use a provider here.
    with store.connect() as db:batches=[] if getattr(store,'_mapping_discovered',False) else db.execute('SELECT account_id,provider,payload FROM import_batches ORDER BY id DESC').fetchall()
    entries={}
    for batch in batches:
        for row in json.loads(batch['payload']):
            if row.get('kind') not in ('BUY','SELL','DIVIDEND','SPLIT') or not row.get('currency'):continue
            key=(batch['account_id'],batch['provider'],identity(row)[0],row['currency'])
            if key not in entries or (not entries[key].get('mapping') and row.get('mapping')):entries[key]=row
    for key,row in entries.items():
        mapping=row.get('mapping')
        # An existing registry entry always wins over stale preview snapshots.
        with store.connect() as db:exists=db.execute('SELECT 1 FROM instrument_mappings WHERE account_id=? AND provider=? AND identity=? AND source_currency=?',key).fetchone()
        if not exists:remember(store,key[0],key[1],row,mapping)
        elif mapping:
            with store.connect() as db:db.execute("UPDATE instrument_mappings SET symbol=?,exchange=?,currency=?,name=?,origin='automatic',updated_at=? WHERE account_id=? AND provider=? AND identity=? AND source_currency=? AND symbol=''",(mapping['symbol'],mapping['exchange'],mapping['currency'],mapping.get('name','')[:100],now(),*key))
    store._mapping_discovered=True
    with store.connect() as db:
        return [dict(r) for r in db.execute('SELECT m.*,a.name AS account_name FROM instrument_mappings m JOIN broker_accounts a ON a.id=m.account_id ORDER BY m.ticker,m.source_currency,m.account_id')]

def edit(store,data):
    record_id=int(data['id']);symbol=str(data.get('symbol','')).strip().upper()
    if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',symbol):raise ValueError('Vul een geldig koersticker in, bijvoorbeeld SOF.BR of MO.')
    with store.connect() as db:entry=db.execute('SELECT * FROM instrument_mappings WHERE id=?',(record_id,)).fetchone()
    if not entry:raise ValueError('Koppeling niet gevonden.')
    if entry['exchange']=='PRIVATE':raise ValueError('Dit fonds heeft geen beursnotering. Stel de actuele fondskoers handmatig in bij Aandelen; de ISIN-koppeling blijft behouden.')
    actual=listing(symbol,store=store)
    if actual['exchange']!=str(data.get('exchange','')).upper() or actual['currency']!=str(data.get('currency','')).upper():
        raise ValueError('Beurs of valuta wijkt af van de gecontroleerde notering: '+actual['exchange']+' / '+actual['currency']+'. Pas de velden aan; er is niets gewijzigd.')
    with store.lock,store.connect() as db:
        db.execute("UPDATE instrument_mappings SET symbol=?,exchange=?,currency=?,name=?,origin='manual',updated_at=? WHERE id=?",(actual['symbol'],actual['exchange'],actual['currency'],actual['name'],now(),record_id))
        # Persist the override in every open preview. Imported payloads are audit records.
        batches=db.execute("SELECT id,payload FROM import_batches WHERE account_id=? AND provider=? AND status IN ('preview','partial')",(entry['account_id'],entry['provider'])).fetchall()
        for batch in batches:
            rows=json.loads(batch['payload']);changed=False
            for row in rows:
                if not row.get('duplicate') and row.get('currency')==entry['source_currency'] and row.get('ticker') and identity(row)[0]==entry['identity']:
                    row['mapping']=actual;changed=True
            if changed:db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch['id']))
    return dict(mapping=actual,message='Koppeling opgeslagen voor openstaande en volgende imports. Eerder geboekte transacties zijn behouden.')
