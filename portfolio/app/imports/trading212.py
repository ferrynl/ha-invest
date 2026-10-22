"""Trading 212 Invest/ISA English History CSV, parsed without guessing a listing."""
import csv
import io
import hashlib
import json
from decimal import Decimal,InvalidOperation
from datetime import datetime,date,timezone
from forex import code as currency_code

def history_reader(text):
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)):raise ValueError('Trading 212 CSV bevat dubbele kolomnamen.')
    if not {'Action','Ticker','Name'}.issubset(fields) or not {'Time','Time (UTC)'}.intersection(fields):
        raise ValueError('Gebruik de Engelstalige Trading 212 History CSV (Action, Time of Time (UTC), Ticker, Name).')
    return reader

def transaction_time(raw):
    legacy=raw.get('Time','');utc=raw.get('Time (UTC)','')
    if not legacy and not utc:raise ValueError('Transactietijd ontbreekt.')
    def parse(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
    def as_utc(value):return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if legacy and utc and as_utc(parse(legacy))!=as_utc(parse(utc)):raise ValueError('Time en Time (UTC) bevatten verschillende transactietijden.')
    if legacy:return parse(legacy)
    # Keep the historical naive representation for source-ID/content deduplication.
    return as_utc(parse(utc)).replace(tzinfo=None)

def number(value):
    value=str(value or '').strip()
    try:
        parsed=Decimal(value)
        if not parsed.is_finite():raise ValueError('Ongeldig bedrag.')
        return format(parsed.normalize(),'f')
    except InvalidOperation as error:raise ValueError('Gebruik een Trading 212 CSV met punt als decimaalteken.') from error

def unclassified_identity(raw):
    canonical={k:v for k,v in raw.items() if k not in ('Time','Time (UTC)')}
    try:canonical['time']=transaction_time(raw).isoformat()
    except ValueError:canonical['time']=raw.get('Time (UTC)',raw.get('Time',''))
    digest=hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
    return digest,('id:'+raw['ID']+':UNCLASSIFIED') if raw.get('ID') else 'raw:'+digest

def parse_csv(text):
    if len(text)>5*1024*1024:raise ValueError('CSV is te groot (maximaal 5 MB).')
    reader=history_reader(text)
    rows=[]
    for index,source in enumerate(reader,2):
        if index>10001:raise ValueError('Maximaal 10.000 CSV-regels per import.')
        raw={str(k):str(v or '').strip() for k,v in source.items() if k is not None}
        action=raw.get('Action','').lower();kind=None;error=None
        if action.endswith('buy'):kind='BUY'
        elif action.endswith('sell'):kind='SELL'
        elif action.startswith('dividend'):kind='CAPITAL_RETURN' if 'return of capital' in action else 'DIVIDEND'
        elif action in ('stock distribution','custom stock distribution'):kind='DISTRIBUTION'
        elif action=='stock split open':kind='SPLIT'
        elif action=='stock split close':kind='SPLIT_CLOSE'
        elif action in ('deposit','withdrawal','currency conversion','interest on cash','lending interest','cashback','spending cashback'):
            kind='SKIP'
        else:error='Dit transactietype wordt nog niet ondersteund: '+raw.get('Action','onbekend')
        row=dict(line=index,kind=kind,ticker=raw.get('Ticker',''),name=raw.get('Name',''),raw=raw,error=error)
        if kind and kind!='SKIP':
            try:
                stamp=transaction_time(raw)
                if stamp.date()>date.today():raise ValueError('Toekomstige transactie.')
                row.update(day=stamp.date().isoformat(),trade_time=stamp.isoformat())
                if not row['ticker']:raise ValueError('Ticker ontbreekt.')
                if kind=='DISTRIBUTION':
                    row.update(quantity=number(raw.get('No. of shares')),currency=currency_code(raw.get('Currency (Price / share)') or raw.get('Currency (Total)') or ''))
                    raise ValueError('Aandelenuitkering of omzetting: de oorspronkelijke aandelen en over te dragen kostprijs moeten worden gecontroleerd. Deze regel blijft apart bewaard; boek dit niet als dividend of gewone aankoop.')
                if kind in ('DIVIDEND','CAPITAL_RETURN'):
                    amount=Decimal(number(raw.get('Total')))
                    if amount<=0:raise ValueError('Netto dividend moet positief zijn.')
                    row.update(amount=str(amount),currency=currency_code(raw.get('Currency (Total)','')))
                elif kind in ('SPLIT','SPLIT_CLOSE'):
                    quantity=Decimal(number(raw.get('No. of shares')))
                    if quantity<=0:raise ValueError('Aantal na/voor splitsing moet positief zijn.')
                    row.update(quantity=str(quantity),currency=currency_code(raw.get('Currency (Price / share)','')))
                else:
                    row['currency']=currency_code(raw.get('Currency (Price / share)',''))
                    quantity,price=Decimal(number(raw.get('No. of shares'))),Decimal(number(raw.get('Price / share')))
                    if quantity<=0 or price<=0:raise ValueError('Aantal of prijs ontbreekt. Bij een fusie of intrekking kan de broker een nulprijs rapporteren; controleer de bijbehorende aandelenuitkering en kostprijs bij Te beoordelen.')
                    row.update(quantity=str(quantity),price=str(price),currency=currency_code(raw.get('Currency (Price / share)','')))
                canonical={k:row.get(k) for k in ('kind','ticker','day','trade_time','quantity','price','amount','currency')}
                digest=hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
                row.update(digest=digest,external_id=('id:'+raw['ID']+':'+str(kind)) if raw.get('ID') else 'row:'+digest)
                if len(row['currency'])!=3:raise ValueError('Valutacode ontbreekt.')
            except (ValueError,KeyError) as exc:row['error']=str(exc)
        if not row.get('external_id'):
            digest,external_id=unclassified_identity(raw)
            row.update(digest=digest,external_id=external_id)
        if kind in ('CAPITAL_RETURN','SPLIT','SPLIT_CLOSE'):
            digest,external_id=unclassified_identity(raw)
            row.update(digest=digest,external_id=external_id)
        rows.append(row)
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    split_groups={}
    for row in rows:
        if row['kind'] in ('SPLIT','SPLIT_CLOSE'):
            key=(row.get('trade_time'),row['ticker'],row['raw'].get('ISIN',''))
            split_groups.setdefault(key,[]).append(row)
    for group in split_groups.values():
        opens=[r for r in group if r['kind']=='SPLIT']
        closes=[r for r in group if r['kind']=='SPLIT_CLOSE']
        if len(opens)!=1 or len(closes)>1 or any(r.get('error') for r in group) or len({r.get('currency') for r in group})!=1:
            for row in group:row['error']=row.get('error') or 'Splitsing heeft geen geldige, eenduidige open/close-combinatie.'
            continue
        opens[0]['split_before']=closes[0]['quantity'] if closes else '0'
        if closes:closes[0]['kind']='SPLIT_INFO'
    return rows
