"""One row per listing, with financial values summed across broker accounts."""
from decimal import Decimal
from instruments import category_overview

def overview(store,snapshot):
    metadata=category_overview(store);categories={(p['symbol'],p['exchange'],p['currency']):p['categories'] for p in metadata['entries']};groups={}
    fields=('quantity','cost','value','gain','dividend','total_gain','realised')
    for p in snapshot['positions']:
        key=tuple(p[k] for k in ('symbol','exchange','currency'))
        row=groups.setdefault(key,{**{k:p[k] for k in ('symbol','exchange','currency','name','quote')},'categories':categories.get(key,p.get('categories',{})),'broker_count':0,**{field:Decimal(0) for field in fields}})
        row['broker_count']+=1
        for field in fields:
            value=p.get(field,'0')
            row[field]=None if row[field] is None or value is None else row[field]+Decimal(value)
    positions=[]
    for p in groups.values():positions.append({**p,**{field:str(p[field]) if p[field] is not None else None for field in fields}})
    positions.sort(key=lambda p:p['name'].casefold())
    return dict(positions=positions,accounts=len({p['account_id'] for p in snapshot['positions']}))
