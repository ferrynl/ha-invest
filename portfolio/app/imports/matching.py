"""Automatic listing resolution. Never guess exchange rates or select a fuzzy hit."""
import json
import re
from provider import search_stocks,fetch_quote,listing
from persistent_cache import cached_json
from diagnostics import record
from .listings import CATALOGUE

def ticker_base(value):
    value=re.sub(r'_(US|NL|UK|DE|FR|IT|CH)_EQ$','',value.upper())
    return re.sub(r'\.(AS|PA|DE|MI|L|SW|F)$','',value)

def resolve(store,rows,provider,preferred=None):
    first=rows[0];ticker=first['ticker'];currency=first['currency'];target=preferred or currency
    isins={r.get('raw',{}).get('ISIN','').strip().upper() for r in rows}-{''}
    if len(isins)>1:return {'error':'Meerdere ISIN-codes bij '+ticker+'. Deze brongegevens zijn niet eenduidig.'}
    isin=next(iter(isins),'');base=ticker_base(ticker)
    identity='|'.join((provider,isin or ticker,currency,preferred or ''))
    def find():
        # Prefer mappings proven by prior committed imports with the same ISIN/ticker.
        with store.connect() as db:
            batches=db.execute("SELECT payload FROM import_batches WHERE provider=? AND status='imported' ORDER BY id DESC LIMIT 200",(provider,)).fetchall()
        for batch in batches:
            for row in json.loads(batch['payload']):
                if row.get('currency')!=currency:continue
                same=(row.get('raw',{}).get('ISIN','').upper()==isin) if isin else row.get('ticker')==ticker
                if same and row.get('mapping') and (not preferred or row['mapping']['currency']==target):return {'mapping':row['mapping'],'via':'Bewaarde koppeling'}
        # Issuer-backed ISIN tables bypass incomplete Yahoo search indexes.
        catalogue=CATALOGUE.get(isin,[])
        if catalogue:
            verified=[]
            for symbol in catalogue:
                try:stock=listing(symbol,store=store)
                except Exception:continue
                verified.append(stock)
                if stock['currency']==(preferred or currency):return {'mapping':stock,'via':'Gecontroleerde ISIN-notering'}
            if verified:return {'mapping':verified[0],'via':'Gecontroleerde ISIN-notering met historische valutaomrekening'}
        queries=[]
        for query in (isin,base,first.get('name','')):
            if 2<=len(query)<=80 and query not in queries:queries.append(query)
        observed=set();failures=False;convertible=[]
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
                try:fetch_quote('',stock['symbol'],stock['exchange'],target,store=store)
                except Exception:
                    failures=True
                    try:actual=listing(stock['symbol'],store=store)
                    except Exception:continue
                    convertible.append(actual);continue
                verified[(stock['symbol'],stock['exchange'])]={**stock,'currency':target}
            if len(verified)==1:return {'mapping':next(iter(verified.values())),'via':'ISIN / ticker en gecontroleerde koersvaluta'}
        unique={(c['symbol'],c['exchange']):c for c in convertible}
        if len(unique)==1:return {'mapping':next(iter(unique.values())),'via':'Exacte ticker met historische valutaomrekening'}
        if observed and currency not in observed:
            reason='Bronvaluta '+currency+' wijkt af van de gevonden koersvaluta ('+', '.join(sorted(observed))+'). Er kon geen betrouwbare notering worden gecontroleerd; ontbrekende koersen worden niet gegokt.'
        elif failures:reason='Koersdienst tijdelijk niet beschikbaar of de gevonden notering kon niet worden gecontroleerd. Probeer de automatische koppeling opnieuw.'
        else:reason='Geen eenduidige ondersteunde notering gevonden voor '+ticker+((' · ISIN '+isin) if isin else '')+'.'
        return {'error':reason}
    result=cached_json(store,'import-listing-v3',identity,7*86400,find)
    # Do not keep transient failures for a week.
    if result.get('error'):
        with store.connect() as db:db.execute("DELETE FROM api_cache WHERE namespace='import-listing-v3' AND cache_key=?",(identity,))
    return result

def resolve_instrument(store,batch_id,key):
    with store.connect() as db:batch=db.execute('SELECT * FROM import_batches WHERE id=?',(batch_id,)).fetchone()
    if not batch or batch['status']!='preview':raise ValueError('Importvoorbeeld niet beschikbaar.')
    rows=json.loads(batch['payload'])
    selected=[r for r in rows if r.get('kind') not in (None,'SKIP') and r.get('ticker','')+'|'+r.get('currency','')==key and not r.get('duplicate')]
    if not selected:raise ValueError('Instrument niet gevonden in dit importvoorbeeld.')
    # Dividend settlement currency may differ from the listing currency. Reuse
    # the quote currency of purchases of the same instrument in this batch.
    isin=selected[0].get('raw',{}).get('ISIN','')
    related=[r for r in rows if r.get('kind') in ('BUY','SELL') and ((isin and r.get('raw',{}).get('ISIN')==isin) or r.get('ticker')==selected[0]['ticker'])]
    preferred=None
    held={}
    if selected[0].get('kind')=='DIVIDEND':
        mappings=[r['mapping'] for r in related if r.get('mapping')]
        if not mappings:
            with store.connect() as db:previous=db.execute("SELECT payload FROM import_batches WHERE account_id=? AND provider=? AND status='imported' ORDER BY id DESC LIMIT 200",(batch['account_id'],batch['provider'])).fetchall()
            for old in previous:
                for row in json.loads(old['payload']):
                    same=(isin and row.get('raw',{}).get('ISIN')==isin) or (not isin and row.get('ticker')==selected[0]['ticker'])
                    if same and row.get('kind') in ('BUY','SELL') and row.get('mapping'):mappings.append(row['mapping'])
        for item in mappings:held[(item['symbol'],item['exchange'],item['currency'])]=item
        if mappings:preferred=mappings[0]['currency']
        elif related:preferred=related[0]['currency']
    if len(held)==1:result={'mapping':next(iter(held.values())),'via':'Bestaande aankoop in dit brokeraccount'}
    elif len(held)>1:result={'error':'Dividend hoort bij meerdere bestaande noteringen. Deze ontvangst kan niet veilig aan één positie worden toegewezen.'}
    else:result=resolve(store,selected,batch['provider'],preferred)
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
