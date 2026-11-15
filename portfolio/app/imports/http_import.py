
"""Route-specific read-only broker imports use the normal saved preview pipeline."""
import json

from . import ADAPTERS, saxo
from .interactivebrokers.client import request_report, retrieve_report
from .saxo.client import transactions
from .service import preview, import_account


def from_broker(store, operation, data):
    provider, action = operation.split('/',1)
    account_id = int(data['account_id'])
    import_account(store,account_id,ADAPTERS[provider])
    token = str(data.get('token','')).strip()
    if provider == 'interactivebrokers' and action == 'start':
        return {'reference':request_report(token,str(data.get('query','')).strip())}
    if provider == 'interactivebrokers' and action == 'poll':
        statement = retrieve_report(token,str(data.get('reference','')).strip())
        if statement is None:
            return {'pending':True}
        filename = 'ibkr-flex.xml' if statement.lstrip().startswith('<') else 'ibkr-flex.csv'
        return {'preview':preview(store,account_id,provider,filename,statement)}
    if provider == 'saxo' and action == 'fetch':
        records = transactions(token,str(data.get('key','')).strip(),str(data.get('start','')),
                               str(data.get('end','')),str(data.get('environment','')))
        return {'preview':preview(store,account_id,provider,'saxo-openapi.json',
                                  json.dumps(records,ensure_ascii=False),parse=lambda _: saxo.api_rows(records))}
    raise ValueError('Onbekende importactie.')
