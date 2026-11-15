
"""Fetch one account's dated transaction history using a short-lived bearer token."""
import json
from datetime import date
from time import monotonic
from urllib.parse import urlencode
from urllib.request import Request,build_opener

from ..broker_rows import MAX_BYTES,MAX_ROWS
from ..broker_http import NoRedirect

BASE = {'live':'https://gateway.saxobank.com/openapi','sim':'https://gateway.saxobank.com/sim/openapi'}


def transactions(token,account,start,end,environment):
    first,last = date.fromisoformat(start),date.fromisoformat(end)
    if first > last or last > date.today() or (last-first).days > 366:
        raise ValueError('Kies een periode van maximaal één jaar die niet in de toekomst eindigt.')
    if not token or not account or len(token)>8192 or len(account)>512 or any(not c.isascii() or not 33<=ord(c)<=126 for c in token):
        raise ValueError('Vul een geldig Saxo-token en AccountKey in.')
    if environment not in BASE:
        raise ValueError('Kies Saxo LIVE of SIM.')
    records = []
    size = 0
    opener = build_opener(NoRedirect())
    next_url = BASE[environment]+'/hist/v1/transactions?'+urlencode({
        'AccountKeys':account,'FromDate':first.isoformat(),'ToDate':last.isoformat(),'$top':100})
    prefix = BASE[environment]+'/hist/v1/transactions?'
    visited = set()
    deadline = monotonic()+45
    while next_url:
        remaining = deadline-monotonic()
        if remaining <= 0 or not next_url.startswith(prefix) or next_url in visited or len(visited)>=20:
            raise ValueError('Saxo-paginering is ongeldig of het rapport is te groot. Kies een kortere periode.')
        visited.add(next_url)
        try:
            with opener.open(Request(next_url,headers={'Authorization':'Bearer '+token}),timeout=min(8,remaining)) as response:
                body = response.read(MAX_BYTES-size+1)
            size += len(body)
            if size > MAX_BYTES:
                raise ValueError('Saxo-rapport is groter dan 5 MB. Kies een kortere periode.')
            payload = json.loads(body,parse_float=str)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('Saxo OpenAPI is niet bereikbaar of heeft het verzoek geweigerd.') from error
        if not isinstance(payload,dict) or not isinstance(payload.get('Data'),list):
            raise ValueError('Saxo gaf geen geldig transactierapport terug.')
        records.extend(payload['Data'])
        if len(records)>MAX_ROWS:
            raise ValueError('Maximaal 10.000 transacties per import.')
        next_url = payload.get('__next')
        if next_url is not None and not isinstance(next_url,str):
            raise ValueError('Saxo gaf een ongeldige volgende pagina terug.')
    if not records:
        raise ValueError('Saxo gaf geen transacties terug voor deze periode.')
    accounts = {tx.get('AccountId') for tx in records if isinstance(tx,dict) and isinstance(tx.get('AccountId'),str) and tx['AccountId']}
    if len(accounts) != 1 or any(not isinstance(tx,dict) or not isinstance(tx.get('AccountId'),str) or tx['AccountId'] not in accounts for tx in records):
        raise ValueError('Het Saxo-rapport moet transacties van precies één rekening bevatten.')
    return records
