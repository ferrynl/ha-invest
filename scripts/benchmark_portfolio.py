"""Measure Home Invest HTTP routes on an isolated fixture, without market I/O."""
import gzip
import http.client
import json
import sqlite3
import statistics
import sys
import tempfile
import threading
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))

from cache import StateCache
from security import Auth
from storage import Store
from web import make_handler

ACCOUNTS = 10
LISTINGS = 50
TRADES_PER_POSITION = 20
TRADE_COUNT = ACCOUNTS * LISTINGS * TRADES_PER_POSITION
DAYS = 180
HEADERS = {'Accept-Encoding': 'gzip', 'X-HomeInvest-Language': 'en',
           'X-Portfolio-Request': '1', 'Content-Type': 'application/json'}


def seed(store, first_day):
    with store.connect() as db:
        db.executemany('INSERT INTO broker_accounts VALUES(?,?,?,?)', (
            (account, f'Test {account}', 'Fixture', first_day.isoformat())
            for account in range(2, ACCOUNTS + 1)
        ))
        db.executemany(
            'INSERT INTO purchases(account_id,symbol,exchange,name,quantity,price,currency,purchased_on,created_at) '
            'VALUES(?,?,?,?,?,?,?,?,?)', (
                (account, f'FIX{listing}', 'AMSTERDAM', f'Fixture {listing}', '1', '100', 'EUR',
                 (first_day + timedelta(days=trade)).isoformat(), first_day.isoformat())
                for account in range(1, ACCOUNTS + 1)
                for listing in range(LISTINGS)
                for trade in range(TRADES_PER_POSITION)
            )
        )
        db.executemany('INSERT INTO daily_prices VALUES(?,?,?,?,?)', (
            (f'FIX{listing}', 'AMSTERDAM', 'EUR', (first_day + timedelta(days=day)).isoformat(), '110')
            for listing in range(LISTINGS)
            for day in range(DAYS)
        ))
    stamp = (first_day + timedelta(days=DAYS - 1)).isoformat() + 'T15:00:00+00:00'
    for listing in range(LISTINGS):
        store.quote(f'FIX{listing}', 'AMSTERDAM', 'EUR', '110', stamp, 'fixture')


def request(port, path, data=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=40)
    started = perf_counter()
    try:
        connection.request('POST' if data else 'GET', path, json.dumps(data) if data else None, HEADERS)
        response = connection.getresponse()
        body = response.read()
        elapsed = perf_counter() - started
        expected = 201 if data else 200
        if response.status != expected:
            raise RuntimeError(f'{path} returned {response.status}: {body[:500]!r}')
        if response.getheader('Content-Encoding') == 'gzip':
            body = gzip.decompress(body)
        return elapsed, json.loads(body)
    finally:
        connection.close()


def measure(port, store, first_day):
    state_path = '/api/state?compact=1'
    broker_path = state_path + '&account_id=2'
    euro_path = '/api/home/euro?compact=1'
    cold, state = request(port, state_path)
    broker_cold, broker = request(port, broker_path)
    if len(state['purchases']) != TRADE_COUNT or len(broker['purchases']) != TRADE_COUNT // ACCOUNTS:
        raise AssertionError('Incorrect transaction count')
    if not all(position['quote']['quoted_at'][:10] == (first_day + timedelta(days=DAYS - 1)).isoformat()
               for position in state['positions']):
        raise AssertionError('Historic quotes must preserve their source date')
    request(port, euro_path)
    warm = [sum(request(port, path)[0] for path in (state_path, euro_path)) for _ in range(7)]
    trade = dict(symbol='FIX0', exchange='AMSTERDAM', currency='EUR', name='Fixture 0',
                 account_id=2, quantity='1', price='105', purchased_on=date.today().isoformat())
    writes = [request(port, '/api/purchases', trade)[0] for _ in range(7)]
    updated = request(port, broker_path)[1]
    if len(updated['purchases']) != len(broker['purchases']) + len(writes):
        raise AssertionError('Warm snapshot did not reflect committed trades')
    with store.read() as db:
        journal = db.execute('PRAGMA journal_mode').fetchone()[0]
        busy_timeout = db.execute('PRAGMA busy_timeout').fetchone()[0]
    print(f'Python {sys.version.split()[0]}, SQLite {sqlite3.sqlite_version}, {journal}, busy_timeout {busy_timeout} ms')
    print(f'{TRADE_COUNT:,} trades, {ACCOUNTS} brokers, {LISTINGS} listings, {DAYS} daily prices per listing')
    print(f'Cold dashboard {cold:.3f} s; cold broker selection {broker_cold:.3f} s')
    print(f'Warm dashboard median {statistics.median(warm):.3f} s; max {max(warm):.3f} s (limit 2 s)')
    print(f'Purchase median {statistics.median(writes):.3f} s; max {max(writes):.3f} s (limit 1 s)')
    return max(warm) <= 2 and max(writes) <= 1


def main():
    first_day = date.today() - timedelta(days=DAYS + 10)
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        seed(store, first_day)
        handler = make_handler(store, Auth(store), StateCache(), {}, 900,
                               threading.Lock(), threading.Event(), enable_demo=False)
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                return measure(server.server_port, store, first_day)
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
