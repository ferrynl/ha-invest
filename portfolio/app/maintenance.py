"""Explicit, backed-up housekeeping. Financial ledgers and daily closes stay intact."""
import gc
import hashlib
import hmac
import json
import time
from pathlib import Path
from diagnostics import record

CACHE_WHERE="(namespace LIKE 'dashboard:%' OR (expires_at<? AND namespace NOT IN ('fund-task-status','fund-refresh','provider-cooldown','trading212')))"
REDUNDANT="SELECT id FROM (SELECT id,ROW_NUMBER() OVER (PARTITION BY symbol,exchange,currency,substr(quoted_at,1,10) ORDER BY quoted_at DESC,id DESC) AS rank FROM quotes) WHERE rank>1"

def options(data):
    if not isinstance(data,dict):raise ValueError('Kies minstens één onderdeel om op te schonen.')
    result={key:data.get(key,True) for key in ('caches','quotes','backups','compact')}
    if any(type(value) is not bool for value in result.values()) or not any(result.values()):raise ValueError('Kies minstens één onderdeel om op te schonen.')
    return result

def backups(store):
    folder=store.root/'backups'
    if folder.is_symlink():raise ValueError('De back-upmap kan niet veilig worden opgeschoond.')
    root=folder.resolve()
    return sorted((p for p in folder.glob('portfolio-*.sqlite3') if not p.is_symlink() and p.resolve().parent==root and p.is_file()),key=lambda p:p.name)

def preview(store,data):
    selected=options(data);stamp=time.time();files=backups(store)
    with store.read() as db:
        revision=db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]
        cache_count,cache_bytes=db.execute('SELECT COUNT(*),COALESCE(SUM(length(payload)),0) FROM api_cache WHERE '+CACHE_WHERE,(stamp,)).fetchone()
        quote_count=db.execute('SELECT COUNT(*) FROM ('+REDUNDANT+')').fetchone()[0] if selected['quotes'] else 0
        all_quotes=db.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]
        page=db.execute('PRAGMA page_size').fetchone()[0];free=db.execute('PRAGMA freelist_count').fetchone()[0]*page
    # The new recovery backup is included among the five retained files.
    obsolete=files[:max(0,len(files)-4)] if selected['backups'] else []
    result=dict(options=selected,revision=revision,cache_count=cache_count if selected['caches'] else 0,cache_bytes=cache_bytes if selected['caches'] else 0,quote_count=quote_count,quotes_kept=all_quotes-quote_count,backup_count=len(obsolete),backup_bytes=sum(p.stat().st_size for p in obsolete),reusable_bytes=free,database_bytes=store.path.stat().st_size,retain_backups=5 if selected['backups'] else None)
    signature=dict(result,files=[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in files])
    result['review']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    return result

def clean(store,cache,data):
    if data.get('confirmation')!='OPSCHONEN':raise ValueError('Controleer eerst het opschoonoverzicht.')
    with store.lock:
        plan=preview(store,data.get('options',{}))
        if not hmac.compare_digest(str(data.get('review','')),plan['review']):raise ValueError('De gegevens zijn gewijzigd. Maak een nieuw opschoonoverzicht.')
        original_files=backups(store)
        backup=store.backup(retain=False)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if plan['options']['caches']:db.execute('DELETE FROM api_cache WHERE '+CACHE_WHERE,(time.time(),))
            if plan['options']['quotes']:db.execute('DELETE FROM quotes WHERE id IN ('+REDUNDANT+')')
            if plan['options']['backups']:db.execute("INSERT OR REPLACE INTO app_settings VALUES('backup_retention','5')")
        cache.invalidate();compacted=False
        if plan['options']['compact']:
            try:
                with store.read() as db:
                    db.execute('PRAGMA busy_timeout=5000');db.execute('VACUUM');db.execute('PRAGMA optimize')
                compacted=True
            except Exception as error:
                record(store,'WARNING','system','cleanup_compaction_failed','Database verkleinen kon nu niet worden afgerond.',{'error_type':type(error).__name__})
        removed=0
        if plan['options']['backups']:
            root=(store.root/'backups').resolve()
            for path in original_files[:max(0,len(original_files)-4)]:
                if path.is_symlink() or path.resolve().parent!=root:continue
                path.unlink();removed+=1
        gc.collect()
        result=dict(ok=True,backup_name=backup.name,cache_count=plan['cache_count'],quote_count=plan['quote_count'],backup_count=removed,compacted=compacted,database_before=plan['database_bytes'],database_after=store.path.stat().st_size)
        record(store,'INFO','system','cleanup_completed','Gegevensopslag opgeschoond; boekingen en dagelijkse koershistorie behouden.',{k:v for k,v in result.items() if k!='backup_name'})
        return result
