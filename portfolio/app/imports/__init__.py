"""API-first directory of broker-owned adapter definitions."""
from . import (degiro, interactivebrokers, lightyear, lynx, nordnet, revolut,
               saxo, scalablecapital, traderepublic, trading212)
from .charge_csv import parse_csv as parse_charges


ADAPTERS = {
    'trading212': trading212.ADAPTER,
    'interactivebrokers': interactivebrokers.ADAPTER,
    'saxo': saxo.ADAPTER,
    'degiro': degiro.ADAPTER,
    'lynx': lynx.ADAPTER,
    'traderepublic': traderepublic.ADAPTER,
    'revolut': revolut.ADAPTER,
    'scalablecapital': scalablecapital.ADAPTER,
    'lightyear': lightyear.ADAPTER,
    'nordnet': nordnet.ADAPTER,
    'charges': dict(name='Kosten en belastingen', formats=['csv'], parse=parse_charges, any_broker=True),
}


def __getattr__(name):
    if name == 'trading212_api':
        from .trading212 import client
        return client
    raise AttributeError(name)
