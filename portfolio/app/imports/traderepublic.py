"""Trade Republic transaction export; explicit types, source IDs and source prices.

Format reference: https://github.com/aritzmmartinez/libtraderepublic (SCHEMA.md).
No login API, price reconstruction or inferred corporate actions.
"""
import csv
import io
import hashlib
import json
import re
from datetime import datetime, date, timezone
from decimal import Decimal
from .trading212 import number
from forex import code as currency_code

REQUIRED={'date','datetime','category','type','name','symbol','shares','price','amount','currency','transaction_id','asset_class'}
CASH_ONLY={'CARD_TRANSACTION','CARD_TRANSACTION_INTERNATIONAL','TRANSFER_INSTANT_INBOUND',
           'TRANSFER_INSTANT_OUTBOUND','TRANSFER_DIRECT_DEBIT_INBOUND','INTEREST_PAYMENT','BENEFITS_SAVEBACK'}

def parse_csv(text, decision=None):
    if len(text)>5*1024*1024:raise ValueError('CSV is te groot (maximaal 5 MB).')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)) or not REQUIRED.issubset(fields):
        raise ValueError('Gebruik de oorspronkelijke Trade Republic transactie-export CSV met date, datetime, category, type, symbol, shares, price, amount, currency en transaction_id. PDF en exports van externe tools worden niet ondersteund.')
    rows=[]
    try:
        for index,source in enumerate(reader,2):
            if index>10001:raise ValueError('Maximaal 10.000 CSV-regels per import.')
            malformed=None in source or any(value is None for value in source.values())
            raw={k:str(v or '').strip() for k,v in source.items() if k is not None}
            digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
            category,action=raw['category'],raw['type']
            kind=decision or (action if (category,action) in {('TRADING','BUY'),('TRADING','SELL'),('CASH','DIVIDEND')} else 'SKIP' if category=='CASH' and action in CASH_ONLY else None)
            row=dict(line=index,kind=kind,ticker=raw['symbol'],name=raw['name'],raw={**raw,'ISIN':raw['symbol']},
                     digest=digest,external_id='id:'+raw['transaction_id'] if raw['transaction_id'] else 'raw:'+digest,error=None)
            try:
                if malformed:raise ValueError('CSV-regel bevat een onjuist aantal kolommen.')
                if not raw['transaction_id']:raise ValueError('Transactie-ID ontbreekt; deze regel kan niet veilig worden ontdubbeld.')
                stamp=datetime.fromisoformat(raw['datetime'].replace('Z','+00:00'))
                stamp=stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
                day=date.fromisoformat(raw['date'])
                if stamp.date()!=day:raise ValueError('Datum wijkt af van de transactietijd in UTC.')
                if day>date.today():raise ValueError('Toekomstige transactie.')
                row.update(day=day.isoformat(),trade_time=stamp.isoformat(),currency=currency_code(raw['currency']))
                if not kind:raise ValueError('Dit transactietype vereist beoordeling: '+category+' / '+action+'.')
                if kind=='SKIP':rows.append(row);continue
                if raw['asset_class'].lower() not in ('stock','fund','etf','equity'):
                    raise ValueError('Alleen aandelen en fondsen worden ondersteund; controleer de beleggingscategorie.')
                if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]',row['ticker']):raise ValueError('Geldige ISIN ontbreekt.')
                if len(row['currency'])!=3:raise ValueError('Valutacode ontbreekt.')
                if kind in ('DIVIDEND','CAPITAL_RETURN'):
                    amount=Decimal(number(raw['amount']))
                    if amount<=0:raise ValueError('Negatief of ontbrekend netto dividend vereist handmatige beoordeling.')
                    row['amount']=str(amount)
                else:
                    quantity,price=Decimal(number(raw['shares'])),Decimal(number(raw['price']))
                    if not quantity or price<=0 or (kind=='BUY' and quantity<0):raise ValueError('Aantal of prijs ontbreekt of is ongeldig; er wordt geen kostprijs geschat.')
                    row.update(quantity=str(abs(quantity)),price=str(price))
            except (ValueError,KeyError) as error:row['error']=str(error)
            rows.append(row)
    except csv.Error as error:raise ValueError('Trade Republic CSV is ongeldig; download het oorspronkelijke bestand opnieuw.') from error
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    return rows
