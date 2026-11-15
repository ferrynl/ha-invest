
"""Saxo transaction export and historical OpenAPI transactions."""
from ..broker_rows import action, csv_rows, field, movement

DATE = ('Trade Date','Transaction Date','Datum','Transactiedatum')
SIDE = ('Buy/Sell','Direction','Type','Koop/Verkoop')
QUANTITY = ('Quantity','Quantity Traded','Amount','Aantal')
PRICE = ('Trade Price','Price','Koers')
CURRENCY = ('Price Currency','Instrument Currency','Currency','Valuta')


def parse(text):
    def map_row(raw,line,comma):
        kind = action(field(raw,*SIDE),buy=('buy','bought','koop'),sell=('sell','sold','verkoop'))
        asset = field(raw,'Asset Type','Producttype').lower()
        if asset not in ('stock','stocks','equity','etf','aandeel','aandelen'):
            kind = None
        return movement(raw,line,action=kind,stamp=field(raw,*DATE),ticker=field(raw,'Symbol','Ticker'),isin=field(raw,'ISIN'),
            name=field(raw,'Instrument','Product'),currency=field(raw,*CURRENCY),quantity=field(raw,*QUANTITY),
            price=field(raw,*PRICE),source_id=field(raw,'Trade ID','TradeId'),comma=comma,
            costs=(('commission','COMMISSION',field(raw,'Commission','Commissie'),field(raw,'Commission Currency')),))
    return csv_rows(text,[DATE,SIDE,QUANTITY,PRICE,CURRENCY,('ISIN','Symbol','Ticker'),('Asset Type','Producttype')],map_row)


def api_rows(records):
    result = []
    for tx in records:
        trades = tx.get('Trades') or [{}]
        for trade in trades:
            instrument = trade.get('Instrument') or tx.get('Instrument') or {}
            kind = action(field(trade,'TradeEventType','TradeType') or field(tx,'Event'),
                          buy=('buy','bought'),sell=('sell','sold'))
            if tx.get('TransactionType') != 'Trade' or instrument.get('AssetType') not in ('Stock','Etf'):
                kind = 'SKIP' if tx.get('TransactionType') == 'CashTransfer' else None
            if tx.get('IsIntraDay') or not field(trade,'TradeId'):
                kind = kind if kind == 'SKIP' else None
            # TotalCost is explicitly denominated in the transaction account currency.
            result.append(movement({'Event':field(tx,'Event'), 'transaction':tx, 'trade':trade},len(result)+1,
                action=kind,stamp=field(trade,'TradeExecutionTime','AdjustedTradeDate') or field(tx,'Date'),
                ticker=field(instrument,'Symbol').split(':',1)[0],isin=field(instrument,'ISINCode'),
                name=field(instrument,'Description'),currency=field(instrument,'PriceCurrency','Currency'),
                quantity=field(trade,'TradedQuantity'),price=field(trade,'Price'),
                source_id=field(trade,'TradeId') or field(tx,'CorporateActionId','BookingId'),
                costs=(('total-cost','OTHER_FEE',field(tx,'TotalCost') if len(trades)==1 else '',field(tx,'Currency')),)))
    return result


ADAPTER = dict(name='Saxo',
    formats=['api', 'csv'],
    parse=parse,
    guide='Gebruik OpenAPI met een geldig toegangstoken en AccountKey. Voor CSV gebruik je het transactieoverzicht met datum, koop/verkoop, ticker of ISIN, aantal, koers, koersvaluta en producttype.',
    source='https://www.help.saxo/hc/nl/articles/360019241398-Waar-vind-ik-mijn-transactiehistorie-bij-Saxo')
