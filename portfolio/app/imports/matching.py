"""Automatic listing resolution. Never guess exchange rates or select a fuzzy hit."""
import json
import re
from provider import search_stocks,fetch_quote
from persistent_cache import cached_json
from diagnostics import record

def ticker_base(value):
    value=re.sub(r'_(US|NL|UK|DE|FR|IT|CH)_EQ$','',value.upper())
    return re.sub(r'\.(AS|PA|DE|MI)$','',value)

def resolve(store,rows,provider):
    first=rows[0];ticker=first['ticker'];currency=first['currency']
    isins={r.get('raw',{}).get('ISIN','').strip().upper() for r in rows}-{''}
    if len(isins)>1:return {'error':'Meerdere ISIN-codes bij '+ticker+'. Deze brongegevens zijn niet eenduidig.'}
    isin=next(iter(isins),'');base=ticker_base(ticker)
    identity='|'.join((provider,isin or ticker,currency))
    def find():
        # Prefer mappings proven by prior committed imports with the same ISIN/ticker.
        with store.connect() as db:
            batches=db.execute("SELECT payload FROM import_batches WHERE provider=? AND status='imported' ORDER BY id DESC LIMIT 200",(provider,)).fetchall()
        for batch in batches:
            for row in json.loads(batch['payload']):
                if row.get('currency')!=currency:continue
                same=(row.get('raw',{}).get('ISIN','').upper()==isin) if isin else row.get('ticker')==ticker
                if same and row.get('mapping'):return {'mapping':row['mapping'],'via':'Bewaarde koppeling'}
        queries=[]
        for query in (isin,base,first.get('name','')):
            if 2<=len(query)<=80 and query not in queries:queries.append(query)
        observed=set();failures=False
        for query in queries:
            try:candidates=search_stocks(query,store=store)
            except Exception:failures=True;continue
            observed.update(c['currency'] for c in candidates)
            exact=[c for c in candidates if ticker_base(c['symbol'])==base]
            # An ISIN lookup identifies the security; otherwise require an exact ticker.
            accepted=exact or (candidates if isin and query==isin else [])
            unique={(c['symbol'],c['exchange'],c['currency']):c for c in accepted}
            verified={}
            for stock in unique.values():
                # Search results often omit currency. Check chart metadata instead
                # of excluding USD listings merely because their exchange is in Europe.
                try:fetch_quote('',stock['symbol'],stock['exchange'],currency,store=store)
                except Exception:failures=True;continue
                verified[(stock['symbol'],stock['exchange'])]={**stock,'currency':currency}
            if len(verified)==1:return {'mapping':next(iter(verified.values())),'via':'ISIN / ticker en gecontroleerde koersvaluta'}
        if observed and currency not in observed:
            reason='Bronvaluta '+currency+' wijkt af van de gevonden koersvaluta ('+', '.join(sorted(observed))+'). Automatisch omrekenen is nog niet beschikbaar.'
        elif failures:reason='Koersdienst tijdelijk niet beschikbaar of de gevonden notering kon niet worden gecontroleerd. Probeer de automatische koppeling opnieuw.'
        else:reason='Geen eenduidige ondersteunde notering gevonden voor '+ticker+((' · ISIN '+isin) if isin else '')+'.'
        return {'error':reason}
    result=cached_json(store,'import-listing-v1',identity,7*86400,find)
    # Do not keep transient failures for a week.
    if result.get('error'):
        with store.connect() as db:db.execute("DELETE FROM api_cache WHERE namespace='import-listing-v1' AND cache_key=?",(identity,))
    return result

def resolve_instrument(store,batch_id,key):
    with store.connect() as db:batch=db.execute('SELECT * FROM import_batches WHERE id=?',(batch_id,)).fetchone()
    if not batch or batch['status']!='preview':raise ValueError('Importvoorbeeld niet beschikbaar.')
    rows=json.loads(batch['payload'])
    selected=[r for r in rows if r.get('kind') not in (None,'SKIP') and r.get('ticker','')+'|'+r.get('currency','')==key and not r.get('duplicate')]
    if not selected:raise ValueError('Instrument niet gevonden in dit importvoorbeeld.')
    result=resolve(store,selected,batch['provider'])
    with store.connect() as db:
        # Re-read after network I/O to preserve other resolved instruments.
        current=db.execute("SELECT payload FROM import_batches WHERE id=? AND status='preview'",(batch_id,)).fetchone()
        if not current:raise ValueError('Importvoorbeeld is inmiddels verwerkt.')
        rows=json.loads(current['payload'])
        for row in rows:
            if row.get('ticker','')+'|'+row.get('currency','')==key:
                if result.get('mapping'):row['mapping']=result['mapping']
        db.execute('UPDATE import_batches SET payload=? WHERE id=?',(json.dumps(rows),batch_id))
    record(store,'INFO' if result.get('mapping') else 'WARNING','imports','listing_resolved' if result.get('mapping') else 'listing_unresolved','Automatische beurskoppeling afgerond.' if result.get('mapping') else result['error'],{'batch_id':batch_id,'ticker':selected[0]['ticker'],'currency':selected[0]['currency']})
    return result
