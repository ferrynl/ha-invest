
"""DEGIRO Dutch and English transaction CSV with adjacent currency fields."""
from ..broker_rows import csv_rows, decimal, field, movement

DATE = ('Datum','Date')
QUANTITY = ('Aantal','Quantity')
PRICE = ('Koers','Price')
FEES = ('Transactiekosten','Transaction and/or third party fees','Transactiekosten en/of kosten van derden')
VALUE = ('Lokale waarde','Local value')


def parse(text):
    currencies = {}
    def configure(headers):
        for labels, target in ((PRICE,'Price Currency'),(FEES,'Fee Currency')):
            for label in labels:
                if label in headers:
                    index = headers.index(label)+1
                    if headers[index:index+1] == ['']:
                        headers[index] = target
                    currencies[label] = target

    def map_row(raw,line,comma):
        quantity = field(raw,*QUANTITY)
        try:
            shares = decimal(quantity,True)
            kind = 'BUY' if shares > 0 else 'SELL' if shares < 0 else None
        except ValueError:
            kind = None
        fee_currency = field(raw,'Fee Currency','Transaction fee currency')
        return movement(raw,line,action=kind,stamp=' '.join(filter(None,(field(raw,*DATE),field(raw,'Tijd','Time')))),
            isin=field(raw,'ISIN'),name=field(raw,'Product'),currency=field(raw,'Price Currency','Currency (Price)','Valuta (Koers)'),
            quantity=quantity,price=field(raw,*PRICE),comma=True,
            costs=(('commission','COMMISSION',field(raw,*FEES),fee_currency),))

    # Order IDs may group partial fills. Use full row identity to distinguish fills.
    return csv_rows(text,[DATE,('ISIN',),QUANTITY,PRICE,VALUE],map_row,finalize=configure)


ADAPTER = dict(name='DEGIRO',
    formats=['csv'],
    parse=parse,
    guide='Ga naar Inbox → Transacties, kies je periode en exporteer Transacties als CSV. Dit bestand bevat de aan- en verkopen.',
    source='https://moneywolf.io/nl/help/export-degiro/')
