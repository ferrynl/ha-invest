
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from imports import ADAPTERS
from imports.http_import import from_broker
from imports.interactivebrokers.client import retrieve_report
from imports.service import commit, open_preview, preview
from storage import Store


FLEX = """<FlexQueryResponse><FlexStatements><FlexStatement accountId="U100">
<Trades><Trade assetCategory="STK" levelOfDetail="EXECUTION" tradeID="42" buySell="BUY"
dateTime="20251024;140000" symbol="ASML" isin="NL0010273215" currency="EUR"
quantity="2" tradePrice="120.00" ibCommission="-1" ibCommissionCurrency="EUR"/></Trades>
</FlexStatement></FlexStatements></FlexQueryResponse>"""
FLEX_CSV = ('ClientAccountID,AssetCategory,LevelOfDetail,TradeID,Buy/Sell,DateTime,'
            'Symbol,ISIN,CurrencyPrimary,Quantity,TradePrice,IBCommission,IBCommissionCurrency\n'
            'U100,STK,EXECUTION,42,BUY,20251024;140000,ASML,NL0010273215,EUR,2,120,-1,EUR\n')
DEGIRO = ('Datum,Tijd,Product,ISIN,Aantal,Koers,,Lokale waarde,,Transactiekosten,,Order ID\n'
          '24-10-2025,14:00,ASML,NL0010273215,-2,"120,50",EUR,"241,00",EUR,"-1,00",EUR,order-1\n')
LIGHTYEAR = ('Date,Reference,Ticker,ISIN,Type,Quantity,CCY,Price/share,Net Amt.,Tax Amt.\n'
             '2025-10-24,L1,ASML,NL0010273215,Dividend,,EUR,,8,-2\n')
SCALABLE = ('date;time;status;reference;description;assetType;type;isin;shares;price;amount;fee;tax;currency\n'
            '2025-10-24;14:00:00;Executed;S1;ASML;Security;Buy;NL0010273215;2;120,50;-241;0,99;0;EUR\n')
NORDNET = ('Id;Handelsdag;Transaktionstype;ISIN;Antal;Kurs;Beløb;Valuta;Indkøbsværdi;Valuta;Kurtage;Valuta\n'
           'N1;2025-10-24;KØB;NL0010273215;2;120,50;-242;DKK;241;EUR;1;DKK\n')
SAXO = ('Trade Date,Trade ID,Asset Type,Buy/Sell,Symbol,ISIN,Quantity,Trade Price,Price Currency\n'
        '2025-10-24,42,Stock,Buy,ASML,NL0010273215,2,120,EUR\n')


class EuropeanBrokerImports(unittest.TestCase):
    def test_all_export_adapters_produce_previewable_rows(self):
        for provider, export, kind in (
            ('interactivebrokers', FLEX, 'BUY'), ('lynx', FLEX, 'BUY'),
            ('degiro', DEGIRO, 'SELL'), ('scalablecapital', SCALABLE, 'BUY'),
            ('lightyear', LIGHTYEAR, 'DIVIDEND'), ('nordnet', NORDNET, 'BUY'),
            ('saxo', SAXO, 'BUY'),
        ):
            with self.subTest(provider=provider):
                row, = ADAPTERS[provider]['parse'](export)
                self.assertIsNone(row['error'])
                self.assertEqual(row['kind'],kind)
                self.assertEqual(row['currency'],'EUR')
                self.assertEqual(row['raw']['ISIN'],'NL0010273215')
        dividend, = ADAPTERS['lightyear']['parse'](LIGHTYEAR)
        self.assertEqual(dividend['amount'],'8')
        self.assertEqual(dividend['charges'][0]['amount'],'2')
        self.assertEqual(dividend['charges'][0]['included_in_net'],1)
        nordnet, = ADAPTERS['nordnet']['parse'](NORDNET)
        self.assertEqual(nordnet['charges'][0]['currency'],'DKK')

    def test_flex_api_csv_and_xml_share_identity_at_execution_level(self):
        adapter = ADAPTERS['interactivebrokers']['parse']
        a, = adapter(FLEX)
        b, = adapter(FLEX_CSV)
        self.assertEqual((a['external_id'],a['digest']),(b['external_id'],b['digest']))
        with self.assertRaises(ValueError):
            adapter('<!DOCTYPE root [<!ENTITY x "test">]>'+FLEX)
        with self.assertRaises(ValueError):
            adapter(FLEX.replace('tradeID="42"','tradeID="42" accountId="U200"'))
        self.assertTrue(adapter(FLEX.replace('EXECUTION','SUMMARY'))[0]['error'])

    def test_api_preview_uses_existing_account_and_repeat_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            store.add_account(dict(name='Flex account',broker='Interactive Brokers'))
            with patch('imports.http_import.retrieve_report',return_value=FLEX) as fetch:
                with self.assertRaises(ValueError):
                    from_broker(store,'interactivebrokers/poll',dict(account_id=1))
                fetch.assert_not_called()
                result = from_broker(store,'interactivebrokers/poll',dict(account_id=2,token='123456',reference='5'))
            batch = result['preview']['batch_id']
            self.assertEqual(open_preview(store,batch)['rows'][0]['quantity'],'2')
            self.assertEqual(commit(store,batch,{'ASML|EUR':dict(symbol='ASML.AS',exchange='AMSTERDAM',currency='EUR')})['imported'],1)
            again = preview(store,2,'interactivebrokers','manual.csv',FLEX_CSV)
            self.assertTrue(again['rows'][0]['duplicate'])
            self.assertEqual(commit(store,again['batch_id'],{})['imported'],0)

    def test_pending_or_failed_flex_report_never_creates_preview(self):
        response = '<FlexStatementResponse><ErrorCode>{}</ErrorCode></FlexStatementResponse>'
        with patch('imports.interactivebrokers.client.download',return_value=response.format(1019)):
            self.assertIsNone(retrieve_report('123456','1'))
        with patch('imports.interactivebrokers.client.download',return_value=response.format(1003)):
            with self.assertRaises(ValueError):
                retrieve_report('123456','1')

    def test_saxo_reads_cash_and_trade_currency_independently(self):
        records = [dict(Date='2025-10-24',TransactionType='Trade',Event='Buy',
            Currency='DKK', TotalCost='-7',Trades=[dict(TradeId='42',TradedQuantity='2',Price='120',
            Instrument=dict(AssetType='Stock',PriceCurrency='EUR',Symbol='ASML:xams',ISINCode='NL0010273215'))])]
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            store.add_account(dict(name='Saxo account',broker='Saxo'))
            with patch('imports.http_import.transactions',return_value=records):
                result = from_broker(store,'saxo/fetch',dict(account_id=2))
            row, = result['preview']['rows']
            self.assertEqual((row['kind'],row['ticker'],row['currency']),('BUY','ASML','EUR'))
            self.assertEqual(row['charges'][0]['currency'],'DKK')

    def test_unknown_actions_keep_the_source_as_review_rows(self):
        row, = ADAPTERS['scalablecapital']['parse'](SCALABLE.replace('Executed','Cancelled'))
        self.assertTrue(row['error'])
        self.assertEqual(row['raw']['reference'],'S1')
        with self.assertRaises(ValueError):
            ADAPTERS['degiro']['parse'](LIGHTYEAR)
