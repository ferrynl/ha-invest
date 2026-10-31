"""Trade Republic transaction export; explicit types, source IDs and source prices.

Format reference: https://github.com/aritzmmartinez/libtraderepublic (SCHEMA.md).
No login API, price reconstruction or inferred corporate actions.
"""
import csv
import io
import hashlib
import json
import re
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from .trading212 import number
from forex import code as currency_code

REQUIRED={'date','datetime','category','type','name','symbol','shares','price','amount','currency','transaction_id','asset_class'}
CASH_ONLY={'CARD_TRANSACTION','CARD_TRANSACTION_INTERNATIONAL','TRANSFER_INSTANT_INBOUND',
           'TRANSFER_INSTANT_OUTBOUND','TRANSFER_DIRECT_DEBIT_INBOUND','INTEREST_PAYMENT','BENEFITS_SAVEBACK'}
# Netflix issuer release, 2025-10-30: nine additional shares per share;
# split-adjusted trading began 2025-11-17. Do not infer other split ratios.
# ir.netflix.net/investor-news-and-events/financial-releases/press-release-details/
# 2025/Netflix-Announces-Ten-For-One-Stock-Split/default.aspx
SPLITS={('US64110L1061','2025-11-17'):Decimal('10')}
SPLIT_CURRENCY_ERROR='Splitsing zonder prijsvaluta: importeer de aankoophistorie of herstel eerst de bestaande ISIN-koppeling.'

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
            if not decision and (category,action)==('DELIVERY','MIGRATION'):kind='MIGRATION'
            if not decision and (category,action)==('CORPORATE_ACTION','SPLIT'):kind='SPLIT'
            # Pre-payment is a cash reservation, not the eventual fund purchase.
            # Only accept the observed shape; a changed shape still needs review.
            if not decision and category=='CASH' and action=='PRIVATE_MARKET_BUY' and raw['asset_class']=='PRIVATE_FUND' and not raw['shares'] and not raw['price']:
                kind='SKIP'
            if not decision and category=='CASH' and action=='CUSTOMER_INPAYMENT' and not raw['symbol'] and not raw['shares'] and not raw['price']:
                kind='SKIP'
            if not decision and category=='CASH' and action=='BONUS' and not raw['symbol'] and not raw['shares'] and not raw['price']:
                kind='SKIP'
            if not decision and category=='CASH' and action in ('FEE','TAX'):kind='CHARGE'
            row=dict(line=index,kind=kind,ticker=raw['symbol'],name=raw['name'],raw={**raw,'ISIN':raw['symbol']},
                     digest=digest,external_id='id:'+raw['transaction_id'] if raw['transaction_id'] else 'raw:'+digest,error=None)
            try:
                if malformed:raise ValueError('CSV-regel bevat een onjuist aantal kolommen.')
                if not raw['transaction_id']:raise ValueError('Transactie-ID ontbreekt; deze regel kan niet veilig worden ontdubbeld.')
                stamp=datetime.fromisoformat(raw['datetime'].replace('Z','+00:00'))
                stamp=stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
                day=date.fromisoformat(raw['date'])
                # Broker booking date and UTC execution time can straddle midnight.
                # Preserve the explicit source date for the ledger and FX.
                if abs((stamp.date()-day).days)>1:raise ValueError('Boekdatum en transactietijd verschillen meer dan één dag; controleer de bronregel.')
                if day>date.today() or stamp.date()>date.today():raise ValueError('Toekomstige transactie.')
                row.update(day=day.isoformat(),trade_time=stamp.isoformat())
                if stamp.date()!=day:row['notice']='Boekdatum uit de export behouden; UTC-transactietijd valt op een andere dag.'
                if not kind:raise ValueError('Dit transactietype vereist beoordeling: '+category+' / '+action+'.')
                try:row['currency']=currency_code(raw['currency']) if raw['currency'] or kind!='SPLIT' else ''
                except ValueError:raise ValueError('Valuta ontbreekt of is ongeldig in de bronkolom currency voor '+category+' / '+action+'; er wordt geen valuta afgeleid uit de ISIN.') from None
                if kind=='SKIP':
                    if action=='PRIVATE_MARKET_BUY':row['notice']='Vooruitbetaling overgeslagen; de latere fondsuitvoering boekt de aankoop.'
                    if action=='CUSTOMER_INPAYMENT':row['notice']='Storting op de geldrekening overgeslagen; geen aankoop of dividend.'
                    if action=='BONUS':row['notice']='Geldbonus op de geldrekening overgeslagen; geen dividend of aandelenboeking.'
                    rows.append(row);continue
                if kind=='CHARGE':
                    rows.append(row);continue
                if raw['asset_class'].lower() not in ('stock','fund','etf','equity','private_fund'):
                    raise ValueError('Alleen aandelen en fondsen worden ondersteund; controleer de beleggingscategorie.')
                if raw['asset_class'].lower()=='private_fund':row['notice']='Niet-beursgenoteerd fonds: stel de actuele fondskoers handmatig in bij Aandelen.'
                if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]',row['ticker']):raise ValueError('Geldige ISIN ontbreekt.')
                if kind=='SPLIT':
                    ratio=SPLITS.get((row['ticker'],row['day']))
                    if not ratio:raise ValueError('Splitsingsverhouding niet bevestigd voor deze ISIN en datum; deze regel blijft ter beoordeling.')
                    quantity=Decimal(number(raw['shares']))
                    if quantity<=0:raise ValueError('Aantal bij splitsing ontbreekt of is ongeldig.')
                    row.update(quantity=str(quantity),split_ratio=str(ratio),notice='10-op-1-splitsing: aantal wordt gecontroleerd tegen het voorafgaande bezit; kostprijs blijft behouden.')
                elif kind in ('DIVIDEND','CAPITAL_RETURN'):
                    amount=Decimal(number(raw['amount']))
                    if amount<=0:raise ValueError('Negatief of ontbrekend netto dividend vereist handmatige beoordeling.')
                    row['amount']=str(amount)
                else:
                    quantity,price=Decimal(number(raw['shares'])),Decimal(number(raw['price']))
                    if not quantity or price<=0 or (kind=='BUY' and quantity<0):raise ValueError('Aantal of prijs ontbreekt of is ongeldig; er wordt geen kostprijs geschat.')
                    row.update(quantity=str(quantity if kind=='MIGRATION' else abs(quantity)),price=str(price))
            except (ValueError,KeyError) as error:row['error']=str(error)
            rows.append(row)
    except csv.Error as error:raise ValueError('Trade Republic CSV is ongeldig; download het oorspronkelijke bestand opnieuw.') from error
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    neutralize_migrations(rows)
    for row in rows:
        if row['kind']!='SPLIT' or row.get('error') or row['currency']:continue
        currencies={r['currency'] for r in rows if r['ticker']==row['ticker'] and r['kind'] in ('BUY','SELL') and r.get('currency') and not r.get('error')}
        if len(currencies)==1:
            row['currency']=next(iter(currencies));row['currency_origin']='source_trades'
        else:row.update(needs_split_currency=True,error=SPLIT_CURRENCY_ERROR)
    from .charge_fields import attach
    return attach(rows,'traderepublic')

def prepare_rows(store,account_id,rows):
    """A split moves units, not money; reuse a unique saved listing if needed."""
    from .registry import lookup
    for row in rows:
        if not row.get('needs_split_currency') or row.get('error')!=SPLIT_CURRENCY_ERROR:continue
        mapping=lookup(store,account_id,'traderepublic',row)
        if mapping:
            row.update(currency=mapping['currency'],mapping=mapping,currency_origin='saved_listing',error=None)
            row.pop('needs_split_currency',None)

def neutralize_migrations(rows):
    """Only the observed, tightly paired internal out/in migration is neutral.

    Keep incomplete transfers, different accounts, altered bases and duplicate IDs
    for review. Source IDs and raw rows are retained, never turned into trades.
    """
    groups={}
    for row in rows:
        if row['kind']!='MIGRATION' or row.get('error'):continue
        raw=row['raw']
        key=(row['ticker'],row['day'],row['currency'],raw.get('account_type',''),raw['asset_class'],abs(Decimal(row['quantity'])),Decimal(row['price']))
        groups.setdefault(key,[]).append(row)
    for group in groups.values():
        neutral=(len(group)==2 and group[0]['external_id']!=group[1]['external_id']
                 and sum((Decimal(row['quantity']) for row in group),Decimal(0))==0
                 and abs(datetime.fromisoformat(group[0]['trade_time'])-datetime.fromisoformat(group[1]['trade_time']))<=timedelta(seconds=1))
        for row in group:
            if neutral:row.update(kind='SKIP',notice='Interne migratie: gelijke uit- en inboeking overgeslagen; bezit en kostprijs blijven gelijk.')
            else:row['error']='Migratie zonder eenduidige gelijke tegenboeking binnen één seconde in dit bestand. Er wordt geen aankoop, verkoop of kostprijs geschat.'
