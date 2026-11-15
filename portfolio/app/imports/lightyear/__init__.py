
"""Lightyear transaction report CSV."""
from ..broker_rows import action, csv_rows, field, movement


def map_row(raw,line,comma):
    kind = action(raw['Type'],buy=('buy','purchase','trade buy'),sell=('sell','sale','trade sell'),
                  dividend=('dividend','cash dividend'),skip=('deposit','withdrawal','interest','currency exchange','fx conversion'))
    currency = raw['CCY']
    return movement(raw,line,action=kind,stamp=raw['Date'],ticker=field(raw,'Ticker'),isin=field(raw,'ISIN'),
        currency=currency,quantity=field(raw,'Quantity'),price=field(raw,'Price/share'),amount=field(raw,'Net Amt.'),
        source_id=field(raw,'Reference'),comma=comma,costs=(('fee','COMMISSION',field(raw,'Fee'),currency),
        ('tax','WITHHOLDING_TAX' if kind=='DIVIDEND' else 'TRANSACTION_TAX',field(raw,'Tax Amt.'),currency)))


def parse(text):
    return csv_rows(text, [('Date',),('Reference',),('Ticker',),('Type',),('CCY',),('Quantity',),('Price/share',),('Net Amt.',)],map_row)


ADAPTER = dict(name='Lightyear',
    formats=['csv'],
    parse=parse,
    guide='Open Profiel → Statements en download het Engelstalige transactierapport als CSV.',
    source='https://lightyear.com/en-eu/help/trading-and-investments/tax-and-statement')
