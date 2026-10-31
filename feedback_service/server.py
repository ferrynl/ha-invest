"""Bounded relay HTTP API; deploy behind an HTTPS reverse proxy, one replica."""
import hashlib
import hmac
import ipaddress
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .store import Rejected


class LimitedServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=32

    def __init__(self, *args, **kwargs):
        self.slots=threading.BoundedSemaphore(32)
        super().__init__(*args,**kwargs)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try: super().process_request(request,address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request,address)
        finally: self.slots.release()

    def handle_error(self, request, client_address):
        # Do not print client IPs, headers or tracebacks to container logs.
        print('request_failed',flush=True)


def make_handler(store, webhook_secret, repository_id, trusted_proxies=()):
    if len(webhook_secret)<32: raise ValueError('webhook_secret_too_short')
    proxies=tuple(ipaddress.ip_network(value) for value in trusted_proxies)
    if any(network.prefixlen==0 for network in proxies): raise ValueError('unbounded_proxy_trust')

    class Handler(BaseHTTPRequestHandler):
        server_version='HomeInvestRelay'
        sys_version=''

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args): pass

        def reply(self, data, status=200, retry_after=0):
            payload=json.dumps(data,separators=(',',':')).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            if retry_after: self.send_header('Retry-After',str(retry_after))
            self.end_headers()
            self.wfile.write(payload)

        def address(self):
            peer=ipaddress.ip_address(self.client_address[0])
            if any(peer in network for network in proxies):
                try: return str(ipaddress.ip_address(self.headers.get('X-Real-IP','')))
                except ValueError: raise Rejected('invalid_proxy',400) from None
            return str(peer)

        def authenticated(self):
            value=self.headers.get('Authorization','')
            if not value.startswith('Bearer '): raise Rejected('unauthorized',401)
            identity=store.authenticate(value[7:])
            with store.db() as db: store.consume(db,'read:'+identity,120,3600)
            return identity

        def read_body(self, limit):
            if self.headers.get('Transfer-Encoding') or self.headers.get_content_type()!='application/json': raise Rejected('invalid_request')
            if len(self.headers.get_all('Content-Length',[])) != 1: raise Rejected('invalid_request')
            try: size=int(self.headers.get('Content-Length','0'))
            except ValueError: raise Rejected('invalid_request') from None
            if not 0<size<=limit: raise Rejected('invalid_request',413)
            body=self.rfile.read(size)
            if len(body)!=size: raise Rejected('invalid_request')
            return body

        def dispatch(self, mutation=False):
            try:
                if self.path=='/health' and not mutation: return self.reply({'ok':True})
                store.throttle(self.address())
                if mutation and self.path=='/v1/github-webhook':
                    body=self.read_body(262144)
                    signature=self.headers.get('X-Hub-Signature-256','')
                    expected='sha256='+hmac.new(webhook_secret.encode(),body,hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(signature,expected): raise Rejected('unauthorized',401)
                    delivery=self.headers.get('X-GitHub-Delivery','')
                    if not re.fullmatch(r'[A-Za-z0-9-]{1,64}',delivery): raise Rejected('invalid_request')
                    data=json.loads(body)
                    if self.headers.get('X-GitHub-Event')=='ping': return self.reply({'ok':True})
                    if self.headers.get('X-GitHub-Event')!='issues' or data.get('repository',{}).get('id')!=repository_id: raise Rejected('invalid_event')
                    issue=data.get('issue',{})
                    if type(issue.get('number')) is not int or issue.get('state') not in ('open','closed'): raise Rejected('invalid_event')
                    store.webhook(delivery,issue['number'],issue['state'])
                    return self.reply({'ok':True},202)
                if mutation and self.path=='/v1/enroll':
                    store.throttle(self.address(),'enrollment',30)
                    data=json.loads(self.read_body(2048))
                    if not isinstance(data,dict) or set(data)!={'code','credential'}: raise Rejected('invalid_activation')
                    return self.reply({'installation_id':store.enroll(data['code'],data['credential'])},201)
                identity=self.authenticated()
                if self.path=='/v1/submissions':
                    if mutation: return self.reply(store.submit(identity,json.loads(self.read_body(24576))),202)
                    return self.reply({'submissions':store.mine(identity)})
                if self.path=='/v1/issues' and not mutation:
                    return self.reply(store.get_meta('board',{'issues':[],'limited':False,'checked_at':None}))
                raise Rejected('not_found',404)
            except Rejected as error: self.reply({'error':error.code},error.status,error.retry_after)
            except (ValueError,TypeError,AttributeError,TimeoutError): self.reply({'error':'invalid_request'},400)
            except Exception: self.reply({'error':'service_unavailable'},503,60)

        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch(True)

    return Handler
