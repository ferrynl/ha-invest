import json
import logging
import os
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer
from storage import Store
from provider import fetch_quote, search_stocks, fetch_history
from security import Auth
from cache import StateCache
from web import make_handler
from datetime import datetime, timezone
from diagnostics import record
from profiles import enrich_categories
from forex import snapshot as fx_snapshot,currencies as fx_currencies

ROOT = Path(__file__).parent
store = Store(os.environ.get('DATA_DIR', './data'))
auth = Auth(store)
state_cache = StateCache(30)
options_path = store.root / 'options.json'
options = json.loads(options_path.read_text()) if options_path.exists() else {}
interval = max(5, int(options.get('refresh_minutes', 15))) * 60
refresh_requested = threading.Event()
status = {'message': 'Yahoo-koersen worden opgehaald; mogelijk vertraagd.', 'last_attempt': None}
refresh_lock = threading.Lock()

def refresh():
    if not refresh_lock.acquire(blocking=False):
        return
    try:
        errors = 0
        snapshot = store.state()
        history_errors = 0
        seen=set()
        for p in snapshot['positions']:
            instrument=(p['symbol'],p['exchange'],p['currency'])
            if instrument in seen:continue
            seen.add(instrument)
            if p['exchange']=='PRIVATE':
                if enrich_categories(store,instrument):state_cache.invalidate()
                continue
            if p.get('quote',{} ) and p['quote'].get('manual'):
                if enrich_categories(store,instrument):state_cache.invalidate()
                continue
            start = min(l['purchased_on'] for l in snapshot['purchases'] if all(l[k] == p[k] for k in ('symbol', 'exchange', 'currency')))
            try:
                if store.history_needed(p['symbol'], p['exchange'], p['currency'], start):
                    requested=store.history_start(p['symbol'],p['exchange'],p['currency'],start)
                    rows = fetch_history(p['symbol'], p['exchange'], p['currency'], requested,store=store)
                    store.save_history(p['symbol'], p['exchange'], p['currency'], start, rows)
            except Exception as error:
                record(store,'WARNING','market','history_failed','Koershistorie ophalen mislukt.',{'symbol':p['symbol'],'exchange':p['exchange'],'currency':p['currency'],'error_type':type(error).__name__,'code':getattr(error,'code','provider_failed')})
                history_errors += 1
            try:
                fresh = p['quote'] and (datetime.now(timezone.utc)-datetime.fromisoformat(p['quote']['fetched_at'])).total_seconds()<interval
                if not fresh:
                    price, stamp = fetch_quote('', p['symbol'], p['exchange'], p['currency'],store=store,ttl=interval)
                    store.quote(p['symbol'], p['exchange'], p['currency'], price, stamp, 'Yahoo Finance (mogelijk vertraagd)')
            except Exception as error:
                record(store,'WARNING','market','quote_failed','Actuele koers ophalen mislukt.',{'symbol':p['symbol'],'exchange':p['exchange'],'currency':p['currency'],'error_type':type(error).__name__,'code':getattr(error,'code','provider_failed')})
                errors += 1
            # Profile lookup runs once per listing, including existing holdings.
            if enrich_categories(store,instrument):state_cache.invalidate()
            # Space requests to avoid bursts; plan limits still apply.
            time.sleep(1)
        from storage import now
        status.update(message=f'{errors} koersaanvragen mislukt. Vorige koersen blijven zichtbaar met hun oorspronkelijke tijd.' if errors else 'Yahoo-koersen bijgewerkt; mogelijk vertraagd. Buiten beurstijden zie je de laatst beschikbare koers.', last_attempt=now())
        if history_errors:
            status['message'] += f' Historie van {history_errors} aandeel/aandelen kon niet worden opgehaald; volgt bij de volgende controle.'
        state_cache.invalidate()
    finally:
        refresh_lock.release()

def background():
    last_backup = 0
    last_fx=0
    while True:
        try:
            if time.time() - last_backup >= 86400:
                store.backup()
                last_backup = time.time()
            if time.time()-last_fx>=21600:
                try:
                    fx_currencies(store);fx_snapshot(store,datetime.now(timezone.utc).date().isoformat())
                    record(store,'INFO','fx','daily_rates','Dagreferentiekoersen opgeslagen.')
                except ValueError as error:record(store,'WARNING','fx','daily_rates_failed',str(error))
                last_fx=time.time()
            refresh()
        except Exception as error:
            record(store,'ERROR','system','background_failed','Achtergrondtaak mislukt.',{'error_type':type(error).__name__})
            logging.exception('Achtergrondtaak mislukt')
        refresh_requested.wait(interval)
        refresh_requested.clear()

Handler = make_handler(store, auth, state_cache, status, interval, refresh_lock, refresh_requested)

if __name__ == '__main__':
    threading.Thread(target=background, daemon=True).start()
    # No published host port in HA; access is through authenticated ingress only.
    ThreadingHTTPServer((os.environ.get('BIND', '0.0.0.0'), int(os.environ.get('PORT', 8099))), Handler).serve_forever()
