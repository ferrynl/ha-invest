"""Read the public app manifest; never install or execute remote content."""
import json
import re
from urllib.request import Request,urlopen
from persistent_cache import cached_json
from version import APP_VERSION

REPOSITORY='https://github.com/ferrynl/ha-invest'
def version_tuple(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Ongeldig versienummer.')
    return tuple(int(n) for n in value.split('.'))
def check_updates(store):
    def load():
        request=Request('https://raw.githubusercontent.com/ferrynl/ha-invest/main/portfolio/config.yaml',headers={'User-Agent':'Home-Invest-update-check'})
        with urlopen(request,timeout=15) as response:text=response.read(65536).decode('utf-8')
        match=re.search(r'^version:\s*[\"\']?(\d+\.\d+\.\d+)[\"\']?\s*$',text,re.M)
        if not match:raise ValueError('Versiecontrole kon de appversie niet lezen.')
        from datetime import datetime,timezone
        return dict(latest=match.group(1),checked_at=datetime.now(timezone.utc).isoformat())
    result=cached_json(store,'updates','github-main',86400,load)
    return {**result,'installed':APP_VERSION,'available':version_tuple(result['latest'])>version_tuple(APP_VERSION),'url':REPOSITORY}
