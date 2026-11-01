"""One explicit, cancellable ETF update queue per portfolio. GET never calls issuers."""
import copy
import json
import re
import threading
import time
from datetime import datetime, timezone
from fund_holdings import saved, refresh, KNOWN
from fund_providers import discover, issuer_name, FundSourceUnavailable

_lock = threading.RLock()
_jobs = {}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def candidates(store):
    with store.read() as db:
        rows = db.execute("SELECT p.symbol,p.exchange,p.currency,MAX(p.name) name,MAX(c.asset_type) asset_type FROM purchases p LEFT JOIN instrument_categories c ON c.symbol=p.symbol AND c.exchange=p.exchange AND c.currency=p.currency GROUP BY p.symbol,p.exchange,p.currency ORDER BY name").fetchall()
        mappings = db.execute("SELECT symbol,exchange,currency,isin FROM instrument_mappings WHERE isin<>'' AND symbol<>''").fetchall()
    identities = {}
    for m in mappings:
        identities.setdefault(tuple(m[k] for k in ('symbol', 'exchange', 'currency')), set()).add(m['isin'])
    result = []
    for row in rows:
        row = dict(row)
        key = tuple(row[k] for k in ('symbol', 'exchange', 'currency'))
        previous = saved(store, key)
        if row['asset_type'] != 'ETF' and not re.search(r'\bETF\b', row['name'], re.I) and key not in KNOWN and not previous:
            continue
        isins = identities.get(key, set())
        row.update(isin=next(iter(isins)) if len(isins) == 1 else row['symbol'] if re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d', row['symbol']) else '',
                   issuer=issuer_name(row['name']), status='ready', message='', source_url=previous['source_url'] if previous else KNOWN.get(key, ''),
                   as_of=previous['as_of'] if previous else '', count=len(previous['holdings']) if previous else 0,
                   stale=previous['stale'] if previous else False)
        result.append(row)
    return result


def key(store):
    return str(store.path.resolve())


def persist(store, state):
    now = time.time()
    with store.connect() as db:
        db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',
                   ('fund-task-status', 'latest', json.dumps(state), now, now + 30 * 86400))


def status(store):
    with _lock:
        job = _jobs.get(key(store))
        if job:
            return copy.deepcopy(job['state'])
    with store.read() as db:
        row = db.execute("SELECT payload FROM api_cache WHERE namespace='fund-task-status' AND cache_key='latest'").fetchone()
    # Restored operational state is never resumed or executed.
    if row:
        try:
            previous = json.loads(row[0])
            if isinstance(previous, dict) and isinstance(previous.get('rows'), list):
                # Only restore operational labels for current, server-owned listings.
                labels = {tuple(r.get(k) for k in ('symbol', 'exchange', 'currency')): r
                          for r in previous['rows'] if isinstance(r, dict)}
                rows = candidates(store)
                valid = ('success', 'partial', 'waiting', 'skipped', 'unsupported', 'error', 'cancelled', 'interrupted', 'closed')
                for item in rows:
                    old = labels.get(tuple(item[k] for k in ('symbol', 'exchange', 'currency')), {})
                    status_label = old.get('status')
                    item['status'] = status_label if status_label in valid else 'interrupted' if status_label in ('queued', 'running') else 'ready'
                    if item['status'] == 'interrupted':
                        item['message'] = 'Taak onderbroken door een herstart. Start opnieuw om verder te gaan.'
                phase = 'interrupted' if previous.get('running') else previous.get('phase')
                return dict(running=False, phase=phase if phase in ('complete', 'cancelled', 'interrupted') else 'ready',
                            started_at='', finished_at='', rows=rows)
        except (ValueError, TypeError):
            pass
    return dict(running=False, phase='ready', started_at='', finished_at='', rows=candidates(store))


def start(store, cache, mode='all'):
    if mode not in ('all', 'missing', 'failed'):
        raise ValueError('Kies een geldige ETF-taak.')
    with _lock:
        existing = _jobs.get(key(store))
        if existing and existing['state']['running']:
            return copy.deepcopy(existing['state'])
        before = status(store)
        failed = {tuple(r.get(k) for k in ('symbol', 'exchange', 'currency')) for r in before['rows']
                  if r.get('status') in ('error', 'unsupported', 'interrupted', 'cancelled')}
        rows = candidates(store)
        if len(rows) > 1000:
            raise ValueError('Deze taak ondersteunt maximaal 1.000 ETF-noteringen.')
        for row in rows:
            selected = mode == 'all' or mode == 'missing' and (not row['count'] or row['stale']) or mode == 'failed' and tuple(row[k] for k in ('symbol', 'exchange', 'currency')) in failed
            row['status'] = 'queued' if selected else 'skipped'
        state = dict(running=True, phase='running', started_at=stamp(), finished_at='', rows=rows)
        job = dict(state=state, cancel=threading.Event())
        _jobs[key(store)] = job
        persist(store, state)
        threading.Thread(target=run, args=(store, cache, job), daemon=True, name='etf-holdings-task').start()
        return copy.deepcopy(state)


def cancel(store):
    with _lock:
        job = _jobs.get(key(store))
        if job and job['state']['running']:
            job['cancel'].set()
            job['state']['phase'] = 'stopping'
            persist(store, job['state'])
    return status(store)


def update(store, job, row, **values):
    with _lock:
        row.update(values)
        persist(store, job['state'])


def run(store, cache, job):
    failed = False
    try:
        for row in job['state']['rows']:
            if row['status'] != 'queued':
                continue
            if job['cancel'].is_set():
                update(store, job, row, status='cancelled', message='Overgeslagen na stoppen.')
                continue
            update(store, job, row, status='running', message='Gratis fondsbron zoeken en ophalen…')
            listing = tuple(row[k] for k in ('symbol', 'exchange', 'currency'))
            try:
                # Never trust a ticker passed by the client or a restored queue.
                with store.read() as db:
                    if not db.execute('SELECT 1 FROM purchases WHERE symbol=? AND exchange=? AND currency=?', listing).fetchone():
                        update(store, job, row, status='skipped', message='ETF staat niet meer in de portefeuille.')
                        continue
                url = row['source_url']
                if not url:
                    match = discover(store, row)
                    url = match['url']
                    update(store, job, row, source_url=url, issuer=match['issuer'], isin=match['isin'])
                if job['cancel'].is_set():
                    update(store, job, row, status='cancelled', message='Overgeslagen na stoppen.')
                    continue
                old = saved(store, listing)
                result = refresh(store, listing, url=url)
                waiting = old and result['fetched_at'] == old['fetched_at']
                incomplete = any(not h['sector'] or not h['country'] for h in result['holdings'])
                message = ('Bronwachttijd actief; opgeslagen gegevens behouden.' if waiting else
                           'Samenstelling opgehaald; sommige sectoren of landen ontbreken.' if incomplete else 'Samenstelling opgehaald.')
                update(store, job, row, status='waiting' if waiting else 'partial' if incomplete else 'success',
                       message=message, as_of=result['as_of'], count=len(result['holdings']), stale=result['stale'], source_url=result['source_url'])
                cache.invalidate()
            except Exception as error:
                if isinstance(error, FundSourceUnavailable):
                    update(store, job, row, status=error.task_status, message=str(error))
                    continue
                from diagnostics import record
                reference = record(store, 'WARNING', 'market', 'fund_task_failed', 'ETF-taak kon geen nieuwe samenstelling ophalen.',
                                   {'symbol': listing[0], 'error_type': type(error).__name__})
                unsupported = isinstance(error, ValueError) and str(error) in ('Geen eenduidige gratis fondsbron gevonden.', 'Meerdere fondsen gevonden. Controleer de ISIN-koppeling.')
                update(store, job, row, status='unsupported' if unsupported else 'error',
                       message=str(error) if unsupported else 'Ophalen mislukt; bestaande gegevens behouden.', log_id=reference)
            # Cancellation wakes the wait immediately; no bursts at an issuer.
            job['cancel'].wait(1)
    except Exception as error:
        failed = True
        from diagnostics import record
        record(store, 'ERROR', 'market', 'fund_queue_failed', 'ETF-taak is onderbroken.', {'error_type': type(error).__name__})
        for row in job['state']['rows']:
            if row['status'] in ('queued', 'running'):
                row.update(status='interrupted', message='Taak onderbroken door een herstart. Start opnieuw om verder te gaan.')
    finally:
        with _lock:
            job['state'].update(running=False, phase='interrupted' if failed else 'cancelled' if job['cancel'].is_set() else 'complete', finished_at=stamp())
            persist(store, job['state'])
