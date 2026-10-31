"""Broker account administration; ledger ownership stays stable when renamed."""
import hmac
from contextlib import contextmanager
from transactions import scope,revision,reset_preview_db


def edit(store,data):
    name=str(data.get('name','')).strip();broker=str(data.get('broker','')).strip()
    if not 1<=len(name)<=80 or not 1<=len(broker)<=80:raise ValueError('Vul een accountnaam en bedrijf in (maximaal 80 tekens).')
    with store.connect() as db:
        account_id=scope(db,data['id'])
        if account_id is None:raise ValueError('Kies één brokeraccount om te wijzigen.')
        current=dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(account_id,)).fetchone())
        if not hmac.compare_digest(str(data.get('revision','')),revision(current)):raise ValueError('De rekening is intussen gewijzigd. Open de rekening opnieuw.')
        if broker!=current['broker']:
            used=any(reset_preview_db(db,account_id)['counts'].values())
            if used or (store.root/'connections'/f'{account_id}.encrypted').exists():raise ValueError('De broker kan alleen worden gewijzigd bij een rekening zonder administratie of API-verbinding.')
        db.execute('UPDATE broker_accounts SET name=?,broker=? WHERE id=?',(name,broker,account_id))
    return {'ok':True}


def overview(store,account_id):
    with store.connect() as db:
        account_id=scope(db,account_id)
        if account_id is None:raise ValueError('Kies één brokeraccount om te wijzigen.')
        account=dict(db.execute('SELECT * FROM broker_accounts WHERE id=?',(account_id,)).fetchone())
        return {**account,'revision':revision(account)}


class BusyAccountError(ValueError):
    pass


@contextmanager
def mutation(store,connection_lock):
    # Market refresh writes shared instrument data and need not block account changes.
    # Keep the connection -> store lock order, but never queue a destructive request.
    if not connection_lock.acquire(blocking=False):raise BusyAccountError('Er wordt een API-rapport verwerkt. Probeer de rekening straks opnieuw te wijzigen of verwijderen.')
    try:
        if not store.lock.acquire(blocking=False):raise BusyAccountError('De administratie wordt bijgewerkt. Probeer de rekening straks opnieuw te wijzigen of verwijderen.')
        try:yield
        finally:store.lock.release()
    finally:connection_lock.release()
