"""Import portfolio rows only; never import executable schema or access controls."""
import sqlite3
import json
import tempfile
import re
from pathlib import Path
from contextlib import closing
from datetime import date, datetime
from storage import positive
from migrations import SCHEMA_VERSION

TABLES={
 'instrument_valuations':(15,('symbol','exchange','currency','price','day','updated_at')),
 'broker_accounts':(6,('id','name','broker','created_at')),
 'purchases':(1,('id','symbol','exchange','name','quantity','price','currency','purchased_on','created_at','account_id','side','trade_time','split_before','transfer_id','transfer_cost','transfer_invested')),
 'instrument_categories':(13,('symbol','exchange','currency','sector','country','asset_type','category','updated_at','manual_sector','manual_country','manual_asset_type')),
 'instrument_category_sync':(14,('symbol','exchange','currency','status','attempted_at','retry_at','attempts','error_code')),
 'quotes':(1,('id','symbol','exchange','currency','price','quoted_at','fetched_at','source')),
 'daily_prices':(2,('symbol','exchange','currency','day','price')),
 'history_sync':(2,('symbol','exchange','currency','start','synced_on')),
 'dividends':(3,('id','symbol','exchange','currency','amount','paid_on','note','created_at','account_id')),
 'import_batches':(6,('id','account_id','provider','filename','digest','payload','status','created_at')),
 'import_issues':(10,('id','batch_id','line','state','reason','payload','resolution','updated_at')),
 'capital_returns':(10,('id','batch_id','account_id','provider','external_id','ticker','isin','amount','currency','paid_on','created_at')),
 'charges':(20,('id','batch_id','account_id','provider','external_id','component','category','ticker','amount','currency','paid_on','included_in_net','description','created_at')),
 'transaction_edits':(12,('id','kind','record_id','account_id','before_payload','after_payload','changed_by','created_at')),
 'instrument_mappings':(9,('id','account_id','provider','identity','ticker','isin','source_currency','symbol','exchange','currency','name','origin','updated_at')),
 'import_records':(6,('id','batch_id','account_id','provider','external_id','digest','raw')),
 'api_cache':(6,('namespace','cache_key','payload','fetched_at','expires_at')),
 'fx_currencies':(8,('code','name','updated_at')),
 'fx_rates':(8,('base','quote','day','rate','source','fetched_at')),
 'fx_coverage':(8,('currency','start','end','checked_at')),
 'import_fx':(8,('id','batch_id','external_id','kind','source_currency','target_currency','original_amount','converted_amount','rate','requested_on','rate_on','source')),
}

def restore_backup(store,content):
    if not content.startswith(b'SQLite format 3\x00') or len(content)>25*1024*1024:raise ValueError('Kies een geldige SQLite-back-up van maximaal 25 MB.')
    with tempfile.TemporaryDirectory(prefix='.restore-',dir=store.root) as folder:
        uploaded=Path(folder)/'input.sqlite3';uploaded.write_bytes(content)
        rows={}
        with closing(sqlite3.connect(uploaded.as_uri()+'?mode=ro&immutable=1',uri=True)) as source:
            source.execute('PRAGMA trusted_schema=OFF')
            version=source.execute('PRAGMA user_version').fetchone()[0]
            if not 1<=version<=SCHEMA_VERSION:raise ValueError('Deze databaseversie wordt niet ondersteund.')
            if source.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('De back-up is beschadigd.')
            for table,(minimum,columns) in TABLES.items():
                if version<minimum:
                    rows[table]=[(1,'Handmatig','Handmatig',datetime.now().astimezone().isoformat())] if table=='broker_accounts' else []
                    continue
                definition=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
                if not definition or 'VIRTUAL' in definition[0].upper():raise ValueError('De back-up bevat geen geldig portefeuilleschema.')
                source_columns=columns
                if table=='instrument_categories' and version<14:source_columns=columns[:-3]
                if table=='purchases':
                    source_columns=columns if version>=19 else columns[:-3] if version>=11 else columns[:-4] if version>=6 else columns[:-7]
                if version<6 and table=='dividends':source_columns=columns[:-1]
                data=source.execute(f'SELECT {",".join(source_columns)} FROM {table} LIMIT 250001').fetchall()
                # Derived financial snapshots from uploads must never be trusted.
                if table=='api_cache':data=[row for row in data if not str(row[0]).startswith('dashboard:')]
                if table=='instrument_categories' and version<14:data=[(*r,int(bool(r[3])),int(bool(r[4])),int(bool(r[5]))) for r in data]
                if version<6 and table=='purchases':data=[(*r,1,'BUY','') for r in data]
                if version<6 and table=='dividends':data=[(*r,1) for r in data]
                if table=='purchases' and version<11:data=[(*r,'') for r in data]
                if table=='purchases' and version<19:data=[(*r,'','','') for r in data]
                if len(data)>250000:raise ValueError('Te veel regels in deze back-up.')
                for values in data:
                    row=dict(zip(columns,values))
                    if table=='charges':
                        from charges import validate_charge
                        validate_charge(row)
                    if table=='import_issues' and row['state'] not in ('pending','resolved','ignored'):raise ValueError('Ongeldige importstatus in back-up.')
                    if table=='instrument_mappings':
                        from imports import ADAPTERS
                        if row['origin'] not in ('pending','automatic','manual') or row['provider'] not in ADAPTERS:raise ValueError('Ongeldige instrumentkoppeling in back-up.')
                        if row['identity']!=('isin:'+row['isin'] if row['isin'] else 'ticker:'+row['ticker'].strip().upper()):raise ValueError('Ongeldige instrumentidentiteit in back-up.')
                        if not row['symbol'] and (row['exchange'] or row['currency'] or row['origin']!='pending'):raise ValueError('Onvolledige instrumentkoppeling in back-up.')
                    if table=='instrument_category_sync':
                        if row['status'] not in ('fetching','complete','partial','retry') or not isinstance(row['attempts'],int) or row['attempts']<1 or not re.fullmatch(r'[a-z0-9_]{0,60}',str(row['error_code'])):raise ValueError('Ongeldige profielstatus in back-up.')
                    if table=='instrument_categories':
                        from instruments import validate_categories
                        validate_categories(row)
                    if table=='transaction_edits':
                        if row['kind'] not in ('trade','dividend','capital'):raise ValueError('Ongeldig transactietype in wijzigingshistorie.')
                        for field in ('before_payload','after_payload'):
                            try:value=json.loads(row[field])
                            except (ValueError,TypeError):raise ValueError('Ongeldige wijzigingshistorie.')
                            if not isinstance(value,dict) or value.get('id')!=row['record_id'] or value.get('account_id')!=row['account_id']:raise ValueError('Ongeldige wijzigingshistorie.')
                    for key in ('code','base','quote','currency','source_currency','target_currency'):
                        if key in row and not (table=='instrument_mappings' and key=='currency' and row[key]=='') and not re.fullmatch('[A-Z]{3}',str(row[key])):raise ValueError('Ongeldige valutacode in back-up.')
                    if 'symbol' in row and not (table=='instrument_mappings' and row['symbol']=='') and (not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',str(row['symbol'])) or not re.fullmatch(r'[A-Z0-9 _-]{1,40}',str(row['exchange'])) or not re.fullmatch(r'[A-Z]{3}',str(row['currency']))):raise ValueError('Ongeldige beursnotering in back-up.')
                    if table=='purchases' and row['split_before'] not in ('','0'):positive(row['split_before'])
                    if table=='purchases' and row['split_before'] and row['side']!='BUY':raise ValueError('Ongeldige splitsing in back-up.')
                    for key in ('quantity','price','amount','rate','original_amount','converted_amount'):
                        if key in row:
                            if table=='instrument_valuations' and key=='price':
                                from valuations import validate_price
                                validate_price(row[key])
                            elif not (table=='charges' and key=='amount'):positive(row[key])
                    for key in ('purchased_on','paid_on','day','start','end','synced_on','requested_on','rate_on'):
                        if key in row:
                            day=date.fromisoformat(row[key])
                            if day>date.today():raise ValueError('De back-up bevat toekomstige datums.')
                    for key in ('quoted_at','fetched_at','created_at','updated_at','checked_at','attempted_at','retry_at'):
                        if key in row and not (table=='api_cache' and key=='fetched_at'):
                            stamp=datetime.fromisoformat(row[key].replace('Z','+00:00'))
                            if stamp.tzinfo is None:raise ValueError('Ongeldige tijdzone in back-up.')
                    for key,value in row.items():
                        if key in ('manual_sector','manual_country','manual_asset_type','included_in_net'):
                            if not isinstance(value,int) or value not in (0,1):raise ValueError('Ongeldige handmatige categorie in back-up.')
                        elif table=='instrument_category_sync' and key=='attempts':pass
                        elif key in ('id','account_id','batch_id','line','record_id'):
                            if not isinstance(value,int) or value<1:raise ValueError('Ongeldig recordnummer in back-up.')
                        elif key in ('fetched_at','expires_at') and table=='api_cache':
                            if not isinstance(value,(int,float)):raise ValueError('Ongeldige cachetijd.')
                        elif not isinstance(value,str) or len(value)>(20*1024*1024 if key in ('payload','raw','before_payload','after_payload') else 500):raise ValueError('Ongeldige gegevens in back-up.')
                rows[table]=data
            default_range='1M'
            from conversions import validate_pairs
            validate_pairs([dict(zip(TABLES['purchases'][1],r)) for r in rows['purchases']])
            if version>=4:
                setting=source.execute("SELECT value FROM app_settings WHERE key='default_range'").fetchone()
                if setting and setting[0] in ('1W','1M','3M','6M','YTD','1Y','ALL'):default_range=setting[0]
        # Live schema, users and authentication stay intact, including when restoring old backups.
        with store.lock:
            safety=store.backup();safety_folder=store.root/'backups'/'restores';safety_folder.mkdir(exist_ok=True)
            safety.rename(safety_folder/('before-restore-'+safety.name))
            with store.connect() as target:
                for table in reversed(TABLES):target.execute(f'DELETE FROM {table}')
                for table,(_,columns) in TABLES.items():
                    target.executemany(f'INSERT INTO {table} ({",".join(columns)}) VALUES({",".join("?" for _ in columns)})',rows[table])
                target.execute("UPDATE app_settings SET value=? WHERE key='default_range'",(default_range,))
                if target.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('De back-up verwijst naar ontbrekende accounts of importbatches.')
                if target.execute('SELECT 1 FROM charges c JOIN import_batches b ON b.id=c.batch_id WHERE c.account_id!=b.account_id OR c.provider!=b.provider LIMIT 1').fetchone():raise ValueError('Ongeldige kostenreferentie.')
                from history import daily_values
                for key in target.execute('SELECT DISTINCT account_id,symbol,exchange,currency FROM purchases').fetchall():
                    lots=[dict(row) for row in target.execute('SELECT * FROM purchases WHERE account_id=? AND symbol=? AND exchange=? AND currency=?',tuple(key))]
                    daily_values(lots,[],[])
        store._mapping_discovered=False
        return {table:len(data) for table,data in rows.items()}
