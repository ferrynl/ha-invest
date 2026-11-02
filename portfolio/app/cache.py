"""Revision-aware RAM and compressed SQLite snapshots. Never cache authorization."""
import time
import json
import zlib
import base64
import sys
from datetime import date
from threading import RLock
from weakref import WeakValueDictionary
from version import APP_VERSION
MEMORY_BUDGET=64*1024*1024

def memory_size(value,limit=MEMORY_BUDGET):
    """Conservative object size with bounded traversal; shared references overcount."""
    size=sys.getsizeof(value)
    items=value.items() if isinstance(value,dict) else ((None,v) for v in value) if isinstance(value,(list,tuple)) else ()
    for key,item in items:
        size+=sys.getsizeof(key) if key is not None else 0
        size+=memory_size(item,max(0,limit-size))
        if size>limit:break
    return size

class StateCache:
    def __init__(self,ttl=30,store=None):
        self.ttl=ttl;self.lock=RLock();self.value=None;self.expires=0;self.store=store;self.entries={};self.build_locks=WeakValueDictionary();self.generation=0;self.pruned_store=None;self.active={};self.measurements={}
    def bind(self,store):
        with self.lock:
            if self.store is not store:
                self.value=None;self.expires=0;self.entries.clear();self.store=store;self.generation+=1
            if self.pruned_store is not store:
                # Discard obsolete derived views, preserving all ledger/provider data.
                with store.read() as db:db.execute("DELETE FROM api_cache WHERE namespace LIKE 'dashboard:%' AND (namespace NOT LIKE ? OR expires_at<?)",('dashboard:'+APP_VERSION+':%',time.time()))
                self.pruned_store=store
        return self
    def invalidate(self):
        with self.lock:
            self.value=None;self.expires=0;self.entries.clear();self.generation+=1
            store=self.store
        if store is not None:
            with store.read() as db:db.execute("DELETE FROM api_cache WHERE namespace LIKE 'dashboard:%'")
    def get(self,loader):
        if self.store is not None:return self.derived('state',loader)
        with self.lock:
            if self.value is None or time.monotonic()>=self.expires:
                self.value=loader();self.expires=time.monotonic()+self.ttl
            return self.value
    def statistics(self):
        with self.lock:
            return dict(bytes=sum(e[2] for e in self.entries.values()),budget_bytes=MEMORY_BUDGET,entries=len(self.entries),active=[dict(view=slot.split(':')[0],seconds=round(time.monotonic()-started,2)) for slot,started in self.active.items()],measurements=[dict(view=family,**values) for family,values in self.measurements.items()])
    def derived(self,slot,loader):
        # Only identical views wait for each other. Heavy report builds must not
        # hold the shared RAM lock or block unrelated cached Home/state requests.
        with self.lock:
            store=self.store
            if store is None:return loader()
            slot_lock=self.build_locks.get(slot)
            if slot_lock is None:
                slot_lock=RLock();self.build_locks[slot]=slot_lock
        with slot_lock:
            with self.lock:generation=self.generation
            with store.read() as db:revision=db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]
            key=f'{date.today().isoformat()}:{revision}'
            namespace='dashboard:'+APP_VERSION+':'+slot
            with self.lock:
                existing=self.entries.get(slot) if self.store is store else None
                if existing and existing[0]==key:
                    self.entries.pop(slot);self.entries[slot]=existing
                    return existing[1]
            with store.read() as db:
                saved=db.execute('SELECT payload FROM api_cache WHERE namespace=? AND cache_key=? AND expires_at>?',(namespace,key,time.time())).fetchone()
            result=None
            if saved:
                try:
                    raw=zlib.decompress(base64.b64decode(saved['payload']));result=json.loads(raw)
                    if not isinstance(result,dict):result=None
                except (ValueError,TypeError,zlib.error):pass
            if result is None:
                started=time.monotonic();family=slot.split(':')[0]
                with self.lock:self.active[slot]=started
                try:result=loader()
                finally:
                    with self.lock:
                        self.active.pop(slot,None)
                        measurement=self.measurements.setdefault(family,dict(builds=0,oversized=0,last_seconds=0,max_seconds=0))
                        duration=time.monotonic()-started;measurement['builds']+=1;measurement['last_seconds']=round(duration,3);measurement['max_seconds']=round(max(duration,measurement['max_seconds']),3)
                size=memory_size(result)
                # Do not serialise oversized expanded histories into more copies.
                if size>MEMORY_BUDGET:
                    with self.lock:
                        self.entries.pop(slot,None);self.measurements[family]['oversized']+=1
                    return result
                raw=json.dumps(result,separators=(',',':')).encode()
                payload=base64.b64encode(zlib.compress(raw,1)).decode()
                with store.read() as db:
                    db.execute('BEGIN IMMEDIATE')
                    current=db.execute('SELECT revision FROM dashboard_revision WHERE id=1').fetchone()[0]
                    with self.lock:valid=self.store is store and generation==self.generation
                    if current!=revision or not valid:return result
                    db.execute('DELETE FROM api_cache WHERE namespace=?',(namespace,))
                    stamp=time.time()
                    db.execute('INSERT INTO api_cache VALUES(?,?,?,?,?)',(namespace,key,payload,stamp,stamp+86400))
                    db.execute("DELETE FROM api_cache WHERE namespace LIKE 'dashboard:%' AND expires_at<?",(stamp,))
            else:size=memory_size(result)
            with self.lock:
                if self.store is not store or generation!=self.generation:return result
                self.entries.pop(slot,None)
                while self.entries and (len(self.entries)>=16 or sum(entry[2] for entry in self.entries.values())+size>MEMORY_BUDGET):
                    self.entries.pop(next(iter(self.entries)))
                if size<=MEMORY_BUDGET:self.entries[slot]=(key,result,size)
            return result
