import json
import logging
import os
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from storage import Store
from provider import fetch_quote, search_stocks, fetch_history

ROOT = Path(__file__).parent
store = Store(os.environ.get('DATA_DIR', './data'))
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
        for p in snapshot['positions']:
            start = min(l['purchased_on'] for l in snapshot['purchases'] if all(l[k] == p[k] for k in ('symbol', 'exchange', 'currency')))
            try:
                if store.history_needed(p['symbol'], p['exchange'], p['currency'], start):
                    rows = fetch_history(p['symbol'], p['exchange'], p['currency'], start)
                    store.save_history(p['symbol'], p['exchange'], p['currency'], start, rows)
            except Exception:
                history_errors += 1
            try:
                price, stamp = fetch_quote('', p['symbol'], p['exchange'], p['currency'])
                store.quote(p['symbol'], p['exchange'], p['currency'], price, stamp, 'Yahoo Finance (mogelijk vertraagd)')
            except Exception:
                errors += 1
            # Space requests to avoid bursts; plan limits still apply.
            time.sleep(1)
        from storage import now
        status.update(message=f'{errors} koersaanvragen mislukt. Vorige koersen blijven zichtbaar met hun oorspronkelijke tijd.' if errors else 'Yahoo-koersen bijgewerkt; mogelijk vertraagd. Buiten beurstijden zie je de laatst beschikbare koers.', last_attempt=now())
        if history_errors:
            status['message'] += f' Historie van {history_errors} aandeel/aandelen kon niet worden opgehaald; volgt bij de volgende controle.'
    finally:
        refresh_lock.release()

def background():
    last_backup = 0
    while True:
        try:
            if time.time() - last_backup >= 86400:
                store.backup()
                last_backup = time.time()
            refresh()
        except Exception:
            logging.exception('Achtergrondtaak mislukt')
        refresh_requested.wait(interval)
        refresh_requested.clear()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, content, code=200, kind='application/json', filename=None):
        if kind == 'application/json':
            content = json.dumps(content).encode()
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/search':
            query = parse_qs(urlsplit(self.path).query).get('q', [''])[0]
            if not 2 <= len(query.strip()) <= 80:
                return self.respond({'error': 'Typ minimaal twee en maximaal 80 tekens.'}, 400)
            try:
                return self.respond({'results': search_stocks(query)})
            except Exception:
                return self.respond({'error': 'Zoeken bij Yahoo lukt nu niet. Probeer het opnieuw.'}, 502)
        if path == '/api/state':
            return self.respond({**store.state(), 'status': status, 'refresh_minutes': interval // 60})
        if path == '/api/backup':
            backup = store.backup()
            return self.respond(backup.read_bytes(), kind='application/vnd.sqlite3', filename=backup.name)
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/chart.js': ('chart.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        if path in files:
            name, kind = files[path]
            return self.respond((ROOT / 'static' / name).read_bytes(), kind=kind)
        self.respond({'error': 'Niet gevonden'}, 404)

    def do_POST(self):
        # JSON-only, custom header and no CORS prevent cross-site form writes.
        if self.headers.get('X-Portfolio-Request') != '1' or self.headers.get('Content-Type') != 'application/json':
            return self.respond({'error': 'Ongeldige aanvraag'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('Aanvraag te groot of leeg.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Object verwacht.')
            if urlsplit(self.path).path != '/api/purchases':
                return self.respond({'error': 'Niet gevonden'}, 404)
            store.add(data)
            refresh_requested.set()
            self.respond({'ok': True}, 201)
        except (ValueError, KeyError, TypeError):
            self.respond({'error': 'Controleer alle velden, positieve getallen en aankoopdatum.'}, 400)

if __name__ == '__main__':
    threading.Thread(target=background, daemon=True).start()
    # No published host port in HA; access is through authenticated ingress only.
    ThreadingHTTPServer((os.environ.get('BIND', '0.0.0.0'), int(os.environ.get('PORT', 8099))), Handler).serve_forever()
