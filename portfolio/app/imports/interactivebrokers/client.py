
"""Read-only Flex Web Service, without persisting tokens or following redirects."""
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from ..broker_http import NoRedirect
from ..broker_rows import MAX_BYTES
from . import xml_root


def download(action, token, query):
    if not re.fullmatch(r'\d{6,80}', token) or not re.fullmatch(r'\d{1,30}', query):
        raise ValueError('Vul een geldig Flex-token en query- of referentienummer in.')
    url = 'https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/'+action
    request = Request(url+'?'+urlencode(dict(t=token,q=query,v=3)),headers={'User-Agent':'Home Invest'})
    try:
        with build_opener(NoRedirect()).open(request,timeout=12) as response:
            content = response.read(MAX_BYTES+1)
        if len(content) > MAX_BYTES:
            raise ValueError('Flex-rapport is groter dan 5 MB. Kies een kortere periode.')
        return content.decode('utf-8-sig')
    except (OSError, UnicodeError) as error:
        raise ValueError('Flex Web Service is niet bereikbaar of heeft het verzoek geweigerd.') from error


def request_report(token, query):
    root = xml_root(download('SendRequest',token,query))
    reference = root.findtext('ReferenceCode','')
    if root.findtext('Status') != 'Success' or not re.fullmatch(r'\d{1,30}', reference):
        raise ValueError('Flex Query geweigerd. Controleer het token, query-ID en de Flex-instellingen.')
    return reference


def retrieve_report(token, reference):
    text = download('GetStatement',token,reference)
    if text.lstrip().startswith('<'):
        root = xml_root(text)
        if root.tag == 'FlexStatementResponse':
            if root.findtext('ErrorCode') == '1019':
                return None
            raise ValueError('Flex-rapport kon niet worden opgehaald. Controleer het token en referentienummer.')
    return text
