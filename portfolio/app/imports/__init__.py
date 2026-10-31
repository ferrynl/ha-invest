"""Broker adapters normalize source rows; preview and commit remain broker-neutral."""
from .trading212 import parse_csv
from .traderepublic import parse_csv as parse_traderepublic
from .traderepublic import prepare_rows as prepare_traderepublic

ADAPTERS={'trading212':{'name':'Trading 212','formats':['csv','api'],'parse':parse_csv},
          'traderepublic':{'name':'Trade Republic','formats':['csv'],'parse':parse_traderepublic,'prepare':prepare_traderepublic}}

from .revolut import parse_csv as parse_revolut
ADAPTERS["revolut"]={"name":"Revolut","formats":["csv"],"parse":parse_revolut}
