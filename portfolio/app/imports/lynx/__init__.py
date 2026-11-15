
"""LYNX Account Management exports the Activity Flex Query XML format."""
from ..interactivebrokers import parse as parse_flex


def parse(text):
    if not text.lstrip('\ufeff \t\r\n').startswith('<'):
        raise ValueError('Gebruik de Activity Flex Query XML uit LYNX Account Management.')
    return parse_flex(text)


ADAPTER = dict(name='LYNX',
    formats=['xml'],
    parse=parse,
    guide='Ga in LYNX Account Management naar Performance & Reports → Flex Queries. Exporteer een Activity Flex Query voor één rekening als XML met Trades op uitvoeringsniveau.',
    source='https://simpleportfolio.app/guides/lynx-export/')
