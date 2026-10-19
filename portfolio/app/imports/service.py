"""Durable previews, explicit instrument mapping and atomic idempotent imports."""
import hashlib
import json
from . import ADAPTERS
from storage import now

def preview(store,account_id,provider,filename,text):
    adapter=ADAPTERS.get(provider)
    if not adapter:raise ValueError('Onbekende importaanbieder.')
    with store.connect() as db:
        store.require_account(db,account_id)
        account=dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(account_id,)).fetchone())
    if account['broker']!=adapter['name']:raise ValueError('Kies een brokeraccount van '+adapter['name']+'.')
    rows=adapter['parse'](text)
    with store.connect() as db:
        seen={}
        for row in rows:
            if row.get('external_id'):
                key=row['external_id']
                if key in seen:
                    if seen[key]!=row['digest']:row['error']='Dezelfde bron-ID staat met verschillende gegevens in dit bestand.'
                    elif key.startswith('row:'):row['error']='Identieke regels zonder bron-ID: niet veilig te onderscheiden.'
                    else:row['duplicate']=True
                seen[key]=row['digest']
                existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(account_id,provider,row['external_id'])).fetchone()
                row['duplicate']=row.get('duplicate',False) or bool(existing and existing[0]==row['digest'])
                if existing and not row['duplicate']:row['error']='Deze bron-ID is eerder geïmporteerd met andere gegevens.'
        payload=json.dumps(rows)
        cursor=db.execute('INSERT INTO import_batches(account_id,provider,filename,digest,payload,created_at) VALUES(?,?,?,?,?,?)',(account_id,provider,str(filename)[:180],hashlib.sha256(text.encode()).hexdigest(),payload,now()))
    instruments=sorted({(r['ticker'],r.get('currency','')) for r in rows if r.get('kind') not in (None,'SKIP') and not r.get('duplicate')})
    return dict(batch_id=cursor.lastrowid,account=account,rows=rows,instruments=[dict(ticker=t,currency=c) for t,c in instruments],warnings=['Prijzen worden in de noteringsvaluta geïmporteerd; transactiekosten, rente en valutawissels worden niet in de winst verwerkt.','Dividend vereist dezelfde valuta als de gekoppelde beursnotering. Er wordt geen wisselkoers gegokt.'])

def commit(store,batch_id,mappings):
    with store.lock:
        with store.connect() as db:
            batch=db.execute('SELECT * FROM import_batches WHERE id=?',(batch_id,)).fetchone()
        if not batch:raise ValueError('Importvoorbeeld niet gevonden.')
        if batch['status']=='imported':return dict(imported=0,duplicate=True)
        rows=json.loads(batch['payload'])
        if any(r.get('error') for r in rows):raise ValueError('Deze CSV bevat fouten of niet-ondersteunde transacties. Los deze eerst op; er is niets geïmporteerd.')
        pending=[];seen=set()
        for row in rows:
            if row['kind']=='SKIP':continue
            if row['external_id'] in seen:continue
            seen.add(row['external_id'])
            key=row['ticker']+'|'+row['currency'];mapping=mappings.get(key)
            with store.connect() as db:existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(batch['account_id'],batch['provider'],row['external_id'])).fetchone()
            if existing:
                if existing[0]!=row['digest']:raise ValueError('Een eerder geïmporteerde transactie is gewijzigd.')
                continue
            if not isinstance(mapping,dict) or mapping.get('currency')!=row['currency']:raise ValueError('Koppel iedere ticker aan een beursnotering met dezelfde valuta.')
            pending.append((row,mapping))
        # Reuse validation and rollback the complete batch, including prior rows.
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row,mapping in sorted(pending,key=lambda pair:(pair[0]['trade_time'],0 if pair[0]['kind']=='BUY' else 1 if pair[0]['kind']=='SELL' else 2)):
                base=dict(account_id=batch['account_id'],symbol=mapping.get('symbol'),exchange=mapping.get('exchange'),currency=mapping.get('currency'))
                # The connection-scoped import helpers below avoid nested SQLite writers.
                if row['kind']=='DIVIDEND':
                    lot=db.execute('SELECT 1 FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=? AND purchased_on<=?',(base['account_id'],base['symbol'],base['exchange'],base['currency'],row['day'])).fetchone()
                    if not lot:raise ValueError('Dividend zonder voorafgaande aankoop in dit brokeraccount.')
                    from storage import positive
                    db.execute('INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at,account_id) VALUES(?,?,?,?,?,?,?,?)',(base['symbol'],base['exchange'],base['currency'],positive(row['amount']),row['day'],'Trading 212 import',now(),base['account_id']))
                else:
                    from storage import positive
                    import re
                    if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',str(base['symbol'])) or base['exchange'] not in ('AMSTERDAM','NASDAQ','NYSE'):raise ValueError('Ongeldige beurskoppeling.')
                    db.execute('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(base['symbol'],base['exchange'],str(mapping.get('name') or row['name'])[:100],positive(row['quantity']),positive(row['price']),base['currency'],row['day'],now(),base['account_id'],row['kind'],row['trade_time']))
                db.execute('INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',(batch_id,batch['account_id'],batch['provider'],row['external_id'],row['digest'],json.dumps(row['raw'])))
            from history import daily_values
            keys=db.execute('SELECT DISTINCT symbol,exchange,currency FROM purchases WHERE account_id=?',(batch['account_id'],)).fetchall()
            for key in keys:
                lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(batch['account_id'],*tuple(key)))]
                daily_values(lots,[],[])
            db.execute("UPDATE import_batches SET status='imported' WHERE id=?",(batch_id,))
        return dict(imported=len(pending),skipped=sum(r['kind']=='SKIP' for r in rows))
