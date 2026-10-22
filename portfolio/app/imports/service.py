"""Durable previews, persisted instrument mappings and atomic idempotent imports."""
import hashlib
import json
from . import ADAPTERS
from storage import now
from diagnostics import record
from provider import EXCHANGES
from forex import convert,prepare_rates
from .registry import remember,lookup,discover,identity

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
                    elif key.startswith(('row:','raw:')):row['error']='Identieke regels zonder bron-ID: niet veilig te onderscheiden.'
                    else:row['duplicate']=True
                seen[key]=row['digest']
                existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(account_id,provider,row['external_id'])).fetchone()
                row['duplicate']=row.get('duplicate',False) or bool(existing and existing[0]==row['digest'])
                if existing and not row['duplicate']:row['error']='Deze bron-ID is eerder geïmporteerd met andere gegevens.'
        payload=json.dumps(rows)
        cursor=db.execute('INSERT INTO import_batches(account_id,provider,filename,digest,payload,created_at) VALUES(?,?,?,?,?,?)',(account_id,provider,str(filename)[:180],hashlib.sha256(text.encode()).hexdigest(),payload,now()))
    record(store,'WARNING' if any(r.get('error') for r in rows) else 'INFO',provider,'import_preview','Importvoorbeeld aangemaakt.',{'account_id':account_id,'batch_id':cursor.lastrowid,'source_rows':len(rows),'errors':sum(bool(r.get('error')) for r in rows),'duplicates':sum(bool(r.get('duplicate')) for r in rows),'buys':sum(r.get('kind')=='BUY' for r in rows),'sells':sum(r.get('kind')=='SELL' for r in rows),'splits':sum(r.get('kind')=='SPLIT' for r in rows),'skipped':sum(r.get('kind')=='SKIP' for r in rows),'first_day':min((r['day'] for r in rows if r.get('day')),default=None),'last_day':max((r['day'] for r in rows if r.get('day')),default=None)})
    registered=set()
    for row in rows:
        if row.get('kind') in ('BUY','SELL','DIVIDEND','SPLIT') and row.get('currency'):
            key=(identity(row)[0],row['currency'])
            if key not in registered:remember(store,account_id,provider,row);registered.add(key)
    instruments=sorted({(r['ticker'],r.get('currency','')) for r in rows if r.get('kind') in ('BUY','SELL','DIVIDEND','SPLIT') and r.get('currency') and not r.get('error') and not r.get('duplicate')})
    return dict(batch_id=cursor.lastrowid,account=account,rows=rows,instruments=[dict(ticker=t,currency=c) for t,c in instruments],warnings=['Dividend zonder voorafgaande aankoop wordt apart opgeslagen met een melding over ontbrekende aankoophistorie; er wordt geen positie of kostprijs aangemaakt.', 'Prijzen worden in de noteringsvaluta geïmporteerd; transactiekosten, rente en valutawissels worden niet in de winst verwerkt.','Afwijkende prijs- of dividendvaluta wordt op transactiedatum omgerekend met opgeslagen dagreferentiekoersen. Het bronbedrag en de omrekening blijven bewaard.'])

def commit(store,batch_id,mappings):
    with store.lock:
        with store.connect() as db:
            batch=db.execute('SELECT * FROM import_batches WHERE id=?',(batch_id,)).fetchone()
        if not batch:raise ValueError('Importvoorbeeld niet gevonden.')
        if batch['status']=='imported':return dict(imported=0,duplicate=True)
        rows=json.loads(batch['payload'])
        if any(r.get('error') for r in rows):raise ValueError('Deze CSV bevat fouten of niet-ondersteunde transacties. Los deze eerst op; er is niets geïmporteerd.')
        discover(store)
        pending=[];seen=set()
        for row in rows:
            if row['kind'] in ('SKIP','SPLIT_INFO'):continue
            if row['external_id'] in seen:continue
            seen.add(row['external_id'])
            key=row['ticker']+'|'+row['currency'];mapping=lookup(store,batch['account_id'],batch['provider'],row) or row.get('mapping') or mappings.get(key)
            if mapping and lookup(store,batch['account_id'],batch['provider'],row):row['mapping']=mapping
            with store.connect() as db:existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(batch['account_id'],batch['provider'],row['external_id'])).fetchone()
            if existing:
                if existing[0]!=row['digest']:raise ValueError('Een eerder geïmporteerde transactie is gewijzigd.')
                continue
            if row['kind']=='CAPITAL_RETURN':
                pending.append((row,{}));continue
            if not isinstance(mapping,dict):raise ValueError('Automatische beurskoppeling ontbreekt.')
            if mapping.get('currency')!=row['currency'] and not row.get('mapping'):raise ValueError('Valutaomrekening vereist een opgeslagen, gecontroleerde automatische koppeling.')
            pending.append((row,mapping))
        requests=[(row['currency'],mapping['currency'],row['day']) for row,mapping in pending if row['kind'] not in ('SPLIT','CAPITAL_RETURN') and row['currency']!=mapping['currency']]
        prepare_rates(store,requests)
        converted=[];standalone_dividends=0
        for row,mapping in pending:
            trace=None
            if row['kind'] not in ('SPLIT','CAPITAL_RETURN') and row['currency']!=mapping['currency']:
                key='amount' if row['kind']=='DIVIDEND' else 'price'
                trace=convert(store,row[key],row['currency'],mapping['currency'],row['day'])
                row={**row,key:trace['converted']}
            converted.append((row,mapping,trace))
        # Reuse validation and rollback the complete batch, including prior rows.
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row,mapping,trace in sorted(converted,key=lambda pair:(pair[0]['trade_time'],0 if pair[0]['kind']=='BUY' else 1 if pair[0]['kind']=='SELL' else 2)):
                standalone_dividends+=book_row(db,batch_id,batch['account_id'],batch['provider'],row,mapping,trace)
            from history import daily_values
            keys=db.execute('SELECT DISTINCT symbol,exchange,currency FROM purchases WHERE account_id=?',(batch['account_id'],)).fetchall()
            for key in keys:
                lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(batch['account_id'],*tuple(key)))]
                daily_values(lots,[],[])
            db.execute("UPDATE import_batches SET status='imported',payload=? WHERE id=?",(json.dumps(rows),batch_id))
        return dict(imported=len(pending),standalone_dividends=standalone_dividends,skipped=sum(r['kind']=='SKIP' for r in rows))

def open_preview(store,batch_id):
    with store.connect() as db:
        batch=db.execute("SELECT * FROM import_batches WHERE id=? AND status IN ('preview','partial')",(batch_id,)).fetchone()
        if not batch:raise ValueError('Importvoorbeeld niet gevonden.')
        account=dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(batch['account_id'],)).fetchone())
    discover(store)
    rows=json.loads(batch['payload'])
    from .partial import refresh_supported
    refresh_supported(rows)
    for row in rows:
        if row.get('external_id'):
            with store.connect() as db:previous=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(batch['account_id'],batch['provider'],row['external_id'])).fetchone()
            if previous and previous[0]==row.get('digest'):row['duplicate']=True
        if row.get('kind') in ('BUY','SELL','DIVIDEND','SPLIT') and row.get('currency'):
            saved=lookup(store,batch['account_id'],batch['provider'],row)
            if saved:row['mapping']=saved
    with store.connect() as db:
        db.execute("UPDATE import_batches SET payload=? WHERE id=? AND payload=? AND status IN ('preview','partial')",(json.dumps(rows),batch_id,batch['payload']))
    instruments=sorted({(r['ticker'],r['currency']) for r in rows if r.get('kind') in ('BUY','SELL','DIVIDEND','SPLIT') and r.get('currency') and not r.get('error') and not r.get('duplicate')})
    return dict(batch_id=batch_id,account=account,rows=rows,instruments=[dict(ticker=t,currency=c) for t,c in instruments],warnings=['Dividend zonder voorafgaande aankoop wordt apart opgeslagen met een melding over ontbrekende aankoophistorie; er wordt geen positie of kostprijs aangemaakt.', 'Beursnoteringen worden automatisch gekoppeld. Bronbedragen blijven bewaard; afwijkende noteringsvaluta wordt met historische dagreferentiekoersen omgerekend.'])

def book_row(db,batch_id,account_id,provider,row,mapping,trace):
    standalone_dividends=0
    if row['kind']=='SPLIT_INFO':
        db.execute('INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',(batch_id,account_id,provider,row['external_id'],row['digest'],json.dumps(row['raw'])))
        return 0
    if row['kind']=='CAPITAL_RETURN':
        from storage import positive
        db.execute('INSERT INTO capital_returns(batch_id,account_id,provider,external_id,ticker,isin,amount,currency,paid_on,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(batch_id,account_id,provider,row['external_id'],row['ticker'],row['raw'].get('ISIN',''),positive(row['amount']),row['currency'],row['day'],now()))
        db.execute('INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',(batch_id,account_id,provider,row['external_id'],row['digest'],json.dumps(row['raw'])))
        return 0
    base=dict(account_id=account_id,symbol=mapping.get('symbol'),exchange=mapping.get('exchange'),currency=mapping.get('currency'))
    # The connection-scoped import helpers below avoid nested SQLite writers.
    if row['kind']=='DIVIDEND':
        lot=db.execute("SELECT 1 FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=? AND side='BUY' AND purchased_on<=?",(base['account_id'],base['symbol'],base['exchange'],base['currency'],row['day'])).fetchone()
        note='Trading 212 import'
        if not lot:
            standalone_dividends=1
            note+=' - bij import geen voorafgaande aankoop in dit brokeraccount gevonden; aankoophistorie kan ontbreken.'
        from storage import positive
        db.execute('INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at,account_id) VALUES(?,?,?,?,?,?,?,?)',(base['symbol'],base['exchange'],base['currency'],positive(row['amount']),row['day'],note,now(),base['account_id']))
    else:
        from storage import positive
        import re
        if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',str(base['symbol'])) or base['exchange'] not in {market[0] for market in EXCHANGES.values()}:raise ValueError('Ongeldige beurskoppeling.')
        if row['kind']=='SPLIT':
            from history import daily_values
            from datetime import date
            from decimal import Decimal
            lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(account_id,base['symbol'],base['exchange'],base['currency']))]
            prior=[p for p in lots if (p['purchased_on'],p['trade_time'])<=(row['day'],row['trade_time'])]
            if not prior:raise ValueError('Splitsing zonder voorafgaand bezit. Importeer de volledige aankoopgeschiedenis.')
            point=daily_values(prior,[],[],today=date.fromisoformat(row['day']))[-1]
            # Store the preserved cost per new share, never an invented cash price.
            row={**row,'price':str(Decimal(point['cost'])/Decimal(row['quantity']))}
        db.execute('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(base['symbol'],base['exchange'],str(mapping.get('name') or row['name'])[:100],positive(row['quantity']),positive(row['price']),base['currency'],row['day'],now(),base['account_id'],'BUY' if row['kind']=='SPLIT' else row['kind'],row['trade_time']))
        if row['kind']=='SPLIT':db.execute('UPDATE purchases SET split_before=? WHERE id=last_insert_rowid()',(row.get('split_before','0'),))
    db.execute('INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',(batch_id,account_id,provider,row['external_id'],row['digest'],json.dumps(row['raw'])))
    if trace:
        db.execute('INSERT INTO import_fx(batch_id,external_id,kind,source_currency,target_currency,original_amount,converted_amount,rate,requested_on,rate_on,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(batch_id,row['external_id'],row['kind'],trace['from'],trace['to'],trace['amount'],trace['converted'],trace['rate'],trace['requested_on'],trace['rate_on'],trace['source']))
    if row['kind'] in ('BUY','SELL','SPLIT'):
        from history import daily_values
        lots=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',(account_id,base['symbol'],base['exchange'],base['currency']))]
        daily_values(lots,[],[])
    return standalone_dividends
