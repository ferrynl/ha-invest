"""Explicit expense and tax postings. Positive is paid, negative is refunded."""
import csv
import io
import re
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation
from storage import now
from forex import code,unit,prepare_rates

CATEGORIES=('COMMISSION','CUSTODY','FX_FEE','OTHER_FEE','VAT','WITHHOLDING_TAX','TRANSACTION_TAX','OTHER_TAX')
FEES=set(CATEGORIES[:4])

def source_charge(db,account_id,provider,external_id,component):
    # Corrections retain the original source identity even after a broker move.
    row=db.execute('SELECT * FROM charges WHERE account_id=? AND provider=? AND external_id=? AND component=?',(account_id,provider,external_id,component)).fetchone()
    if row:return row,False
    row=db.execute("SELECT c.* FROM transaction_edits e JOIN charges c ON c.id=e.record_id WHERE e.kind='charge' AND json_extract(e.before_payload,'$.account_id')=? AND json_extract(e.before_payload,'$.provider')=? AND json_extract(e.before_payload,'$.external_id')=? AND json_extract(e.before_payload,'$.component')=? ORDER BY e.id LIMIT 1",(account_id,provider,external_id,component)).fetchone()
    return row,bool(row)

def corrected(db,row):
    return bool(db.execute("SELECT 1 FROM transaction_edits WHERE kind='charge' AND record_id=? LIMIT 1",(row['id'],)).fetchone())

def number(value):
    try:value=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError):raise ValueError('Ongeldig kosten- of belastingbedrag.') from None
    if not value.is_finite() or value.copy_abs()>Decimal('1e15'):raise ValueError('Ongeldig kosten- of belastingbedrag.')
    return value

def validate_charge(row):
    number(row['amount']);code(row['currency'])
    if 'provider' in row and row['provider'] not in ('trading212','traderepublic','revolut','charges'):raise ValueError('Ongeldige kostenreferentie.')
    if row['category'] not in CATEGORIES or type(row['included_in_net']) is not int or row['included_in_net'] not in (0,1):raise ValueError('Ongeldige kostensoort of nettoverwerking.')
    if date.fromisoformat(row['paid_on'])>date.today():raise ValueError('Toekomstige transactie.')
    if not re.fullmatch(r'[A-Z0-9.^:/_-]{0,30}',str(row.get('ticker',''))):raise ValueError('Geldige ticker ontbreekt.')
    for key in ('external_id','component','description'):
        if not isinstance(row.get(key),str) or len(row[key])>500:raise ValueError('Ongeldige kostenreferentie.')
    if not row['external_id'] or not row['component']:raise ValueError('Ongeldige kostenreferentie.')

def pending(db,account_id,provider,row):
    if not row.get('charges'):return False
    ignored=db.execute("SELECT 1 FROM import_issues i JOIN import_batches b ON b.id=i.batch_id WHERE b.account_id=? AND b.provider=? AND i.state='ignored' AND i.resolution='IGNORE' AND json_valid(i.payload) AND json_extract(i.payload,'$.external_id')=? LIMIT 1",(account_id,provider,row['external_id'])).fetchone()
    if ignored:return False
    missing=False
    for item in row['charges']:
        existing,moved=source_charge(db,account_id,provider,row['external_id'],item['component'])
        if not existing:missing=True;continue
        if moved or corrected(db,existing):continue
        if any(str(existing[k])!=str(item[k]) for k in ('category','currency','included_in_net')) or existing['paid_on']!=row['day'] or number(existing['amount'])!=number(item['amount']):raise ValueError('Deze kostenreferentie is eerder met andere gegevens verwerkt.')
    return missing

def book(db,batch_id,account_id,provider,row):
    count=0
    for charge in row.get('charges',[]):
        item={**charge,'external_id':row['external_id'],'ticker':row.get('ticker',''),'paid_on':row['day']}
        validate_charge(item)
        values=(batch_id,account_id,provider,row['external_id'],charge['component'],charge['category'],row.get('ticker',''),str(number(charge['amount'])),code(charge['currency']),row['day'],charge['included_in_net'],charge.get('description',''),now())
        existing,moved=source_charge(db,account_id,provider,row['external_id'],charge['component'])
        if existing:
            if moved or corrected(db,existing):continue
            if any(str(existing[k])!=str(item[k]) for k in ('category','currency','included_in_net','paid_on')) or number(existing['amount'])!=number(item['amount']):raise ValueError('Deze kostenreferentie is eerder met andere gegevens verwerkt.')
            continue
        db.execute('INSERT INTO charges(batch_id,account_id,provider,external_id,component,category,ticker,amount,currency,paid_on,included_in_net,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',values)
        count+=1
    return count

def manual_components(data,currency):
    """Manual transaction inputs are amounts excluding VAT, not percentages."""
    charge_currency=code(str(data.get('charge_currency') or '').strip() or currency)
    components=[]
    for field,category in (('fee_amount','COMMISSION'),('vat_amount','VAT')):
        value=number(str(data.get(field) if data.get(field) is not None else '').strip() or '0')
        if value<0:raise ValueError('Ongeldig kosten- of belastingbedrag.')
        if value:
            components.append(dict(component=field,category=category,amount=str(value),currency=charge_currency,included_in_net=0))
    return components

def book_manual_trade(db,trade,components,fx_trace=None):
    if not components and not fx_trace:return
    import hashlib,json
    raw={key:trade[key] for key in ('id','account_id','symbol','exchange','name','currency','quantity','price','purchased_on','side')}
    raw['charges']=components
    if fx_trace:raw['price_fx']=fx_trace
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
    row=dict(kind='CHARGE',ticker=trade['symbol'],day=trade['purchased_on'],currency=trade['currency'],trade_id=trade['id'],raw=raw,digest=digest,external_id='manual-trade:'+str(trade['id']),charges=[dict(item,description=trade['name']) for item in components])
    batch=db.execute("INSERT INTO import_batches(account_id,provider,filename,digest,payload,status,created_at) VALUES(?,'charges',?,?,?,'imported',?)",(trade['account_id'],'manual-trade-'+str(trade['id']),digest,json.dumps([row]),now())).lastrowid
    book(db,batch,trade['account_id'],'charges',row)
    db.execute("INSERT OR IGNORE INTO transaction_charge_links SELECT id,'trade',? FROM charges WHERE batch_id=?",(trade['id'],batch))
    db.execute("INSERT INTO import_records(batch_id,account_id,provider,external_id,digest,raw) VALUES(?,?,'charges',?,?,?)",(batch,trade['account_id'],row['external_id'],digest,json.dumps(raw)))
    if fx_trace:
        db.execute('INSERT INTO import_fx(batch_id,external_id,kind,source_currency,target_currency,original_amount,converted_amount,rate,requested_on,rate_on,source) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(batch,row['external_id'],trade['side'],fx_trace['from'],fx_trace['to'],fx_trace['amount'],fx_trace['converted'],fx_trace['rate'],fx_trace['requested_on'],fx_trace['rate_on'],fx_trace['source']))


def entries(store,account='all',year='',currency='',view='all'):
    from transactions import scope
    if view not in ('all','taxes'):raise ValueError('Ongeldige rapportselectie.')
    if year and not re.fullmatch(r'\d{4}',str(year)):raise ValueError('Ongeldig rapportjaar.')
    if currency:currency=code(currency)
    with store.read() as db:
        owner=scope(db,account)
        rows=[dict(r) for r in db.execute('SELECT c.*,a.name AS account_name,a.broker FROM charges c JOIN broker_accounts a ON a.id=c.account_id ORDER BY paid_on,id')]
    return [r for r in rows if (view!='taxes' or r['category'] not in FEES) and (owner is None or r['account_id']==owner) and (not year or r['paid_on'].startswith(str(year)+'-')) and (not currency or r['currency']==currency)]

def report(store,account='all',year='',currency='',view='all'):
    rows=entries(store,account,year,currency,view)
    with store.read() as db:rates=[dict(r) for r in db.execute("SELECT quote,day,rate,source FROM fx_rates WHERE base='EUR' ORDER BY day")]
    def group(currency):return dict(currency=currency,fees=Decimal(0),taxes=Decimal(0),total=Decimal(0),included=Decimal(0),additional=Decimal(0),count=0,categories={},months={})
    def add(target,row,value):
        target['count']+=1;target['fees' if row['category'] in FEES else 'taxes']+=value
        target['total']+=value;target['included' if row['included_in_net'] else 'additional']+=value
        target['categories'][row['category']]=target['categories'].get(row['category'],Decimal(0))+value
        month=row['paid_on'][:7];target['months'][month]=target['months'].get(month,Decimal(0))+value
    valid_rates=[]
    for row in rates:
        try:
            date.fromisoformat(row['day'])
            rate=number(row['rate'])
            if rate>0:valid_rates.append({**row,'rate':rate})
        except (ValueError,TypeError):
            continue
    total=group('EUR');native={};missing=[];invalid=[];included=[]
    for row in rows:
        try:
            day=date.fromisoformat(row['paid_on'])
            value=number(row['amount'])
            code(row['currency'])
        except (ValueError,TypeError):
            invalid.append(dict(id=row['id'],currency=row['currency'],paid_on=row['paid_on'],
                                account_name=row['account_name'],ticker=row['ticker']))
            continue
        included.append(row)
        add(native.setdefault(row['currency'],group(row['currency'])),row,value)
        base,scale=unit(row['currency']);found=None
        if base=='EUR':factor=scale;actual=row['paid_on'];source='identity'
        else:
            candidates=[r for r in valid_rates if r['quote']==base and (day-timedelta(days=7)).isoformat()<=r['day']<=row['paid_on']]
            if candidates:found=candidates[-1]
            if not found:
                row.update(eur_amount=None,rate=None,rate_on=None);missing.append(dict(id=row['id'],currency=row['currency'],day=row['paid_on']));continue
            factor=scale/found['rate'];actual=found['day'];source=found['source']
        row.update(eur_amount=str(value*factor),rate=str(factor),rate_on=actual,fx_source=source)
        add(total,row,value*factor)
    def serialize(value):
        if isinstance(value,Decimal):return str(value)
        if isinstance(value,dict):return {k:serialize(v) for k,v in value.items()}
        return value
    return dict(total=serialize(total),currencies=[serialize(g) for _,g in sorted(native.items())],entries=included,missing_fx=missing,invalid=invalid,complete=not (missing or invalid),known_only=True)

def refresh_fx(store,account='all',year='',currency='',view='all'):
    rows=entries(store,account,year,currency,view)
    prepare_rates(store,[(r['currency'],'EUR',r['paid_on']) for r in rows])
    return report(store,account,year,currency,view)

def export_csv(result):
    columns=('paid_on','account_name','broker','category','ticker','amount','currency','included_in_net','eur_amount','rate','rate_on','description')
    out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(columns)
    for row in result['entries']:
        values=[str(row.get(key,'') if row.get(key) is not None else '') for key in columns]
        writer.writerow(["'"+value if value.lstrip().startswith(('=','+','-','@')) else value for value in values])
    return out.getvalue().encode('utf-8-sig')
