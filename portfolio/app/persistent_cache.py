"""Persist successful provider responses; cache survives restarts and back-ups."""
import json
import time
from threading import RLock

_lock=RLock()
def cached_json(store,namespace,key,ttl,loader):
    if store is None:return loader()
    with _lock:
        with store.connect() as db:
            row=db.execute('SELECT payload,expires_at FROM api_cache WHERE namespace=? AND cache_key=?',(namespace,key)).fetchone()
        if row and row['expires_at']>time.time():return json.loads(row['payload'])
        result=loader()
        stamp=time.time()
        with store.connect() as db:
            db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',(namespace,key,json.dumps(result),stamp,stamp+ttl))
        return result
