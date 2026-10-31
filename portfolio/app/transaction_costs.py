"""Atomic, audited corrections of linked expense components."""
import json
from uuid import uuid4
from storage import now
from charges import number,validate_charge,book
from forex import code

def snapshot(db,kind,row):
    result=dict(row)
    if kind!='charge':result['charges']=[dict(r) for r in db.execute('SELECT c.* FROM charges c JOIN transaction_charge_links l ON l.charge_id=c.id WHERE l.kind=? AND l.record_id=? ORDER BY c.id',(kind,row['id']))]
    return result

def audit(db,kind,before,after,actor):
    if before==after:return
    db.execute('INSERT INTO transaction_edits(kind,record_id,account_id,before_payload,after_payload,changed_by,created_at) VALUES(?,?,?,?,?,?,?)',(kind,before['id'],before['account_id'],json.dumps(before),json.dumps(after),actor,now()))

def save_charge(db,before,data,account_id,day,actor):
    row={**before,'account_id':account_id,'paid_on':day,'amount':str(number(data['amount'])),'currency':code(str(data['currency'])),'category':str(data['category']),'included_in_net':data.get('included_in_net',0),'description':str(data.get('description',before['description'])).strip()}
    if type(row['included_in_net']) is not int:raise ValueError('Ongeldige kostensoort of nettoverwerking.')
    validate_charge(row)
    if before['account_id']!=account_id:
        batch=dict(db.execute('SELECT * FROM import_batches WHERE id=?',(before['batch_id'],)).fetchone())
        row['batch_id']=db.execute('INSERT INTO import_batches(account_id,provider,filename,digest,payload,status,created_at) VALUES(?,?,?,?,?,?,?)',(account_id,batch['provider'],batch['filename'],batch['digest'],batch['payload'],'imported',now())).lastrowid
    db.execute('UPDATE charges SET account_id=?,batch_id=?,paid_on=?,amount=?,currency=?,category=?,included_in_net=?,description=? WHERE id=?',tuple(row[k] for k in ('account_id','batch_id','paid_on','amount','currency','category','included_in_net','description','id')))
    audit(db,'charge',before,row,actor)

def save_components(db,kind,before,data,account_id,day,actor):
    if 'charges' not in data:return
    items=data['charges']
    if not isinstance(items,list) or len(items)>50:raise ValueError('Ongeldige kostenreferentie.')
    existing={r['id']:r for r in before['charges']};seen=set()
    for item in items:
        if not isinstance(item,dict):raise ValueError('Ongeldige kostenreferentie.')
        charge_id=item.get('id')
        if charge_id:
            if type(charge_id) is not int or charge_id in seen:raise ValueError('Ongeldige kostenreferentie.')
            if charge_id not in existing:
                candidate=db.execute('SELECT * FROM charges WHERE id=? AND account_id=?',(charge_id,before['account_id'])).fetchone()
                if not candidate or db.execute('SELECT 1 FROM transaction_charge_links WHERE charge_id=?',(charge_id,)).fetchone():raise ValueError('Ongeldige kostenreferentie.')
                from transactions import revision
                import hmac
                if not hmac.compare_digest(str(item.get('revision','')),revision(candidate)):raise ValueError('Deze transactie is intussen gewijzigd. Vernieuw het overzicht en open de transactie opnieuw.')
                existing[charge_id]=dict(candidate)
                db.execute('INSERT INTO transaction_charge_links VALUES(?,?,?)',(charge_id,kind,before['id']))
            seen.add(charge_id);save_charge(db,existing[charge_id],item,account_id,day,actor)
        else:
            key='edit:'+uuid4().hex
            batch=db.execute("INSERT INTO import_batches(account_id,provider,filename,digest,payload,status,created_at) VALUES(?,'charges','manual-correction',?,'[]','imported',?)",(account_id,key,now())).lastrowid
            row=dict(external_id=key,ticker=before.get('symbol',before.get('ticker','')),day=day,charges=[dict(item,component=key,description=item.get('description',''))])
            book(db,batch,account_id,'charges',row)
            charge=db.execute('SELECT * FROM charges WHERE batch_id=?',(batch,)).fetchone()
            db.execute('INSERT INTO transaction_charge_links VALUES(?,?,?)',(charge['id'],kind,before['id']))
    # Zero corrections retain source IDs, so reimport cannot revive a removed fee.
    for charge_id,row in existing.items():
        if charge_id not in seen:save_charge(db,row,dict(row,amount='0'),account_id,day,actor)
