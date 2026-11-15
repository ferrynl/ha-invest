
"""Activity Flex Query executions and cash transactions."""
from xml.etree import ElementTree

from ..broker_rows import MAX_ROWS, check_size, csv_rows, field, movement


def xml_root(text):
    check_size(text)
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('XML met DTD of entiteiten wordt niet ondersteund.')
    try:
        return ElementTree.fromstring(text.lstrip('\ufeff'))
    except ElementTree.ParseError as error:
        raise ValueError('Ongeldig Flex XML-bestand.') from error


def trade(raw, line, comma=False):
    action = field(raw, 'buySell', 'Buy/Sell').upper()
    category = field(raw, 'assetCategory', 'AssetCategory').upper()
    detail = field(raw, 'levelOfDetail', 'LevelOfDetail').upper()
    if action in ('BUY', 'SELL') and (category not in ('STK','ETF','FUND') or detail not in ('EXECUTION','TRADE')):
        action = None
    return movement(raw,line,action=action,stamp=field(raw,'dateTime','DateTime','Date/Time'),
        ticker=field(raw,'symbol','Symbol'),isin=field(raw,'isin','ISIN'),name=field(raw,'description','Description'),
        currency=field(raw,'currency','CurrencyPrimary','Currency'),quantity=field(raw,'quantity','Quantity'),
        price=field(raw,'tradePrice','TradePrice','Price'),source_id=field(raw,'tradeID','TradeID'),
        costs=(('commission','COMMISSION',field(raw,'ibCommission','IBCommission'),field(raw,'ibCommissionCurrency','IBCommissionCurrency')),))


def cash(raw, line):
    currency = field(raw,'currency')
    # The Flex cash section reports gross dividends and separate withholding rows.
    # Keep both for review so withholding is never lost or booked as net income.
    kind = 'SKIP' if field(raw,'type') in ('Deposits/Withdrawals','Broker Interest Paid','Broker Interest Received') else None
    return movement(raw,line,action=kind,stamp=field(raw,'dateTime'),ticker=field(raw,'symbol'),
        isin=field(raw,'isin'),currency=currency,source_id=field(raw,'transactionID'))


def parse(text):
    if not text.lstrip('\ufeff \t\r\n').startswith('<'):
        accounts = set()
        def map_trade(raw,line,comma):
            account = field(raw,'ClientAccountID','AccountId','AccountID')
            if not account:
                raise ValueError('Neem Account ID op in de Activity Flex Query.')
            accounts.add(account)
            if len(accounts) > 1:
                raise ValueError('Exporteer één brokerrekening per bestand.')
            return trade(raw,line,comma)
        return csv_rows(text, [('Symbol',), ('Buy/Sell',), ('AssetCategory',), ('LevelOfDetail',),
            ('DateTime','Date/Time'),('CurrencyPrimary','Currency'), ('TradePrice','Price'), ('Quantity',)],map_trade)
    root = xml_root(text)
    if root.tag != 'FlexQueryResponse':
        raise ValueError('Gebruik een Activity Flex Query in XML-formaat.')
    statements = root.findall('./FlexStatements/FlexStatement')
    accounts = {statement.get('accountId','') for statement in statements}
    if len(accounts) != 1 or '' in accounts:
        raise ValueError('Exporteer precies één brokerrekening per Flex Query.')
    rows = []
    for statement in statements:
        for node in statement.iter():
            if node.tag not in ('Trade','CashTransaction','CorporateAction','Transfer'):
                continue
            if len(rows) >= MAX_ROWS:
                raise ValueError('Maximaal 10.000 transacties per import.')
            line = len(rows)+1
            raw = node.attrib
            if raw.get('accountId',statement.get('accountId')) not in accounts:
                raise ValueError('Exporteer precies één brokerrekening per Flex Query.')
            if node.tag == 'Trade':
                rows.append(trade(raw,line))
            elif node.tag == 'CashTransaction':
                rows.append(cash(raw,line))
            else:
                rows.append(movement(raw,line,action=None,source_id=field(raw,'transactionID')))
    if not rows:
        raise ValueError('Flex Query bevat geen transacties.')
    return rows


ADAPTER = dict(name='Interactive Brokers',
    formats=['api', 'xml', 'csv'],
    parse=parse,
    guide='Maak in Client Portal een Activity Flex Query voor één rekening. Kies Trades op uitvoeringsniveau en neem Account ID, Trade ID, Asset Category, Level of Detail, datum/tijd, koers, aantal en commissie met valuta op. Kies bij voorkeur XML.',
    source='https://www.interactivebrokers.com/docs/web-api/flex-web-service/using-flex-web-service/generate-the-report')
