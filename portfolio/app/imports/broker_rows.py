
"""Normalization shared by broker-specific statement adapters."""
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from forex import code

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000


def check_size(text):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Bestand is te groot (maximaal 5 MB).')


def field(raw, *names):
    for name in names:
        value = raw.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def decimal(value, comma=False):
    try:
        value = value.strip()
        if comma:
            value = value.replace(' ', '').replace('\u00a0', '')
            if ',' in value:
                value = value.replace('.', '').replace(',', '.')
        if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value) or len(value) > 40:
            raise InvalidOperation
        return Decimal(value)
    except InvalidOperation as error:
        raise ValueError('Ongeldig bronbedrag of aantal.') from error


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        for pattern in ('%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y', '%d/%m/%Y %H:%M',
                        '%d/%m/%Y', '%Y%m%d;%H%M%S', '%Y%m%d'):
            try:
                return datetime.strptime(value, pattern)
            except ValueError:
                continue
    raise ValueError('Ongeldige transactiedatum.')


def currency_code(value):
    if not re.fullmatch(r'[A-Za-z]{3}', value):
        raise ValueError('Valutacode ontbreekt.')
    return code(value)


def movement(raw, line, *, action, stamp='', ticker='', isin='', name='', currency='',
             quantity='', price='', amount='', source_id='', comma=False, costs=()):
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    row = dict(line=line, kind=action, ticker=ticker or isin, name=name, raw=dict(raw), error=None,
               external_id='id:'+source_id if source_id else 'row:'+digest, digest=digest)
    if isin:
        row['raw']['ISIN'] = isin
    try:
        if action == 'SKIP':
            return row
        if action not in ('BUY', 'SELL', 'DIVIDEND'):
            raise ValueError('Dit transactietype vereist beoordeling: '+field(raw, 'Type', 'type', 'Action', 'Transaction Type', 'Event', 'Transaktionstyp', 'Transaktionstype', 'buySell', 'Buy/Sell'))
        traded = timestamp(stamp)
        if traded.date() > date.today() or traded.year < 1900:
            raise ValueError('Transactiedatum valt buiten de toegestane periode.')
        if not row['ticker']:
            raise ValueError('Ticker en ISIN ontbreken.')
        row.update(day=traded.date().isoformat(), trade_time=traded.isoformat(), currency=currency_code(currency))
        if action == 'DIVIDEND':
            net = decimal(amount, comma)
            if net <= 0:
                raise ValueError('Netto dividend moet positief zijn.')
            row['amount'] = format(net.normalize(), 'f')
        else:
            shares, unit_price = abs(decimal(quantity, comma)), decimal(price, comma)
            if shares <= 0 or unit_price <= 0:
                raise ValueError('Aantal en prijs moeten positief zijn.')
            row.update(quantity=format(shares.normalize(), 'f'), price=format(unit_price.normalize(), 'f'))
        row['charges'] = []
        for component, category, value, denomination in costs:
            if not value:
                continue
            cost = abs(decimal(value, comma))
            if cost:
                row['charges'].append(dict(component=component, category=category,
                    amount=format(cost.normalize(), 'f'), currency=currency_code(denomination),
                    included_in_net=int(action == 'DIVIDEND'), description=component))
        if source_id:
            # The same execution can arrive through XML, CSV or the API.
            core = {k: row.get(k) for k in ('kind','ticker','day','trade_time','currency','quantity','price','amount')}
            row['digest'] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    except ValueError as error:
        row['error'] = str(error)
    return row


def csv_rows(text, required, mapper, *, finalize=None):
    check_size(text)
    for separator in (',', ';', '\t'):
        reader = csv.reader(io.StringIO(text.lstrip('\ufeff')), delimiter=separator, strict=True)
        try:
            headers = [value.strip() for value in next(reader, [])]
            if not all(set(group).intersection(headers) for group in required):
                continue
            if finalize:
                finalize(headers)
            repeated = {key for key in headers if key and headers.count(key) > 1}
            if repeated:
                raise ValueError('Dubbele CSV-kolommen: '+', '.join(sorted(repeated)))
            result = []
            for values in reader:
                if not any(value.strip() for value in values):
                    continue
                if len(result) >= MAX_ROWS or len(values) != len(headers):
                    raise ValueError('Te veel regels of een afwijkend aantal CSV-kolommen.')
                raw = {key: value.strip() for key, value in zip(headers, values) if key}
                result.append(mapper(raw, reader.line_num, separator != ','))
            if not result:
                raise ValueError('CSV bevat geen transacties.')
            return result
        except csv.Error as error:
            raise ValueError('Dit CSV-bestand is ongeldig.') from error
    raise ValueError('CSV-kolommen komen niet overeen met de export van deze broker.')


def action(value, **aliases):
    value = value.strip().casefold()
    for kind, labels in aliases.items():
        if value in labels:
            return kind.upper()
    return None
