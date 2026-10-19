"""Trading 212 Invest/ISA English History CSV, parsed without guessing a listing."""
import csv
import io
import hashlib
import json
from decimal import Decimal,InvalidOperation
from datetime import datetime,date

def number(value):
    value=str(value or '').strip()
    try:
        parsed=Decimal(value)
        if not parsed.is_finite():raise ValueError('Ongeldig bedrag.')
        return format(parsed.normalize(),'f')
    except InvalidOperation as error:raise ValueError('Gebruik een Trading 212 CSV met punt als decimaalteken.') from error

def parse_csv(text):
    if len(text)>5*1024*1024:raise ValueError('CSV is te groot (maximaal 5 MB).')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames or not {'Action','Time','Ticker','Name'}.issubset(set(reader.fieldnames)):
        raise ValueError('Gebruik de Engelstalige Trading 212 History CSV (Action, Time, Ticker, Name).')
    rows=[]
    for index,source in enumerate(reader,2):
        if index>10001:raise ValueError('Maximaal 10.000 CSV-regels per import.')
        raw={str(k):str(v or '').strip() for k,v in source.items() if k is not None}
        action=raw.get('Action','').lower();kind=None;error=None
        if action.endswith('buy'):kind='BUY'
        elif action.endswith('sell'):kind='SELL'
        elif action.startswith('dividend') and 'return of capital' not in action:kind='DIVIDEND'
        elif action in ('deposit','withdrawal','currency conversion','interest on cash','lending interest','cashback','spending cashback'):
            kind='SKIP'
        else:error='Dit transactietype wordt nog niet ondersteund: '+raw.get('Action','onbekend')
        row=dict(line=index,kind=kind,ticker=raw.get('Ticker',''),name=raw.get('Name',''),raw=raw,error=error)
        if kind and kind!='SKIP':
            try:
                stamp=datetime.fromisoformat(raw['Time'].replace('Z','+00:00'))
                if stamp.date()>date.today():raise ValueError('Toekomstige transactie.')
                row.update(day=stamp.date().isoformat(),trade_time=stamp.isoformat())
                if not row['ticker']:raise ValueError('Ticker ontbreekt.')
                if kind=='DIVIDEND':
                    amount=Decimal(number(raw.get('Total')))
                    if amount<=0:raise ValueError('Netto dividend moet positief zijn.')
                    row.update(amount=str(amount),currency=raw.get('Currency (Total)','').upper())
                else:
                    quantity,price=Decimal(number(raw.get('No. of shares'))),Decimal(number(raw.get('Price / share')))
                    if quantity<=0 or price<=0:raise ValueError('Aantal of prijs ontbreekt.')
                    row.update(quantity=str(quantity),price=str(price),currency=raw.get('Currency (Price / share)','').upper())
                canonical={k:row.get(k) for k in ('kind','ticker','day','trade_time','quantity','price','amount','currency')}
                digest=hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
                row.update(digest=digest,external_id=('id:'+raw['ID']+':'+str(kind)) if raw.get('ID') else 'row:'+digest)
                if len(row['currency'])!=3:raise ValueError('Valutacode ontbreekt.')
            except (ValueError,KeyError) as exc:row['error']=str(exc)
        rows.append(row)
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    return rows
