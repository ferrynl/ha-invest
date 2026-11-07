"""Serve validated logo files from the installation's persistent data directory."""
import re
from threading import Lock
from time import monotonic
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, build_opener

ABOUT_DOMAINS=frozenset(('yahoo.com','divvydiary.com','huggingface.co','trading212.com',
                         'traderepublic.com','revolut.com','deutsche-boerse.com',
                         'rheinmetall.com','apollo.com','vaneck.com','allinvestview.com'))
DOMAIN=re.compile(r'(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}')
PNG=b'\x89PNG\r\n\x1a\n'
MAX_SIZE=512*1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class LogoCache:
    def __init__(self,root):
        self.root=root/'logos'
        self.locks=[Lock() for _ in range(16)]
        self.failed={}

    def get(self,group,domain):
        if group not in ('about','dividend') or not DOMAIN.fullmatch(domain):
            return None
        if group=='about' and domain not in ABOUT_DOMAINS:
            return None
        path=self.root/group/domain/'logo.png'
        with self.locks[hash((group,domain)) % len(self.locks)]:
            try:
                return path.read_bytes()
            except FileNotFoundError:
                pass
            except OSError:
                return None
            key=(group,domain)
            if self.failed.get(key,0)>monotonic():
                return None
            try:
                with build_opener(NoRedirect()).open('https://cdn.tickerlogos.com/'+domain,timeout=4) as response:
                    data=response.read(MAX_SIZE+1)
                if len(data)>MAX_SIZE or not data.startswith(PNG):
                    raise ValueError
                path.parent.mkdir(parents=True,exist_ok=True)
                tmp=path.with_suffix('.tmp')
                tmp.write_bytes(data)
                tmp.replace(path)
                self.failed.pop(key,None)
                return data
            except (URLError,OSError,ValueError):
                if len(self.failed)>=512:
                    self.failed.pop(next(iter(self.failed)),None)
                self.failed[key]=monotonic()+3600
                return None
