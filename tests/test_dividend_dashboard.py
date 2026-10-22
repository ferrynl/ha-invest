import sys,unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'portfolio'/'app'))
from dividend_dashboard import overview,month_offset
TODAY=date(2026,10,22)
def position(symbol='TEST',account=1,currency='EUR',quantity='10',history=None):
 return dict(symbol=symbol,account_id=account,exchange='TEST',currency=currency,name=symbol,account_name='Broker '+str(account),quantity=quantity,history=history or [dict(day='2025-11-01',quantity='5'),dict(day='2026-10-22',quantity=quantity)])
def payment(day,amount='10',symbol='TEST',account=1,currency='EUR'):
 return dict(symbol=symbol,account_id=account,exchange='TEST',currency=currency,paid_on=day,amount=amount)
def snapshot(positions=None,payments=None,trades=None):
 return dict(positions=positions or [],dividends=payments or [],purchases=trades or [],accounts=[dict(id=1,name='One'),dict(id=2,name='Two')])
class DividendDashboardTests(unittest.TestCase):
 def test_actual_totals_decimal_and_current_holdings_forecast_do_not_mix(self):
  data=snapshot([position()], [payment('2026-01-15','0.1'),payment('2026-04-15','0.2'),payment('2025-10-22','100'),payment('2027-01-01','999')])
  result=overview(data,today=TODAY)['currencies'][0]
  self.assertEqual(Decimal(result['total']),Decimal('100.3'));self.assertEqual(Decimal(result['ytd']),Decimal('.3'));self.assertEqual(Decimal(result['trailing12']),Decimal('.3'));self.assertEqual(Decimal(result['previous12']),100)
  self.assertEqual(Decimal(result['next12']),Decimal('.6'));self.assertEqual(result['forecast'][0]['month'],'2026-11');self.assertEqual(result['forecast'][-1]['month'],'2031-10');self.assertEqual(len(result['forecast']),60)
  self.assertEqual(Decimal(next(p for p in result['forecast'] if p['month']=='2027-01')['amount']),Decimal('.2'))
 def test_closed_positions_keep_actual_income_but_are_excluded_from_forecast(self):
  result=overview(snapshot([position(quantity='0')],[payment('2026-01-15')]),today=TODAY)['currencies'][0]
  self.assertEqual(Decimal(result['total']),10);self.assertEqual(Decimal(result['next12']),0);self.assertEqual(result['coverage']['modeled'],0);self.assertFalse(result['contributors'][0]['open'])
 def test_currency_and_broker_scope_are_preserved(self):
  result=overview(snapshot([position(),position(account=2,currency='USD')],[payment('2026-01-15'),payment('2026-01-15','999',account=2,currency='USD')]),'1',TODAY)
  self.assertEqual([r['currency'] for r in result['currencies']],['EUR']);self.assertEqual(result['currencies'][0]['total'],'10')
  self.assertEqual(len(overview(snapshot([position(),position(account=2,currency='USD')]),today=TODAY)['currencies']),2)
  for account in ['bad','99']:
   with self.assertRaises(ValueError):overview(snapshot(),account,TODAY)
 def test_known_split_adjusts_payment_per_share_and_unknown_split_is_not_guessed(self):
  split=dict(account_id=1,symbol='TEST',exchange='TEST',currency='EUR',purchased_on='2026-06-01',quantity='10',split_before='5')
  data=snapshot([position()],[payment('2026-01-15')],[split])
  result=overview(data,today=TODAY)['currencies'][0];self.assertEqual(Decimal(result['next12']),10)
  split['split_before']='0';result=overview(data,today=TODAY)['currencies'][0];self.assertEqual(Decimal(result['next12']),0);self.assertIn('Splitsing',result['coverage']['excluded'][0]['reason'])
 def test_missing_basis_and_recent_positions_are_explained_without_guessing(self):
  data=snapshot([position(history=[dict(day='2026-02-01',quantity='10')]),position(symbol='NEW')],[payment('2026-01-15')])
  result=overview(data,today=TODAY)['currencies'][0];self.assertEqual(result['coverage']['modeled'],0);self.assertEqual(len(result['coverage']['excluded']),2);self.assertEqual(result['total'],'10')
 def test_leap_dates_month_boundaries_and_empty_portfolio(self):
  self.assertEqual(month_offset(date(2024,12,31),1),date(2025,1,1));self.assertEqual(month_offset(date(2024,1,31),-1),date(2023,12,1))
  self.assertEqual(overview(snapshot(),today=date(2024,2,29))['currencies'],[])
 def test_current_year_expected_includes_only_remaining_full_months(self):
  result=overview(snapshot([position()],[payment('2025-11-15'),payment('2026-01-15')]),today=TODAY)['currencies'][0]
  year=next(y for y in result['yearly'] if y['year']==2026);self.assertEqual(year['months_expected'],2);self.assertEqual(Decimal(year['received']),10);self.assertEqual(Decimal(year['expected']),20)
  last=result['yearly'][-1];self.assertEqual(last['months_expected'],10)

 def test_empty_dividend_history_retains_currency_and_explains_coverage(self):
  result=overview(snapshot([position()]),today=TODAY)['currencies'][0]
  self.assertEqual(result['total'],'0');self.assertEqual(result['payments'],0);self.assertEqual(result['coverage']['open'],1);self.assertEqual(result['coverage']['modeled'],0);self.assertEqual(len(result['coverage']['excluded']),1)

import test_transactions as transaction_test_support
class DividendDashboardHttpTests(unittest.TestCase):
 setUp=transaction_test_support.TransactionHttpTests.setUp
 tearDown=transaction_test_support.TransactionHttpTests.tearDown
 request=transaction_test_support.TransactionHttpTests.request
 def test_dashboard_requires_login_respects_scope_and_does_not_call_provider(self):
  from unittest.mock import patch
  with patch('provider.fetch_quote') as quote,patch('profiles._download_profile') as profile:
   status,data=self.request('/api/dividends/overview?account_id=all')
   self.assertEqual(status,200);self.assertEqual(data['account_id'],'all');quote.assert_not_called();profile.assert_not_called()
  self.assertEqual(self.request('/api/dividends/overview?account_id=999')[0],400)
  self.auth.enable('owner','Long-test-password-2026');self.assertEqual(self.request('/api/dividends/overview')[0],401)
  self.auth.save_user(dict(username='viewer',password='Long-test-password-2026',role='basic'));token=self.auth.login('viewer','Long-test-password-2026','test')
  self.assertEqual(self.request('/api/dividends/overview',token=token)[0],200)
