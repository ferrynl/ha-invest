"""Defeat Beta fundamentals, isolated from portfolio prices and accounting.

Query the published dataset directly to avoid the API package's notebook/AI
dependencies. A bounded child process keeps remote Parquet work off HTTP threads.
"""
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE='https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/'
SOURCE='Defeat Beta · Yahoo Finance · Hugging Face'
NAMESPACE='defeatbeta-fundamentals-v1'
_query_lock=Lock()
ITEMS={'total_revenue':'revenue','net_income':'net_income','operating_cash_flow':'operating_cash_flow','free_cash_flow':'free_cash_flow'}

def supported(key):
    return key[1] in ('NASDAQ','NYSE','AMEX','NYSEAMERICAN','NMS','NGM','NCM','NYQ','ASE') and key[2]=='USD' and bool(re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',key[0]))

def read_json(path):
    request=Request(BASE+'raw/main/'+path,headers={'User-Agent':'HomeInvest/1.0','Accept':'application/json'})
    for attempt in range(2):
        try:
            with urlopen(request,timeout=10) as response:
                raw=response.read(4*1024*1024+1)
            break
        except HTTPError:raise
        except (URLError,TimeoutError):
            if attempt:raise
    if len(raw)>4*1024*1024:raise ValueError('oversized_dataset')
    return json.loads(raw)

def query_rows(symbol):
    # Fixed module and validated ticker only; never execute dataset content.
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--query',symbol],capture_output=True,text=True,timeout=40,check=True)
    return json.loads(result.stdout)

def normalize(rows,currency):
    observations={}
    for report_day,item,value in rows:
        report_day=str(report_day)
        if item not in ITEMS or date.fromisoformat(report_day)>date.today():continue
        amount=Decimal(str(value)) if value is not None else None
        if amount is not None and not amount.is_finite():continue
        observations.setdefault(report_day,{})[ITEMS[item]]=None if amount is None else str(amount)
    periods=[]
    for day,values in sorted(observations.items(),reverse=True)[:4]:
        # Missing items remain unknown; never fill from a different fiscal year.
        margin=None
        if values.get('revenue') and Decimal(values['revenue'])>0 and values.get('net_income') is not None:
            margin=str(Decimal(values['net_income'])/Decimal(values['revenue'])*100)
        periods.append(dict(day=day,currency=currency,net_margin=margin,**{field:values.get(field) for field in ITEMS.values()}))
    return periods

def load(symbol):
    catalog=read_json('data/US/company_tickers.json')
    entries=catalog.values() if isinstance(catalog,dict) else catalog
    matches=[entry for entry in entries if entry.get('ticker')==symbol]
    if len(matches)!=1:return dict(status='no_data',source=SOURCE,periods=[])
    entry=matches[0];currency=entry.get('financial_currency','')
    if not re.fullmatch('[A-Z]{3}',currency):raise ValueError('missing_financial_currency')
    spec=read_json('spec.json')
    updated=spec['files']['US/stock_statement.parquet']
    datetime.fromisoformat(updated.replace('Z','+00:00'))
    periods=normalize(query_rows(symbol),currency)
    return dict(status='ok' if periods else 'no_data',source=SOURCE,symbol=symbol,company_name=entry.get('title',''),currency=currency,dataset_updated_at=updated,fetched_at=datetime.now(timezone.utc).isoformat(),periods=periods)

def fetch(store,key):
    if not supported(key):return dict(status='unsupported',source=SOURCE,periods=[])
    cache_key='|'.join(key);stamp=time.time()
    with store.read() as db:
        saved=db.execute('SELECT payload,expires_at FROM api_cache WHERE namespace=? AND cache_key=?',(NAMESPACE,cache_key)).fetchone()
        retry=db.execute('SELECT expires_at FROM api_cache WHERE namespace=? AND cache_key=?',(NAMESPACE+'-retry',cache_key)).fetchone()
    previous=json.loads(saved['payload']) if saved else None
    if saved and saved['expires_at']>stamp:return previous
    def unavailable():
        return dict(previous,stale=True) if previous and previous.get('status')=='ok' else dict(status='unavailable',source=SOURCE,periods=[])
    if retry and retry['expires_at']>stamp:return unavailable()
    if not _query_lock.acquire(blocking=False):return unavailable()
    try:
        result=load(key[0]);stamp=time.time()
        with store.connect() as db:
            db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',(NAMESPACE,cache_key,json.dumps(result),stamp,stamp+86400))
            db.execute('DELETE FROM api_cache WHERE namespace=? AND cache_key=?',(NAMESPACE+'-retry',cache_key))
        return result
    except Exception as error:
        # Keep the last successful answer, suppress bodies/transport credentials.
        with store.connect() as db:db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',(NAMESPACE+'-retry',cache_key,'{}',stamp,stamp+900))
        from diagnostics import record
        record(store,'WARNING','market','fundamentals_failed','Defeat Beta is tijdelijk niet beschikbaar. Probeer later opnieuw.',{'symbol':key[0],'provider':'Defeat Beta','error_type':type(error).__name__})
        return unavailable()
    finally:_query_lock.release()

def worker(symbol):
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',symbol):raise ValueError('invalid_symbol')
    import duckdb
    with duckdb.connect(config={'memory_limit':'192MB','threads':'1','max_temp_directory_size':'0B'}) as db:
        db.execute('LOAD httpfs')
        db.execute('SET http_timeout=10')
        db.execute('SET http_retries=1')
        rows=db.execute("SELECT report_date,item_name,item_value FROM read_parquet(?) WHERE symbol=? AND period_type='annual' AND ((finance_type='income_statement' AND item_name IN ('total_revenue','net_income')) OR (finance_type='cash_flow' AND item_name IN ('operating_cash_flow','free_cash_flow'))) ORDER BY report_date DESC LIMIT 32",[BASE+'resolve/main/data/US/stock_statement.parquet',symbol]).fetchall()
    print(json.dumps(rows,default=str))

if __name__=='__main__':
    worker(sys.argv[2])
