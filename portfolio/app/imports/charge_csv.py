"""Explicit supplemental cost entries, never inferred from a price difference."""
import csv,io,hashlib,json
from datetime import date
from charges import number,validate_charge
from forex import code

FIELDS=('date','reference','category','amount','currency','ticker','included_in_net','description')

def parse_csv(text):
    if len(text)>5*1024*1024:raise ValueError('CSV is te groot (maximaal 5 MB).')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not set(FIELDS).issubset(reader.fieldnames):raise ValueError('Gebruik de CSV-kolommen date, reference, category, amount, currency, ticker, included_in_net en description.')
    rows=[]
    try:
        for line,source in enumerate(reader,2):
            if line>10001:raise ValueError('Maximaal 10.000 CSV-regels per import.')
            malformed=None in source or any(v is None for v in source.values())
            raw={k:str(v or '').strip() for k,v in source.items() if k is not None}
            digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
            row=dict(line=line,kind='CHARGE',ticker=raw['ticker'].upper(),name=raw['description'],raw=raw,digest=digest,external_id='id:'+raw['reference']+':'+raw['category'],error=None)
            try:
                if malformed:raise ValueError('CSV-regel bevat een onjuist aantal kolommen.')
                if raw['included_in_net'] not in ('0','1'):raise ValueError('Ongeldige kostensoort of nettoverwerking.')
                if not raw['reference']:raise ValueError('Ongeldige kostenreferentie.')
                charge=dict(component='entry',category=raw['category'],amount=str(number(raw['amount'])),currency=code(raw['currency']),included_in_net=int(raw['included_in_net']),description=raw['description'])
                validate_charge({**charge,'external_id':row['external_id'],'ticker':row['ticker'],'paid_on':raw['date']})
                row.update(day=date.fromisoformat(raw['date']).isoformat(),trade_time=raw['date']+'T00:00:00',currency=charge['currency'],amount=charge['amount'],charges=[charge])
            except (ValueError,KeyError) as error:row['error']=str(error)
            rows.append(row)
    except csv.Error:raise ValueError('CSV-regel bevat een onjuist aantal kolommen.') from None
    if not rows:raise ValueError('CSV bevat geen gegevens.')
    return rows
