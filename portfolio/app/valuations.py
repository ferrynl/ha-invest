"""Explicit final prices and actionable diagnostics for omitted valuations."""
import hashlib
import json
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from diagnostics import record

def validate_price(value):
    try:price=Decimal(str(value))
    except InvalidOperation:raise ValueError('Vul een geldige laatste koers in.') from None
    if not price.is_finite() or price<0 or price>Decimal('1e15'):raise ValueError('De laatste koers moet nul of positief zijn, maximaal 10^15.')
    return str(price)

def final_quote(row):
    return dict(symbol=row['symbol'],exchange=row['exchange'],currency=row['currency'],price=row['price'],quoted_at=row['day']+'T00:00:00+00:00',fetched_at=row['updated_at'],source='Handmatige laatste koers',manual=True)

def apply_final_prices(quotes,daily,manual):
    keys={tuple(row[k] for k in ('symbol','exchange','currency')):row for row in manual}
    def keep(row):
        setting=keys.get(tuple(row[k] for k in ('symbol','exchange','currency')))
        return not setting or (row.get('day') or row['quoted_at'][:10])<setting['day']
    quotes=[row for row in quotes if keep(row)]+[final_quote(row) for row in manual]
    daily=[row for row in daily if keep(row)]+[{**row,'day':row['day']} for row in manual]
    return quotes,daily

def save(store,data):
    from instruments import identity
    from storage import now
    key=identity(data);automatic=data.get('automatic')
    if not isinstance(automatic,bool):raise ValueError('Kies automatisch ophalen of een laatste koers.')
    if not automatic:
        price=validate_price(data.get('price'));day=date.fromisoformat(data.get('day',''))
        if day>date.today():raise ValueError('De koersdatum mag niet in de toekomst liggen.')
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM purchases WHERE symbol=? AND exchange=? AND currency=?',key).fetchone():raise ValueError('Aandeel niet gevonden.')
        if automatic:db.execute('DELETE FROM instrument_valuations WHERE symbol=? AND exchange=? AND currency=?',key)
        else:db.execute('INSERT OR REPLACE INTO instrument_valuations VALUES(?,?,?,?,?,?)',(*key,price,day.isoformat(),now()))
    record(store,'INFO','market','valuation_changed','Koersinstelling aangepast.',dict(symbol=key[0],exchange=key[1],currency=key[2],automatic=automatic,**({} if automatic else dict(price=price,day=day.isoformat()))))
    return dict(ok=True)

def missing_diagnostics(store,positions):
    for p in positions:
        if p['value'] is not None:continue
        details={k:p[k] for k in ('account_id','name','symbol','exchange','currency','quantity','cost','dividend')}
        details.update(reason='no_quote',excluded_from_known_profit=True,last_quote=p.get('quote'))
        reference=hashlib.sha256(json.dumps(details,sort_keys=True).encode()).hexdigest()[:12]
        since=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()
        with store.connect() as db:previous=db.execute('SELECT 1 FROM app_logs WHERE reference=? AND event=? AND created_at>?',(reference,'valuation_missing',since)).fetchone()
        if not previous:record(store,'WARNING','valuation','valuation_missing','Positie zonder koers overgeslagen bij bekende marktwaarde en winst.',details,reference=reference)
        p['valuation_log_id']=reference
