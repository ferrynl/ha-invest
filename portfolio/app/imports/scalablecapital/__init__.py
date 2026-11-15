
"""Scalable Capital PRIME+ transaction export."""
from ..broker_rows import action, csv_rows, decimal, field, movement


def map_row(raw,line,comma):
    kind = action(field(raw,'type'),buy=('buy','purchase','kauf','savings plan'),
                  sell=('sell','sale','verkauf'),dividend=('dividend','distribution','dividende','ausschüttung'),
                  skip=('deposit','withdrawal','interest','einzahlung','auszahlung','zinsen'))
    if field(raw,'status').casefold() not in ('executed','completed','booked','settled','ausgeführt','gebucht','abgeschlossen'):
        kind = None
    if field(raw,'assetType').casefold() not in ('','security') and kind != 'SKIP':
        kind = None
    currency = field(raw,'currency','transaction currency')
    price = field(raw,'price','price per share','share price')
    shares = field(raw,'shares','quantity')
    if not price and kind in ('BUY','SELL'):
        try:
            gross = abs(decimal(field(raw,'gross amount','gross_amount'),comma))
            units = abs(decimal(shares,comma))
            if units and gross:
                price = format(gross/units,'f')
        except ValueError:
            pass  # Keep the source row in review without a supported unit price.
    return movement(raw,line,action=kind,stamp=' '.join(filter(None,(field(raw,'date'),field(raw,'time')))),
        isin=field(raw,'isin'),name=field(raw,'security name','description'),currency=currency,quantity=shares,price=price,
        amount=field(raw,'net amount','net_amount'),source_id=field(raw,'reference'),comma=comma,
        costs=(('fees','COMMISSION',field(raw,'fee','fees'),currency),
               ('taxes','WITHHOLDING_TAX' if kind=='DIVIDEND' else 'TRANSACTION_TAX',field(raw,'tax','taxes'),currency)))


def parse(text):
    return csv_rows(text,[('date',),('status',),('reference',),('type',),('isin',),('currency','transaction currency')],map_row)


ADAPTER = dict(name='Scalable Capital',
    formats=['csv'],
    parse=parse,
    guide='Exporteer met PRIME+ de transacties als CSV. Gebruik de export met referentie, transactietype, status en valuta.',
    source='https://help.scalable.capital/en/account-management-f3197dc7/can-i-use-scalable-with-multibanking-programs-or-integra-86de3bbe')
