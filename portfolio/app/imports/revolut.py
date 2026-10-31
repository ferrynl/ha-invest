"""Revolut investment CSV adapter. Unknown actions require explicit review.

Format examples: github.com/GeiserX/DeclaRenta/issues/56 and
github.com/JakaCikac/revolut-edavki (investment transactions).
"""
import csv
import io
import hashlib
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from forex import code


# Issuer: newsroom.servicenow.com/press-releases/details/2025/
# ServiceNow-Shareholders-Approve-5-for-1-Stock-Split/default.aspx
SPLITS={('NOW','USD','2025-12-18'):Decimal('5')}
MERGER_REVIEW='Fusie: controleer de gekoppelde geld- en aandelenregels en de oorspronkelijke kostprijs. Deze regel blijft apart bewaard.'
TAX_REVIEW='Dividendbelastingcorrectie: controleer de bijbehorende dividendboeking. Alleen een exact tegengesteld correctiepaar wordt automatisch overgeslagen.'
SPLIT_REVIEW='Splitsing: de verhouding is niet bevestigd voor deze ticker, valuta en datum. Deze regel blijft apart bewaard.'

def parse_csv(text, decision=None):
    if len(text)>5*1024*1024:raise ValueError('CSV is te groot (maximaal 5 MB).')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
    fields=reader.fieldnames or []
    modern='Reference' in fields
    required={'Date','Type','Quantity','ISIN','CCY','Price/share','Net Amt.'} if modern else {'Date','Type','Quantity','Price per share','Total Amount','Currency'}
    if len(fields)!=len(set(fields)) or not required.issubset(fields) or not ({'Ticker','Symbol'} & set(fields)):
        raise ValueError('Revolut CSV: gebruik de Engelstalige transactie-export van de beleggingsrekening met Date, Ticker of Symbol, Type, Quantity, prijs, bedrag en valuta.')
    rows=[]
    try:
        for index,source in enumerate(reader,2):
            if index>10001:raise ValueError('Maximaal 10.000 CSV-regels per import.')
            malformed=None in source or any(v is None for v in source.values())
            raw={k:str(v or '').strip() for k,v in source.items() if k is not None}
            digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
            action=raw['Type'].upper()
            action={'BUY - MARKET':'BUY','BUY - LIMIT':'BUY','SELL - MARKET':'SELL','SELL - LIMIT':'SELL'}.get(action,action)
            kind=decision or {'BUY':'BUY','SELL':'SELL','DIVIDEND':'DIVIDEND','CASH TOP-UP':'SKIP','CASH WITHDRAWAL':'SKIP','CUSTODY FEE':'SKIP','RETURN OF CAPITAL':'CAPITAL_RETURN','STOCK SPLIT':'SPLIT'}.get(action)
            row=dict(line=index,kind=kind,ticker=raw.get('Ticker') or raw.get('Symbol',''),name=raw.get('Ticker') or raw.get('Symbol',''),raw=raw,digest=digest,external_id='id:'+raw['Reference'] if raw.get('Reference') else 'raw:'+digest,error=None)
            try:
                if malformed:raise ValueError('CSV-regel bevat een onjuist aantal kolommen.')
                try:stamp=datetime.fromisoformat(raw['Date'].replace('Z','+00:00'))
                except ValueError:stamp=datetime.strptime(raw['Date'],'%d/%m/%Y')
                if stamp.date()>date.today():raise ValueError('Toekomstige transactie.')
                row.update(day=stamp.date().isoformat(),trade_time=stamp.isoformat(),currency=code(raw['CCY' if modern else 'Currency']))
                if not decision and action.startswith('MERGER - '):raise ValueError(MERGER_REVIEW)
                if not decision and action=='DIVIDEND TAX (CORRECTION)':raise ValueError(TAX_REVIEW)
                if not kind:raise ValueError('Dit transactietype vereist beoordeling: '+action+'.')
                if action=='CUSTODY FEE' and not decision:row['notice']='Bewaarloon overgeslagen; kosten worden niet in de winst verwerkt.'
                if kind!='SKIP' and not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',row['ticker']):raise ValueError('Geldige ticker ontbreekt.')
                def amount(field):
                    value=raw[field]
                    value=re.sub(r'^'+re.escape(row['currency'])+r'\s+','',value)
                    result=Decimal(value.replace(',',''))
                    if not result.is_finite() or result<=0:raise ValueError('Aantal of bedrag ontbreekt of is ongeldig.')
                    return str(result)
                if kind=='SPLIT':
                    ratio=SPLITS.get((row['ticker'],row['currency'],row['day']))
                    if not ratio:raise ValueError(SPLIT_REVIEW)
                    row.update(quantity=amount('Quantity'),split_ratio=str(ratio))
                elif kind in ('DIVIDEND','CAPITAL_RETURN'):
                    row['amount']=amount('Net Amt.' if modern else 'Total Amount')
                    if not modern and raw.get('Taxes'):
                        tax=Decimal(re.sub(r'^'+re.escape(row['currency'])+r'\s+','',raw['Taxes']).replace(',',''))
                        net=Decimal(row['amount'])-tax
                        if not tax.is_finite() or tax<0 or net<=0:raise ValueError('Aantal of bedrag ontbreekt of is ongeldig.')
                        row['amount']=str(net)
                elif kind in ('BUY','SELL'):row.update(quantity=amount('Quantity'),price=amount('Price/share' if modern else 'Price per share'))
            except (ValueError,KeyError,InvalidOperation) as error:
                if isinstance(error,ValueError) and str(error).startswith(('Dit transactietype','Geldige ticker','Toekomstige transactie','CSV-regel','Aantal of bedrag','Fusie:','Dividendbelastingcorrectie:','Splitsing:')):
                    row['error']=str(error)
                else:row['error']='Revolut: controleer transactietype, datum, ticker, valuta en positieve bronbedragen.'
            rows.append(row)
    except csv.Error as error:raise ValueError('Revolut CSV is ongeldig.') from error
    # Correction pairs reverse each other without changing net dividend. Never
    # discard standalone tax adjustments or pair different securities/currencies.
    if not decision:
        corrections={}
        for row in rows:
            if row['raw']['Type'].upper()!='DIVIDEND TAX (CORRECTION)' or row.get('error')!=TAX_REVIEW:continue
            if not row.get('day') or not row.get('currency') or not re.fullmatch(r'[A-Z0-9.^:/_-]{1,30}',row['ticker']):continue
            corrections.setdefault((row['ticker'],row['currency'],row['day']),[]).append(row)
        for group in corrections.values():
            if len(group)!=2:continue
            try:
                amounts=[Decimal(re.sub(r'^'+re.escape(r['currency'])+r'\s+','',r['raw']['Net Amt.' if modern else 'Total Amount']).replace(',','')) for r in group]
                if not all(a.is_finite() and a!=0 for a in amounts) or sum(amounts)!=0:continue
            except (InvalidOperation,ValueError):continue
            for row in group:row.update(kind='SKIP',error=None,notice='Tegengestelde dividendbelastingcorrecties heffen elkaar op; overgeslagen.')
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    return rows
