"""Small read-only portfolio export for Home Assistant; no provider requests."""
import hmac
import json
import re
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit
from forex import unit


def valid_token(token):
    return isinstance(token,str) and re.fullmatch(r'[A-Za-z0-9_-]{32,128}',token) is not None


def build(snapshot,rates,today=None):
    today=today or date.today()
    day=today.isoformat();currencies={};total=Decimal(0);missing_fx=0;missing_quotes=0;dates={};quotes=[];count=0
    latest={}
    for row in rates:
        if row['base']=='EUR' and row['day']<=day and (today-date.fromisoformat(row['day'])).days<=7:
            if row['quote'] not in latest or row['day']>latest[row['quote']]['day']:latest[row['quote']]=row
    for position in snapshot['positions']:
        currency=position['currency']
        group=currencies.setdefault(currency,dict(known_value=Decimal(0),missing_quotes=0,positions=0))
        if Decimal(position['quantity'])==0:continue
        group['positions']+=1;count+=1
        quote=position.get('quote')
        if quote and quote.get('quoted_at'):quotes.append(quote['quoted_at'])
        if position['value'] is None:
            group['missing_quotes']+=1;missing_quotes+=1;continue
        value=Decimal(position['value']);group['known_value']+=value
        base,scale=unit(currency)
        if base=='EUR':total+=value*scale;continue
        fx=latest.get(base)
        if fx is None or Decimal(fx['rate'])<=0:missing_fx+=1;continue
        total+=value*scale/Decimal(fx['rate']);dates[currency]=fx['day']
    for group in currencies.values():
        group['complete']=group['missing_quotes']==0
        group['known_value']=str(group['known_value'])
        group['value']=group['known_value'] if group['complete'] else None
    complete=not (missing_fx or missing_quotes)
    return dict(as_of=day,data_revision=snapshot['data_revision'],oldest_quote_at=min(quotes) if quotes else None,
                currencies=currencies,total_eur=dict(value=str(total) if complete else None,known_value=str(total),
                complete=complete,missing_fx=missing_fx,missing_quotes=missing_quotes,positions=count,fx_dates=dates))


def overview(store,cache):
    def load():
        snapshot=cache.get(store.state)
        with store.read() as db:rates=[dict(row) for row in db.execute("SELECT base,quote,day,rate FROM fx_rates WHERE base='EUR'")]
        return build(snapshot,rates)
    return cache.derived('ha-export',load)


def configuration(currencies):
    lines=['rest:','  - resource: !secret home_invest_resource','    headers:','      Authorization: !secret home_invest_authorization',
           '    scan_interval: 60','    timeout: 15','    sensor:',
           '      - name: "Home Invest totaal EUR"','        unique_id: home_invest_total_eur','        device_class: monetary',
           '        unit_of_measurement: "EUR"',
           '        value_template: "{{ value_json.total_eur.value if value_json.total_eur.complete else \'unknown\' }}"',
           '        json_attributes_path: "$.total_eur"','        json_attributes: [complete, known_value, missing_fx, missing_quotes, positions, fx_dates]']
    for currency in sorted(currencies):
        if not re.fullmatch('[A-Z]{3}',currency):continue
        lines.extend(['      - name: "Home Invest '+currency+'"','        unique_id: home_invest_currency_'+currency.lower(),
                      '        unit_of_measurement: "'+currency+'"',
                      '        value_template: "{{ value_json.currencies.get(\''+currency+'\', {}).get(\'value\') if value_json.currencies.get(\''+currency+'\', {}).get(\'complete\', false) else \'unknown\' }}"'])
    return '\n'.join(lines)+'\n'


def make_export_handler(store,cache,token):
    class ExportHandler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def respond(self,body,code):
            raw=json.dumps(body,separators=(',',':')).encode()
            self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not valid_token(token) or not hmac.compare_digest(self.headers.get('Authorization','').encode(),('Bearer '+token).encode()):
                return self.respond({'error':'Ongeldige toegangssleutel.'},401)
            if urlsplit(self.path).path!='/api/ha/state':return self.respond({'error':'Niet gevonden.'},404)
            try:return self.respond(overview(store,cache),200)
            except Exception:return self.respond({'error':'Portefeuille tijdelijk niet beschikbaar.'},503)
        def do_POST(self):return self.respond({'error':'Alleen lezen.'},405)
        do_PUT=do_POST
        do_DELETE=do_POST
        do_PATCH=do_POST
    return ExportHandler
