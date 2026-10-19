"""Broker adapters normalize source rows; preview and commit remain broker-neutral."""
from .trading212 import parse_csv

ADAPTERS={'trading212':{'name':'Trading 212','formats':['csv','api'],'parse':parse_csv}}
