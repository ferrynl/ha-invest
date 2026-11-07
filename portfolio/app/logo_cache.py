"""Serve validated logo files from the installation's persistent data directory."""
import re
from threading import Lock
from time import monotonic
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ABOUT_DOMAINS=frozenset(('yahoo.com','divvydiary.com','huggingface.co','trading212.com',
                         'traderepublic.com','revolut.com','deutsche-boerse.com',
                         'rheinmetall.com','apollo.com','vaneck.com','allinvestview.com'))
DOMAIN=re.compile(r'(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}')
PNG=b'\x89PNG\r\n\x1a\n'
MAX_SIZE=512*1024


class CDNRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination=urlsplit(newurl)
        if destination.scheme!='https' or destination.netloc!='cdn.tickerlogos.com':
            return None
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class LogoCache:
    def __init__(self,root,on_error):
        self.root=root/'logos'
        self.on_error=on_error
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
            stage='download'
            try:
                request=Request('https://cdn.tickerlogos.com/'+domain,headers={'Accept':'image/png','User-Agent':'Home-Invest'})
                with build_opener(CDNRedirect()).open(request,timeout=4) as response:
                    data=response.read(MAX_SIZE+1)
                stage='image'
                if len(data)>MAX_SIZE or not data.startswith(PNG):
                    raise ValueError
                stage='storage'
                path.parent.mkdir(parents=True,exist_ok=True)
                tmp=path.with_suffix('.tmp')
                tmp.write_bytes(data)
                tmp.replace(path)
                self.failed.pop(key,None)
                return data
            except (OSError,ValueError) as error:
                status=error.code if isinstance(error,HTTPError) else None
                if isinstance(error,HTTPError):error.close()
                self.on_error(group,stage,type(error).__name__,status)
                if len(self.failed)>=512:
                    self.failed.pop(next(iter(self.failed)),None)
                self.failed[key]=monotonic()+3600
                return None
