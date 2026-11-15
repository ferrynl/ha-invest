
"""Nordnet Danish and Swedish transaction CSV."""
from ..broker_rows import action, csv_rows, field, movement

DAY = ('Handelsdag','Affärsdag')
TYPE = ('Transaktionstype','Transaktionstyp')
AMOUNT = ('Beløb','Belopp')
GROSS = ('Indkøbsværdi','Anskaffningsvärde','Inköpsvärde')
FEES = ('Kurtage','Courtage')


def parse(text):
    def configure(headers):
        for i,key in enumerate(headers):
            if key == 'Valuta':
                headers[i] = headers[i-1]+' Valuta' if i else 'Valuta'

    def map_row(raw,line,comma):
        kind = action(field(raw,*TYPE),buy=('køb','köp','kopt','købt'),sell=('salg','sälj','sålt','solgt'),
                      dividend=('udbytte','utdelning'),skip=('indbetaling','insättning','udbetaling','uttag'))
        currency = field(raw,*(key+' Valuta' for key in (GROSS if kind != 'DIVIDEND' else AMOUNT)))
        return movement(raw,line,action=kind,stamp=field(raw,*DAY),isin=field(raw,'ISIN'),
            name=field(raw,'Værdipapirer','Värdepapper'),currency=currency,quantity=field(raw,'Antal'),price=field(raw,'Kurs'),
            amount=field(raw,*AMOUNT),source_id=field(raw,'Id','ID'),comma=True,
            costs=(('commission','COMMISSION',field(raw,*FEES),field(raw,*(key+' Valuta' for key in FEES))),))

    return csv_rows(text,[DAY,TYPE,('ISIN',),('Antal',),('Kurs',),AMOUNT],map_row,finalize=configure)


ADAPTER = dict(name='Nordnet',
    formats=['csv'],
    parse=parse,
    guide='Exporteer je transactiehistorie in het Zweeds of Deens. Gebruik één CSV per rekening en behoud de oorspronkelijke valutakolommen.',
    source='https://forum.portfolio-performance.info/t/csv-import-fra-nordnet/32289/3')
