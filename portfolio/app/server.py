import json
import logging
import os
import threading
import time
from decimal import Decimal
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
state_cache = StateCache(30,store=store)
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
        state_cache.bind(store)
        errors = 0
        snapshot = state_cache.derived('state-compact:all',lambda:store.state(compact_view=True))
        history_errors = 0
        seen=set()
        for p in snapshot['positions']:
            instrument=(p['symbol'],p['exchange'],p['currency'])
            if p.get('invalid_position') or p.get('quote_paused'):continue
            if Decimal(p['quantity'])==0 and any(row.get('transfer_id') and row['side']=='SELL' and (row['symbol'],row['exchange'],row['currency'])==instrument for row in snapshot['purchases']):continue
            if instrument in seen:continue
            seen.add(instrument)
            if p['exchange']=='PRIVATE':
                from fund_quotes import supported,fetch_quote as fetch_fund_quote
                if supported(*instrument) and not (p.get('quote') or {}).get('manual'):
                    try:
                        quote=fetch_fund_quote(store)
                        if not p.get('quote') or p['quote']['quoted_at']!=quote['observed_at']:
                            store.quote(*instrument,quote['price'],quote['observed_at'],quote['source']);state_cache.invalidate()
                    except Exception as error:
                        record(store,'WARNING','market','quote_failed','Actuele koers ophalen mislukt.',{'symbol':p['symbol'],'exchange':p['exchange'],'currency':p['currency'],'error_type':type(error).__name__,'code':'fund_provider_failed'})
                        errors+=1
                if enrich_categories(store,instrument):state_cache.invalidate()
                continue
            if p.get('quote',{} ) and p['quote'].get('manual'):
                if enrich_categories(store,instrument):state_cache.invalidate()
                continue
            try:
                fresh = p['quote'] and (datetime.now(timezone.utc)-datetime.fromisoformat(p['quote']['fetched_at'])).total_seconds()<interval
                if not fresh:
                    price, stamp = fetch_quote('', p['symbol'], p['exchange'], p['currency'],store=store,ttl=interval)
                    store.quote(p['symbol'], p['exchange'], p['currency'], price, stamp, 'Yahoo Finance (mogelijk vertraagd)')
            except Exception as error:
                record(store,'WARNING','market','quote_failed','Actuele koers ophalen mislukt.',{'symbol':p['symbol'],'exchange':p['exchange'],'currency':p['currency'],'error_type':type(error).__name__,'code':getattr(error,'code','provider_failed')})
                errors += 1
            start = min(l['purchased_on'] for l in snapshot['purchases'] if all(l[k] == p[k] for k in ('symbol', 'exchange', 'currency')))
            try:
                if store.history_needed(p['symbol'], p['exchange'], p['currency'], start):
                    requested=store.history_start(p['symbol'],p['exchange'],p['currency'],start)
                    rows = fetch_history(p['symbol'], p['exchange'], p['currency'], requested,store=store)
                    store.save_history(p['symbol'], p['exchange'], p['currency'], start, rows)
            except Exception as error:
                record(store,'WARNING','market','history_failed','Koershistorie ophalen mislukt.',{'symbol':p['symbol'],'exchange':p['exchange'],'currency':p['currency'],'error_type':type(error).__name__,'code':getattr(error,'code','provider_failed')})
                history_errors += 1
            # Profile lookup runs once per listing, including existing holdings.
            if enrich_categories(store,instrument):state_cache.invalidate()
            from fund_holdings import background_refresh
            if background_refresh(store,instrument,p.get('categories',{}).get('asset_type')=='ETF'):state_cache.invalidate()
            # Space requests to avoid bursts; plan limits still apply.
            time.sleep(1)
        from storage import now
        status.update(message=f'{errors} koersaanvragen mislukt. Vorige koersen blijven zichtbaar met hun oorspronkelijke tijd.' if errors else 'Yahoo-koersen bijgewerkt; mogelijk vertraagd. Buiten beurstijden zie je de laatst beschikbare koers.', last_attempt=now())
        if history_errors:
            status['message'] += f' Historie van {history_errors} aandeel/aandelen kon niet worden opgehaald; volgt bij de volgende controle.'
        state_cache.invalidate()
    finally:
        refresh_lock.release()

def warm_dashboard():
    # Refresh FX and warm durable views outside the page request path.
    from home_euro import compact_overview,prepare_portfolio_rates
    snapshot=state_cache.derived('state-compact:all',lambda:store.state(compact_view=True))
    prepare_portfolio_rates(store,snapshot)
    snapshot=state_cache.derived('state-compact:all',lambda:store.state(compact_view=True))
    state_cache.derived('home-euro-compact:all',lambda:compact_overview(store,snapshot))

def demo_background():
    from demo import ensure_demo,refresh_demo_quotes
    while True:
        try:refresh_demo_quotes(ensure_demo(store.root/'demo'),ttl=300)
        except Exception as error:record(store,'WARNING','market','demo_refresh_failed','Demokoersen bijwerken mislukt.',{'error_type':type(error).__name__})
        time.sleep(300)

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
            warm_dashboard()
        except Exception as error:
            record(store,'ERROR','system','background_failed','Achtergrondtaak mislukt.',{'error_type':type(error).__name__})
            logging.exception('Achtergrondtaak mislukt')
        refresh_requested.wait(interval)
        refresh_requested.clear()

Handler = make_handler(store, auth, state_cache, status, interval, refresh_lock, refresh_requested, options)

class BoundedHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args):
        self.request_slots = threading.BoundedSemaphore(32)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.request_slots.release()


def start_export():
    from ha_export import valid_token,make_export_handler
    token=options.get('home_assistant_token','')
    if not valid_token(token):
        if token:logging.warning('Home Assistant-sensoren uitgeschakeld: gebruik een toegangssleutel van 32–128 letters, cijfers, streepjes of underscores.')
        return None
    try:
        http=BoundedHTTPServer((os.environ.get('BIND','0.0.0.0'),int(os.environ.get('HA_EXPORT_PORT',8100))),make_export_handler(store,state_cache,token))
    except OSError:
        logging.error('Home Assistant-sensorpoort kon niet worden geopend. Het dashboard blijft beschikbaar.')
        return None
    threading.Thread(target=http.serve_forever,daemon=True).start()
    return http

if __name__ == '__main__':
    start_export()
    threading.Thread(target=background, daemon=True).start()
    threading.Thread(target=demo_background, daemon=True).start()
    from feedback_client import background as feedback_background
    threading.Thread(target=feedback_background,args=(store,options),daemon=True).start()
    # The dashboard stays ingress-only; optional sensors use a separate read-only port.
    BoundedHTTPServer((os.environ.get('BIND', '0.0.0.0'), int(os.environ.get('PORT', 8099))), Handler).serve_forever()
