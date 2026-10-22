"""Listing details and explicit report categories; never infer an issuer from its exchange."""
import json
import re
from storage import now
from transactions import scope

FIELDS=('sector','country','asset_type','category')
ASSET_TYPES=('', 'Aandeel', 'ETF', 'Beleggingsfonds', 'Obligatie', 'REIT', 'Overig')

def identity(data):
    key=tuple(str(data.get(k,'')).strip().upper() for k in ('symbol','exchange','currency'))
    if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',key[0]) or not re.fullmatch(r'[A-Z0-9 _-]{1,40}',key[1]) or not re.fullmatch(r'[A-Z]{3}',key[2]):raise ValueError('Ongeldige beursnotering.')
    return key

def validate_categories(data):
    result={}
    for field in FIELDS:
        value=data.get(field,'')
        if not isinstance(value,str) or len(value)>80 or any(not c.isprintable() for c in value):raise ValueError('Categorievelden bevatten maximaal 80 leesbare tekens.')
        result[field]=value.strip()
    if result['asset_type'] not in ASSET_TYPES:raise ValueError('Kies een geldig type belegging.')
    return result

def save_categories(store,data):
    key=identity(data);values=validate_categories(data)
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM purchases WHERE symbol=? AND exchange=? AND currency=? UNION ALL SELECT 1 FROM dividends WHERE symbol=? AND exchange=? AND currency=?',(*key,*key)).fetchone():raise ValueError('Aandeel niet gevonden.')
        db.execute('INSERT INTO instrument_categories VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(symbol,exchange,currency) DO UPDATE SET sector=excluded.sector,country=excluded.country,asset_type=excluded.asset_type,category=excluded.category,updated_at=excluded.updated_at',(*key,*(values[k] for k in FIELDS),now()))
    return dict(ok=True)

def details(store,data,account='all',include_pending=True):
    key=identity(data)
    with store.connect() as db:
        account_id=scope(db,account)
        restriction='' if account_id is None else ' AND account_id=?'
        args=key if account_id is None else (*key,account_id)
        trades=[dict(r) for r in db.execute('SELECT * FROM purchases WHERE symbol=? AND exchange=? AND currency=?'+restriction,args)]
        dividends=[dict(r) for r in db.execute('SELECT * FROM dividends WHERE symbol=? AND exchange=? AND currency=?'+restriction,args)]
        if not trades and not dividends:raise ValueError('Aandeel niet gevonden in dit brokeraccount.')
        categories=db.execute('SELECT * FROM instrument_categories WHERE symbol=? AND exchange=? AND currency=?',key).fetchone()
        prices=[dict(r) for r in db.execute('SELECT day,price FROM daily_prices WHERE symbol=? AND exchange=? AND currency=? ORDER BY day',key)]
        quote=db.execute('SELECT price,quoted_at,source FROM quotes WHERE symbol=? AND exchange=? AND currency=? ORDER BY quoted_at DESC,id DESC LIMIT 1',key).fetchone()
        accounts={r['id']:r['name'] for r in db.execute('SELECT id,name FROM broker_accounts')}
        mappings={}
        for source in db.execute("SELECT * FROM instrument_mappings WHERE symbol<>''"):
            row=dict(source);mappings.setdefault((row['account_id'],row['provider'],row['identity']),[]).append(row)
        def mapped(owner,provider,raw,ticker,source_currency):
            source_id='isin:'+raw['ISIN'] if raw.get('ISIN') else 'ticker:'+str(ticker).strip().upper()
            candidates=mappings.get((owner,provider,source_id),[])
            exact=[r for r in candidates if r['source_currency']==source_currency]
            targets={(r['symbol'],r['exchange'],r['currency']) for r in exact or candidates}
            return targets=={key}
        events=[]
        for row in trades:
            events.append(dict(row,kind='trade',type='SPLIT' if row['split_before'] else row['side'],day=row['purchased_on'],status='Geboekt'))
        for row in dividends:events.append(dict(row,kind='dividend',type='DIVIDEND',day=row['paid_on'],status='Geboekt'))
        capital_sql='SELECT c.*,r.raw FROM capital_returns c LEFT JOIN import_records r ON r.account_id=c.account_id AND r.provider=c.provider AND r.external_id=c.external_id'
        for source in db.execute(capital_sql):
            row=dict(source)
            if account_id is not None and row['account_id']!=account_id:continue
            raw=json.loads(row.pop('raw') or '{}')
            if mapped(row['account_id'],row['provider'],raw,row['ticker'],row['currency']):events.append(dict(row,kind='capital',type='CAPITAL_RETURN',day=row['paid_on'],status='Geboekt in bronvaluta'))
        pending_rows=db.execute("SELECT i.*,b.account_id,b.provider FROM import_issues i JOIN import_batches b ON b.id=i.batch_id WHERE i.state='pending'") if include_pending else ()
        for source in pending_rows:
            issue=dict(source)
            if account_id is not None and issue['account_id']!=account_id:continue
            row=json.loads(issue['payload']);raw=row.get('raw',{})
            if mapped(issue['account_id'],issue['provider'],raw,row.get('ticker',''),row.get('currency','')):
                events.append(dict(id=issue['id'],kind='issue',type=raw.get('Action') or row.get('kind') or 'Onbekend',day=row.get('day') or raw.get('Time (UTC)',raw.get('Time',''))[:10],trade_time=row.get('trade_time',''),account_id=issue['account_id'],quantity=row.get('quantity'),amount=row.get('amount'),price=row.get('price'),currency=row.get('currency',''),status='Te beoordelen',note=issue['reason']))
        for event in events:event['account_name']=accounts[event['account_id']]
        events.sort(key=lambda r:(r['day'],r.get('trade_time',''),r['id']),reverse=True)
        return dict(symbol=key[0],exchange=key[1],currency=key[2],name=trades[0]['name'] if trades else key[0],categories=dict(categories) if categories else {field:'' for field in FIELDS},prices=prices,quote=dict(quote) if quote else None,events=events,account_id=account)
