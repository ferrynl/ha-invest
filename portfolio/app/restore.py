"""Import portfolio rows only; never import executable schema or access controls."""
import sqlite3
import tempfile
import re
from pathlib import Path
from contextlib import closing
from datetime import date, datetime
from storage import positive
from migrations import SCHEMA_VERSION

TABLES={
 'purchases':(1,('id','symbol','exchange','name','quantity','price','currency','purchased_on','created_at')),
 'quotes':(1,('id','symbol','exchange','currency','price','quoted_at','fetched_at','source')),
 'daily_prices':(2,('symbol','exchange','currency','day','price')),
 'history_sync':(2,('symbol','exchange','currency','start','synced_on')),
 'dividends':(3,('id','symbol','exchange','currency','amount','paid_on','note','created_at')),
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
                if version<minimum:rows[table]=[];continue
                definition=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
                if not definition or 'VIRTUAL' in definition[0].upper():raise ValueError('De back-up bevat geen geldig portefeuilleschema.')
                data=source.execute(f'SELECT {",".join(columns)} FROM {table} LIMIT 250001').fetchall()
                if len(data)>250000:raise ValueError('Te veel regels in deze back-up.')
                for values in data:
                    row=dict(zip(columns,values))
                    if not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',str(row['symbol'])) or not re.fullmatch(r'[A-Z0-9 _-]{1,40}',str(row['exchange'])) or not re.fullmatch(r'[A-Z]{3}',str(row['currency'])):raise ValueError('Ongeldige beursnotering in back-up.')
                    for key in ('quantity','price','amount'):
                        if key in row:positive(row[key])
                    for key in ('purchased_on','paid_on','day','start','synced_on'):
                        if key in row:
                            day=date.fromisoformat(row[key])
                            if day>date.today():raise ValueError('De back-up bevat toekomstige datums.')
                    for key in ('quoted_at','fetched_at','created_at'):
                        if key in row:
                            stamp=datetime.fromisoformat(row[key].replace('Z','+00:00'))
                            if stamp.tzinfo is None:raise ValueError('Ongeldige tijdzone in back-up.')
                    for key,value in row.items():
                        if key!='id' and (not isinstance(value,str) or len(value)>500):raise ValueError('Ongeldige gegevens in back-up.')
                rows[table]=data
            default_range='1M'
            if version>=4:
                setting=source.execute("SELECT value FROM app_settings WHERE key='default_range'").fetchone()
                if setting and setting[0] in ('1W','1M','3M','6M','YTD','1Y','ALL'):default_range=setting[0]
        # Live schema, users and authentication stay intact, including when restoring old backups.
        with store.lock:
            safety=store.backup();safety_folder=store.root/'backups'/'restores';safety_folder.mkdir(exist_ok=True)
            safety.rename(safety_folder/('before-restore-'+safety.name))
            with store.connect() as target:
                for table in TABLES:target.execute(f'DELETE FROM {table}')
                for table,(_,columns) in TABLES.items():
                    target.executemany(f'INSERT INTO {table} ({",".join(columns)}) VALUES({",".join("?" for _ in columns)})',rows[table])
                target.execute("UPDATE app_settings SET value=? WHERE key='default_range'",(default_range,))
        return {table:len(data) for table,data in rows.items()}
