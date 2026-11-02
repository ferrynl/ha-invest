"""Local, bounded resource measurements. No provider calls or financial data."""
import os
import shutil
import sys
import threading
import time
import platform
import sqlite3
from datetime import date
from version import APP_VERSION
from pathlib import Path


def process_memory(peak=False):
    try:
        if sys.platform=='win32':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
            value=Counters();value.cb=ctypes.sizeof(value)
            handle=ctypes.windll.kernel32.GetCurrentProcess
            handle.restype=wintypes.HANDLE
            measure=ctypes.windll.psapi.GetProcessMemoryInfo
            measure.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
            if measure(handle(),ctypes.byref(value),value.cb):return value.PeakWorkingSetSize if peak else value.WorkingSetSize
        else:return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    except (OSError,ValueError,IndexError,AttributeError):pass
    return None


def read_number(path):
    try:
        value=Path(path).read_text().strip()
        return int(value) if value!='max' else None
    except (OSError,ValueError):return None


def container_memory():
    current=read_number('/sys/fs/cgroup/memory.current')
    limit=read_number('/sys/fs/cgroup/memory.max')
    if current is None:
        current=read_number('/sys/fs/cgroup/memory/memory.usage_in_bytes')
        limit=read_number('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    return dict(bytes=current,limit_bytes=limit if limit is not None and limit<2**60 else None)


def process_details():
    if sys.platform=='win32':return dict(peak_bytes=process_memory(peak=True))
    result={}
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            key,_,raw=line.partition(':')
            if key in ('VmHWM','RssAnon','RssFile','VmSwap'):
                result[{'VmHWM':'peak_bytes','RssAnon':'anonymous_bytes','RssFile':'file_bytes','VmSwap':'swap_bytes'}[key]]=int(raw.split()[0])*1024
    except (OSError,ValueError,IndexError):pass
    return result


def active_workers():
    # Only fixed application task labels; never locals, arguments or raw stacks.
    labels={'daily_values':'daily','_state':'state','position_histories':'history','overview':'report','fetch_quote':'quotes','fetch_history':'prices','_download_profile':'profile','fetch_holdings':'funds','backup':'backup'}
    result={}
    for frame in sys._current_frames().values():
        label=None
        while frame:
            if Path(frame.f_code.co_filename).parent==Path(__file__).parent and frame.f_code.co_name in labels:
                label=labels[frame.f_code.co_name];break
            frame=frame.f_back
        if label:result[label]=result.get(label,0)+1
    return result


class ResourceMonitor:
    def __init__(self,store,cache):
        self.store=store;self.cache=cache;self.lock=threading.Lock()
        self.started=self.last=time.monotonic();self.cpu=time.process_time();self.storage=None;self.storage_at=0
    def disk(self):
        totals=dict(database_bytes=0,journal_bytes=0,backup_bytes=0,other_bytes=0)
        root=self.store.root
        for folder,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if not (Path(folder)/d).is_symlink()]
            for name in files:
                path=Path(folder)/name
                if path.is_symlink():continue
                try:size=path.stat().st_size
                except OSError:continue
                relative=path.relative_to(root)
                category='database_bytes' if path==self.store.path else 'journal_bytes' if name in (self.store.path.name+'-wal',self.store.path.name+'-shm',self.store.path.name+'-journal') else 'backup_bytes' if relative.parts[0]=='backups' else 'other_bytes'
                totals[category]+=size
        volume=shutil.disk_usage(root)
        with self.store.read() as db:
            page_size=db.execute('PRAGMA page_size').fetchone()[0]
            totals['reusable_bytes']=db.execute('PRAGMA freelist_count').fetchone()[0]*page_size
            totals['cache_payload_bytes']=db.execute('SELECT COALESCE(SUM(length(payload)),0) FROM api_cache').fetchone()[0]
            totals['date_issues']=[dict(day=r[0],count=r[1]) for r in db.execute("SELECT purchased_on,COUNT(*) FROM purchases WHERE purchased_on<'1900-01-01' GROUP BY purchased_on ORDER BY purchased_on")]
            totals['history_start']=db.execute('SELECT MIN(purchased_on) FROM purchases').fetchone()[0]
            totals['quote_start']=db.execute('SELECT MIN(quoted_at) FROM quotes').fetchone()[0]
            totals['estimated_daily_points']=sum(max(0,(date.today()-date.fromisoformat(r[0])).days+1) for r in db.execute('SELECT MIN(purchased_on) FROM purchases GROUP BY account_id,symbol,exchange,currency'))
            totals['listing_count']=db.execute('SELECT COUNT(*) FROM (SELECT 1 FROM purchases GROUP BY account_id,symbol,exchange,currency)').fetchone()[0]
            totals['rows']={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('purchases','daily_prices','quotes','dividends','api_cache')}
        return dict(totals,total_bytes=sum(totals[k] for k in ('database_bytes','journal_bytes','backup_bytes','other_bytes')),volume_total_bytes=volume.total,volume_free_bytes=volume.free)
    def snapshot(self):
        with self.lock:
            now=time.monotonic();cpu=time.process_time();elapsed=now-self.last
            percent=max(0,(cpu-self.cpu)/elapsed*100) if elapsed>=.1 else None
            if elapsed>=.1:self.last=now;self.cpu=cpu
            if self.storage is None or now-self.storage_at>=30:self.storage=self.disk();self.storage_at=now
            return dict(process=dict(process_details(),memory_bytes=process_memory(),cpu_percent=percent,cpu_seconds=cpu,uptime_seconds=now-self.started,threads=threading.active_count()),container=container_memory(),cache=self.cache.statistics(),storage=self.storage,diagnostics=dict(app_version=APP_VERSION,workers=active_workers(),python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=sys.platform),sampled_at=time.time())
