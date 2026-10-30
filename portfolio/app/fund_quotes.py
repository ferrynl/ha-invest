"""Read the public DivvyDiary Apollo quote, never execute page scripts."""
import json
import re
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from urllib.request import Request,urlopen
from persistent_cache import cached_json

ISIN='LU3170240538'
URL='https://divvydiary.com/en/apollo-private-markets-aligned-alternatives-a2-eur-acc-LU3170240538'
SOURCE='DivvyDiary · waargenomen koers; koersdatum niet vermeld'

def supported(symbol,exchange,currency):return (symbol,exchange,currency)==(ISIN,'PRIVATE','EUR')

def parse_quote(html,observed_at):
    for match in re.finditer(r'JSON\.parse\(("(?:\\.|[^"\\])*")\)',html):
        try:
            payload=json.loads(json.loads(match.group(1)))
            if not isinstance(payload,dict):continue
            for query in payload.get('queries',[]):
                key=query.get('queryKey',[])
                if len(key)!=2 or key[0]!='/symbols' or key[1].get('isin')!=ISIN or key[1].get('quoteCurrency')!='EUR':continue
                row=query['state']['data']
                if row.get('isin')!=ISIN or row.get('currency')!='EUR':continue
                price=Decimal(str(row['price']))
                if not price.is_finite() or price<=0 or price>Decimal('1e15'):continue
                # DivvyDiary does not publish a NAV/price date here. This is the
                # observation time, expressly identified as such in the source.
                return dict(price=str(price),observed_at=observed_at,source=SOURCE,price_date=None)
        except (ValueError,TypeError,KeyError,AttributeError,InvalidOperation):continue
    raise ValueError('De Apollo-koers kon niet met ISIN en valuta worden gecontroleerd. De vorige koers blijft behouden.')

def fetch_quote(store):
    def load():
        request=Request(URL,headers={'User-Agent':'HomeInvest/1.0','Accept':'text/html'})
        with urlopen(request,timeout=20) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('De koersbron gaf een te groot antwoord.')
        return parse_quote(raw.decode('utf-8'),datetime.now(timezone.utc).isoformat())
    return cached_json(store,'divvydiary-fund-v1',ISIN,6*3600,load)
