"""Small initial responses and on-demand history for at most six positions."""
def compact(snapshot):
    return {**snapshot,'compact':True,'positions':[{**p,'history':p['history'][-1:],'history_loaded':False} for p in snapshot['positions']]}

def histories(snapshot,account,selections):
    if not isinstance(selections,list) or not 1<=len(selections)<=6:raise ValueError('Selecteer maximaal zes posities.')
    owner=None if account=='all' else int(account)
    if owner is not None and not any(a['id']==owner for a in snapshot['accounts']):raise ValueError('Brokeraccount niet gevonden.')
    available={(p['account_id'],p['symbol'],p['exchange'],p.get('native_currency',p['currency'])):p for p in snapshot['positions'] if owner is None or p['account_id']==owner}
    result=[]
    for selection in selections:
        if not isinstance(selection,dict):raise ValueError('Ongeldige positie.')
        key=tuple(selection[k] for k in ('account_id','symbol','exchange','currency'))
        if key not in available:raise ValueError('Positie niet gevonden in dit brokeraccount.')
        result.append({**selection,'history':available[key]['history']})
    return {'histories':result,'data_revision':snapshot.get('data_revision')}
