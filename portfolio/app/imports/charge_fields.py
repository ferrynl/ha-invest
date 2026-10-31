"""Read explicit broker fee/tax fields only; preserve the original currency."""
import re
from decimal import Decimal,InvalidOperation
from forex import code
from charges import number

REVOLUT_ACTIONS={'CUSTODY FEE':'CUSTODY','CUSTODY FEE REFUND':'CUSTODY','TRANSACTION FEE REFUND':'COMMISSION','TAX REFUND':'OTHER_TAX','VAT REFUND':'VAT','ADR FEE':'OTHER_FEE','REGULATORY FEE':'OTHER_FEE','TRANSACTION FEE':'COMMISSION','COMMISSION':'COMMISSION','FEE':'OTHER_FEE','FX FEE':'FX_FEE','VAT':'VAT','DIVIDEND TAX':'WITHHOLDING_TAX','DIVIDEND TAX (CORRECTION)':'WITHHOLDING_TAX','WITHHOLDING TAX':'WITHHOLDING_TAX','TRANSACTION TAX':'TRANSACTION_TAX','STAMP DUTY':'TRANSACTION_TAX','TAX':'OTHER_TAX'}

def source_number(value,currency):
    text=str(value).strip();match=re.match(r'^([A-Za-z]{3})\s+',text)
    if match:
        if code(match[1])!=currency:raise ValueError('Kostenbedrag en bronvaluta komen niet overeen.')
        text=text[match.end():]
    return number(text.replace(',',''))

def attach(rows,provider):
    for row in rows:
        if row.get('error'):continue
        raw=row['raw'];kind=row.get('kind');items=[]
        try:
            if kind=='CHARGE':
                field=('Net Amt.' if 'Reference' in raw else 'Total Amount') if provider=='revolut' else 'amount'
                amount=-source_number(raw[field],row['currency'])
                action=raw['Type'].upper() if provider=='revolut' else raw['type'].upper()
                category=REVOLUT_ACTIONS[action] if provider=='revolut' else 'OTHER_FEE' if action=='FEE' else 'OTHER_TAX'
                if amount<0 and 'CORRECTION' not in action and 'REFUND' not in action:raise ValueError('Positieve kostenbetaling vereist beoordeling: is dit een terugbetaling?')
                items=[dict(component='entry',category=category,amount=str(amount),currency=row['currency'],included_in_net=0,description=action)]
                row['amount']=str(amount)
            elif kind in ('BUY','SELL','DIVIDEND','CAPITAL_RETURN','SKIP'):
                if provider=='revolut':
                    specs=[('Fee','COMMISSION' if kind in ('BUY','SELL') else 'OTHER_FEE','Fee Currency'),('Commission','COMMISSION','Commission Currency'),('Fee (excl. VAT)','COMMISSION' if kind in ('BUY','SELL') else 'OTHER_FEE','Fee Currency'),('VAT','VAT','VAT Currency'),('Tax Amt.','WITHHOLDING_TAX' if kind=='DIVIDEND' else 'TRANSACTION_TAX' if kind in ('BUY','SELL') else 'OTHER_TAX','Tax Currency'),('Taxes','WITHHOLDING_TAX' if kind=='DIVIDEND' else 'TRANSACTION_TAX' if kind in ('BUY','SELL') else 'OTHER_TAX','Tax Currency')]
                elif provider=='trading212':
                    specs=[(key,category,'Currency ('+key+')') for key,category in [('Transaction fee','COMMISSION'),('Currency conversion fee','FX_FEE'),('Withholding tax','WITHHOLDING_TAX'),('Stamp duty reserve tax','TRANSACTION_TAX'),('Financial transaction tax','TRANSACTION_TAX'),('VAT','VAT')]]
                else:specs=[('fee','COMMISSION','fee_currency'),('tax','WITHHOLDING_TAX' if kind=='DIVIDEND' else 'TRANSACTION_TAX','tax_currency'),('vat','VAT','vat_currency')]
                for field,category,currency_field in specs:
                    if not str(raw.get(field,'')).strip():continue
                    prefix=re.match(r'^([A-Za-z]{3})\s+',str(raw[field]).strip())
                    currency=code(raw.get(currency_field) or (prefix[1] if prefix else row.get('currency','')))
                    amount=source_number(raw[field],currency)
                    if amount==0:continue
                    if amount<0:raise ValueError('Negatieve kostenkolom vereist beoordeling; gebruik een expliciete terugbetalingsboeking.')
                    if provider=='trading212' and not raw.get(currency_field) and not prefix:raise ValueError('Valuta voor kosten of belasting ontbreekt in de bronregel.')
                    if provider=='revolut' and kind=='DIVIDEND' and 'Reference' not in raw and category in ('COMMISSION','OTHER_FEE','VAT'):raise ValueError('Netto dividend na kosten is niet eenduidig in deze export; controleer de bronregel.')
                    items.append(dict(component=field,category=category,amount=str(amount),currency=currency,included_in_net=int(kind=='DIVIDEND'),description=field))
                if provider=='revolut':
                    commissions=[i for i in items if i['component'] in ('Fee','Commission','Fee (excl. VAT)')]
                    taxes=[i for i in items if i['component'] in ('Taxes','Tax Amt.')]
                    if len(commissions)>1 or len(taxes)>1:raise ValueError('Dubbele kosten- of belastingkolommen zijn niet eenduidig.')
                    vat=[i for i in items if i['category']=='VAT']
                    if commissions and vat and commissions[0]['component']!='Fee (excl. VAT)':
                        flag=raw.get('Fee includes VAT','').lower()
                        if flag not in ('0','1','true','false'):raise ValueError('Geef aan of de bronkosten inclusief btw zijn; btw wordt niet dubbel geboekt.')
                        if flag in ('1','true'):
                            if commissions[0]['currency']!=vat[0]['currency'] or number(commissions[0]['amount'])<number(vat[0]['amount']):raise ValueError('Kostenbedrag en btw sluiten niet op elkaar aan.')
                            commissions[0]['amount']=str(number(commissions[0]['amount'])-number(vat[0]['amount']))
            if kind=='SKIP' and items:
                if provider=='trading212':
                    from .trading212 import transaction_time
                    from datetime import date
                    stamp=transaction_time(raw)
                    if stamp.date()>date.today():raise ValueError('Toekomstige transactie.')
                    row.update(day=stamp.date().isoformat(),trade_time=stamp.isoformat(),currency=items[0]['currency'])
                row['kind']='CHARGE'
                if all(i['currency']==row['currency'] for i in items):row['amount']=str(sum((number(i['amount']) for i in items),Decimal(0)))
            row['charges']=items
        except (ValueError,KeyError,InvalidOperation) as error:row['error']=str(error)
    return rows
