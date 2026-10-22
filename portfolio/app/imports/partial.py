"""Book independent valid rows; preserve every rejected source row for admin review."""
import csv
import io
import json
import sqlite3
from storage import now
from forex import prepare_rates,convert
from .registry import discover,lookup,remember
from .service import book_row
from .trading212 import parse_csv,unclassified_identity

def stable(row):
    if not row.get('external_id'):
        digest,external_id=unclassified_identity(row['raw'])
        row.update(digest=digest,external_id=external_id)
    return row

def commit_partial(store,batch_id):
    with store.lock:
        with store.connect() as db:batch=db.execute('SELECT * FROM import_batches WHERE id=?',(batch_id,)).fetchone()
        if not batch:raise ValueError('Importvoorbeeld niet gevonden.')
        if batch['status']=='imported':return dict(imported=0,pending=0,duplicate=True)
        rows=[stable(r) for r in json.loads(batch['payload'])]
        refresh_supported(rows)
        discover(store)
        conflicts={}
        for row in rows:
            conflicts.setdefault(row['external_id'],set()).add(row['digest'])
        prepared=[];failures={};duplicates=set();processed=set();standalone=0;imported=0;ignored=0
        for row in sorted(rows,key=lambda r:(r.get('trade_time',''),0 if r.get('kind')=='BUY' else 1 if r.get('kind')=='SELL' else 2)):
            if row.get('kind')=='SKIP' and row.get('decision')!='IGNORE':continue
            try:
                if row.get('decision')=='IGNORE':prepared.append((row,None,None));continue
                if len(conflicts[row['external_id']])>1:raise ValueError('Dezelfde bron-ID heeft verschillende gegevens. Controleer het bronbestand; deze regels zijn apart gehouden.')
                with store.connect() as db:existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(batch['account_id'],batch['provider'],row['external_id'])).fetchone()
                if existing:
                    if existing[0]!=row['digest']:raise ValueError('Deze bron-ID is eerder met andere gegevens verwerkt. Eerdere boeking blijft behouden.')
                    duplicates.add(row['line']);continue
                if row.get('error'):raise ValueError(row['error'])
                if row.get('kind') in ('CAPITAL_RETURN','SPLIT_INFO'):prepared.append((row,None,None));continue
                mapping=lookup(store,batch['account_id'],batch['provider'],row) or row.get('mapping')
                if not mapping:raise ValueError('Beurskoppeling ontbreekt. Kies de juiste notering bij Aandelenkoppelingen en probeer deze regel opnieuw.')
                row['mapping']=mapping;trace=None;booked=row
                if row['kind']!='SPLIT' and row['currency']!=mapping['currency']:
                    prepare_rates(store,[(row['currency'],mapping['currency'],row['day'])])
                    key='amount' if row['kind']=='DIVIDEND' else 'price'
                    trace=convert(store,row[key],row['currency'],mapping['currency'],row['day'])
                    booked={**row,key:trace['converted']}
                prepared.append((booked,mapping,trace))
            except (ValueError,KeyError,TypeError) as error:failures[row['line']]=(row,str(error))
        # Provider calls are complete before opening the writer transaction.
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row,mapping,trace in prepared:
                db.execute('SAVEPOINT import_row')
                try:
                    existing=db.execute('SELECT digest FROM import_records WHERE account_id=? AND provider=? AND external_id=?',(batch['account_id'],batch['provider'],row['external_id'])).fetchone()
                    if row.get('decision')=='IGNORE':
                        if not existing:db.execute('INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,?,?,?,?)',(batch_id,batch['account_id'],batch['provider'],row['external_id'],row['digest'],json.dumps(row['raw'])))
                        ignored+=1
                    elif existing:
                        if existing[0]!=row['digest']:raise ValueError('Bron-ID wijkt af van een eerdere boeking.')
                        duplicates.add(row['line'])
                    else:
                        count=book_row(db,batch_id,batch['account_id'],batch['provider'],row,mapping,trace)
                        standalone+=count;imported+=1
                    db.execute('RELEASE import_row')
                    processed.add(row['line'])
                    state='ignored' if row.get('decision')=='IGNORE' else 'resolved'
                    db.execute('UPDATE import_issues SET state=?,resolution=?,updated_at=? WHERE batch_id=? AND line=?',(state,row.get('decision','retry'),now(),batch_id,row['line']))
                except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as error:
                    db.execute('ROLLBACK TO import_row');db.execute('RELEASE import_row')
                    original=next(r for r in rows if r['line']==row['line'])
                    failures[row['line']]=(original,str(error))
            for line in duplicates:db.execute("UPDATE import_issues SET state='resolved',resolution='already_processed',updated_at=? WHERE batch_id=? AND line=?",(now(),batch_id,line))
            for line,(row,reason) in failures.items():
                db.execute("INSERT INTO import_issues(batch_id,line,state,reason,payload,updated_at) VALUES(?,?,'pending',?,?,?) ON CONFLICT(batch_id,line) DO UPDATE SET state='pending',reason=excluded.reason,payload=excluded.payload,updated_at=excluded.updated_at",(batch_id,line,reason[:500],json.dumps(row),now()))
            for original in rows:
                if original['line'] in processed|duplicates:original['duplicate']=True
            pending=db.execute("SELECT COUNT(*) FROM import_issues WHERE batch_id=? AND state='pending'",(batch_id,)).fetchone()[0]
            db.execute('UPDATE import_batches SET status=?,payload=? WHERE id=?',('partial' if pending else 'imported',json.dumps(rows),batch_id))
        return dict(imported=imported,pending=pending,ignored=ignored,duplicates=len(duplicates),standalone_dividends=standalone,batch_id=batch_id)

def list_issues(store):
    with store.connect() as db:
        entries=db.execute('SELECT i.*,b.account_id,b.filename,a.name AS account_name FROM import_issues i JOIN import_batches b ON b.id=i.batch_id JOIN broker_accounts a ON a.id=b.account_id ORDER BY (i.state=?) DESC,i.id DESC LIMIT 2000',('pending',)).fetchall()
        returns=[dict(r) for r in db.execute('SELECT c.*,a.name AS account_name FROM capital_returns c JOIN broker_accounts a ON a.id=c.account_id ORDER BY c.id DESC LIMIT 500')]
    result=[]
    for item in entries:
        item=dict(item);row=json.loads(item.pop('payload'));item.update(ticker=row.get('ticker',''),action=row.get('raw',{}).get('Action',''),day=row.get('day') or row.get('raw',{}).get('Time (UTC)',row.get('raw',{}).get('Time','')),currency=row.get('currency') or row.get('raw',{}).get('Currency (Total)',''),amount=row.get('amount') or row.get('raw',{}).get('Total',''))
        result.append(item)
    return dict(issues=result,capital_returns=returns)

def resolve_issue(store,data):
    issue_id=int(data['id']);decision=str(data.get('decision',''))
    if decision not in ('retry','IGNORE','DIVIDEND','CAPITAL_RETURN','BUY','SELL'):raise ValueError('Kies hoe deze regel verwerkt moet worden.')
    with store.lock:
        with store.connect() as db:
            issue=db.execute('SELECT * FROM import_issues WHERE id=?',(issue_id,)).fetchone()
            if not issue or issue['state']!='pending':raise ValueError('Deze regel is niet meer in behandeling.')
            batch=db.execute('SELECT * FROM import_batches WHERE id=?',(issue['batch_id'],)).fetchone()
        rows=[stable(r) for r in json.loads(batch['payload'])];row=next(r for r in rows if r['line']==issue['line'])
        if decision not in ('retry','IGNORE'):
            raw=row['raw'];edited={**raw,'Action':{'DIVIDEND':'Dividend (Ordinary)','BUY':'Market buy','SELL':'Market sell','CAPITAL_RETURN':'Dividend (Ordinary)'}[decision]}
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(edited));writer.writeheader();writer.writerow(edited)
            parsed=parse_csv(stream.getvalue())[0]
            if parsed.get('error'):raise ValueError(parsed['error'])
            # Preserve the original source identity, original amount and raw columns.
            parsed.update(line=row['line'],raw=raw,external_id=row['external_id'],digest=row['digest'],decision=decision)
            if decision=='CAPITAL_RETURN':parsed['kind']='CAPITAL_RETURN'
            if row.get('mapping'):parsed['mapping']=row['mapping']
            row.clear();row.update(parsed)
        elif decision=='IGNORE':row.update(kind='SKIP',error=None,decision='IGNORE')
        else:
            row['decision']='retry'
            refresh_supported(rows)
        with store.connect() as db:db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch['id']))
        if row.get('kind') in ('BUY','SELL','DIVIDEND','SPLIT'):remember(store,batch['account_id'],batch['provider'],row)
        return commit_partial(store,batch['id'])

def refresh_supported(rows):
    if not any(r.get('error') and r.get('decision') in (None,'retry') for r in rows):return
    stream=io.StringIO()
    fields=list(dict.fromkeys(k for r in rows for k in r['raw']))
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
    for row in rows:writer.writerow(row['raw'])
    parsed=parse_csv(stream.getvalue())
    for row,new in zip(rows,parsed):
        if row.get('decision') not in (None,'retry') or not row.get('error') or row.get('duplicate'):continue
        if new.get('kind') not in ('BUY','SELL','DISTRIBUTION','CAPITAL_RETURN','SPLIT','SPLIT_INFO','SPLIT_CLOSE'):continue
        if row.get('kind') is not None and not (row.get('kind') in ('BUY','SELL') and str(row.get('error','')).startswith('Aantal of prijs ontbreekt.')):continue
        new.update(line=row['line'],external_id=row['external_id'],digest=row['digest'])
        if row.get('mapping'):new['mapping']=row['mapping']
        row.clear();row.update(new)
