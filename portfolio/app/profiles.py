"""One-time Yahoo profiles. Anonymous session material stays in memory, never in SQLite/logs."""
import json
import re
import threading
import time
from datetime import datetime,timedelta,timezone
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from urllib.request import Request,build_opener,HTTPCookieProcessor
from urllib.parse import quote,urlencode,urlsplit,unquote
from urllib.error import HTTPError,URLError
from persistent_cache import cached_json
from provider import EXCHANGES
from forex import code as currency_code
from diagnostics import ActionError,record
from instruments import validate_categories

_lock=threading.RLock()
_session=None
_crumb=None
_direct_retry_at=0
SECTORS={'Technology':'Technologie','Financial Services':'Financiële diensten','Healthcare':'Gezondheidszorg','Energy':'Energie','Industrials':'Industrie','Real Estate':'Vastgoed','Consumer Defensive':'Defensieve consumentengoederen','Consumer Cyclical':'Cyclische consumentengoederen','Communication Services':'Communicatiediensten','Utilities':'Nutsbedrijven','Basic Materials':'Basismaterialen'}
COUNTRIES={'Netherlands':'Nederland','United States':'Verenigde Staten','United Kingdom':'Verenigd Koninkrijk','Germany':'Duitsland','France':'Frankrijk','Belgium':'België','Switzerland':'Zwitserland','Canada':'Canada','Ireland':'Ierland','Luxembourg':'Luxemburg','Spain':'Spanje','Italy':'Italië','Sweden':'Zweden','Norway':'Noorwegen','Denmark':'Denemarken','Austria':'Oostenrijk','Finland':'Finland','Australia':'Australië','China':'China','Japan':'Japan'}
TYPES={'EQUITY':'Aandeel','ETF':'ETF','MUTUALFUND':'Beleggingsfonds','BOND':'Obligatie'}

class ProfileError(ActionError):
    def __init__(self,code,seconds=900,details=None):
        super().__init__('Automatische categorieën konden niet worden opgehaald.',code,details)
        self.seconds=seconds

def _open(url,response_type='json',stage='quote_summary'):
    # Cookie bootstrap/profile pages are HTML; the crumb endpoint returns plain text.
    accepts={'json':'application/json','html':'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8','text':'text/plain,*/*;q=0.8'}
    headers={'User-Agent':'Mozilla/5.0','Accept':accepts[response_type],'Accept-Language':'en-US,en;q=0.9'}
    started=time.monotonic()
    try:return _session.open(Request(url,headers=headers),timeout=15)
    except (HTTPError,URLError,TimeoutError,OSError) as error:
        # Only fixed request metadata, never a URL query, headers, body or cookie.
        error.profile_details={'stage':stage,'endpoint_host':urlsplit(url).hostname,'requested_format':response_type,'duration_ms':round((time.monotonic()-started)*1000)}
        if isinstance(error,HTTPError):error.profile_details['http_status']=error.code
        raise

def _download_direct(symbol):
    global _session,_crumb
    if _session is None:_session=build_opener(HTTPCookieProcessor(CookieJar()))
    if _crumb is None:
        try:
            with _open('https://fc.yahoo.com',response_type='html',stage='cookie_bootstrap') as response:response.read(1024)
        except HTTPError as error:
            if error.code!=404:raise
            error.close()  # This cookie bootstrap may return 404 with Set-Cookie.
        with _open('https://query1.finance.yahoo.com/v1/test/getcrumb',response_type='text',stage='session_crumb') as response:crumb=response.read(1025).decode('utf-8').strip()
        if not crumb or len(crumb)>1024 or any(c.isspace() for c in crumb) or '<' in crumb:raise ProfileError('session_unavailable')
        _crumb=crumb
    params=urlencode({'modules':'assetProfile,quoteType,price','crumb':_crumb})
    with _open('https://query2.finance.yahoo.com/v10/finance/quoteSummary/'+quote(symbol,safe='')+'?'+params) as response:
        raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ProfileError('invalid_profile')
        return json.loads(raw)

class EmbeddedProfile(HTMLParser):
    """Read only Yahoo's serialized API response for the exact requested symbol."""
    def __init__(self,symbol):
        super().__init__();self.symbol=symbol;self.active=False;self.chunks=[];self.payload=None
    def handle_starttag(self,tag,attrs):
        if tag!='script':return
        attrs=dict(attrs);url=urlsplit(attrs.get('data-url',''))
        self.active=attrs.get('type')=='application/json' and 'data-sveltekit-fetched' in attrs and url.scheme=='https' and url.hostname in ('query1.finance.yahoo.com','query2.finance.yahoo.com') and unquote(url.path)=='/v10/finance/quoteSummary/'+self.symbol
        self.chunks=[]
    def handle_data(self,data):
        if self.active:self.chunks.append(data)
    def handle_endtag(self,tag):
        if tag!='script' or not self.active:return
        self.active=False
        try:
            wrapper=json.loads(''.join(self.chunks))
            if wrapper.get('status')!=200:return
            body=wrapper.get('body');value=json.loads(body) if isinstance(body,str) else body
            if isinstance(value,dict) and value.get('quoteSummary',{}).get('result'):self.payload=value
        except (ValueError,TypeError,AttributeError):pass

def _download_profile(symbol):
    global _session,_crumb,_direct_retry_at
    if time.time()>=_direct_retry_at:
        try:return _download_direct(symbol)
        except HTTPError as error:
            if error.code not in (401,403,406):raise
            error.close()
        except (URLError,TimeoutError,OSError,ProfileError):pass
        _direct_retry_at=time.time()+900
    # The profile page carries the same quoteSummary API response server-side.
    # This avoids requiring a user login when the anonymous cookie host is blocked.
    _session=build_opener(HTTPCookieProcessor(CookieJar()));_crumb=None
    with _open('https://finance.yahoo.com/quote/'+quote(symbol,safe='')+'/profile/',response_type='html',stage='profile_page') as response:
        raw=response.read(4*1024*1024+1)
        if len(raw)>4*1024*1024:raise ProfileError('invalid_profile')
    parser=EmbeddedProfile(symbol);parser.feed(raw.decode('utf-8'))
    if parser.payload is None:raise ProfileError('profile_unavailable')
    return parser.payload

def normalize_profile(payload,key):
    try:
        summary=payload['quoteSummary']
        if summary.get('error'):raise ProfileError('invalid_profile')
        row=summary['result'][0];price=row['price'];kind=row.get('quoteType') or {};profile=row.get('assetProfile') or {}
        market=EXCHANGES.get(str(price.get('exchange','')).upper())
        if str(price.get('symbol','')).upper()!=key[0] or not market or market[0]!=key[1] or currency_code(price.get('currency',''))!=key[2]:raise ProfileError('listing_mismatch',86400)
        if kind.get('symbol') and str(kind['symbol']).upper()!=key[0]:raise ProfileError('listing_mismatch',86400)
        sector=profile.get('sector') or '';country=profile.get('country') or ''
        asset_type=TYPES.get(kind.get('quoteType') or price.get('quoteType'),'')
        if asset_type=='Aandeel' and re.search(r'\bREIT\b',str(profile.get('industry','')),re.I):asset_type='REIT'
        values=validate_categories(dict(sector=SECTORS.get(sector,sector),country=COUNTRIES.get(country,country),asset_type=asset_type))
        return {field:values[field] for field in ('sector','country','asset_type')}
    except ProfileError:raise
    except (ValueError,KeyError,IndexError,TypeError,AttributeError):raise ProfileError('invalid_profile') from None

def fetch_profile(store,key):
    def load():
        global _session,_crumb
        with _lock:
            with store.connect() as db:pauses=db.execute("SELECT expires_at FROM api_cache WHERE namespace='provider-cooldown' AND cache_key IN ('yahoo','yahoo-profile')").fetchall()
            delay=max((row[0]-time.time() for row in pauses),default=0)
            if delay>0:raise ProfileError('provider_cooldown',max(1,int(delay)))
            try:return normalize_profile(_download_profile(key[0]),key)
            except HTTPError as error:
                _session=None;_crumb=None
                try:seconds=min(86400,max(900,int((error.headers or {}).get('Retry-After','900'))))
                except (ValueError,TypeError):seconds=900
                code='http_'+str(error.code);error.close()
                raise ProfileError(code,seconds,getattr(error,'profile_details',{'stage':'unknown','http_status':error.code})) from None
            except (URLError,TimeoutError,OSError,UnicodeError) as error:
                _session=None;_crumb=None
                raise ProfileError('connection_error',details=getattr(error,'profile_details',{'stage':'unknown'})) from None
            except (ValueError,TypeError) as error:
                if isinstance(error,ProfileError):raise
                raise ProfileError('invalid_profile') from None
    cached=cached_json(store,'yahoo-profile-v1','|'.join(key),30*86400,load)
    if not isinstance(cached,dict):raise ProfileError('invalid_profile')
    try:values=validate_categories(cached)
    except (ValueError,TypeError):raise ProfileError('invalid_profile') from None
    return {field:values[field] for field in ('sector','country','asset_type')}

def enrich_categories(store,key,retry=False):
    """Claim outside network I/O; re-read manual flags before writing provider values."""
    stamp=datetime.now(timezone.utc)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM purchases WHERE symbol=? AND exchange=? AND currency=? UNION ALL SELECT 1 FROM dividends WHERE symbol=? AND exchange=? AND currency=?',(*key,*key)).fetchone():return False
        sync=db.execute('SELECT * FROM instrument_category_sync WHERE symbol=? AND exchange=? AND currency=?',key).fetchone()
        if sync and (sync['status']=='complete' or sync['status']=='partial' and not retry or datetime.fromisoformat(sync['retry_at'])>stamp):return False
        attempts=sync['attempts']+1 if sync else 1
        db.execute("INSERT INTO instrument_category_sync VALUES(?,?,?,'fetching',?,?,?,'') ON CONFLICT(symbol,exchange,currency) DO UPDATE SET status='fetching',attempted_at=excluded.attempted_at,retry_at=excluded.retry_at,attempts=excluded.attempts,error_code=''",(*key,stamp.isoformat(),(stamp+timedelta(minutes=10)).isoformat(),attempts))
    try:
        result=fetch_profile(store,key)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            claim=db.execute('SELECT * FROM instrument_category_sync WHERE symbol=? AND exchange=? AND currency=?',key).fetchone()
            if not claim or claim['attempted_at']!=stamp.isoformat():return False
            previous=db.execute('SELECT * FROM instrument_categories WHERE symbol=? AND exchange=? AND currency=?',key).fetchone()
            values={field:previous[field] if previous else '' for field in ('sector','country','asset_type','category')}
            manual={field:previous['manual_'+field] if previous else 0 for field in ('sector','country','asset_type')}
            filled=[]
            for field in manual:
                if not manual[field] and not values[field] and result.get(field):values[field]=result[field];filled.append(field)
            db.execute('INSERT INTO instrument_categories VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol,exchange,currency) DO UPDATE SET sector=excluded.sector,country=excluded.country,asset_type=excluded.asset_type,updated_at=excluded.updated_at',(*key,*(values[field] for field in ('sector','country','asset_type','category')),stamp.isoformat(),*(manual[field] for field in ('sector','country','asset_type'))))
            status='complete' if all(result.get(field) for field in manual) else 'partial'
            db.execute("UPDATE instrument_category_sync SET status=?,retry_at=?,error_code='' WHERE symbol=? AND exchange=? AND currency=?",(status,(stamp+timedelta(days=1)).isoformat(),*key))
        record(store,'INFO','market','categories_filled','Aandelencategorieën eenmalig uit de API aangevuld.',{'symbol':key[0],'exchange':key[1],'currency':key[2],'provider':'Yahoo Finance','status':status,'filled_fields':filled,'missing_fields':[field for field in manual if not result.get(field)]})
        return True
    except Exception as error:
        code=error.code if isinstance(error,ProfileError) else 'profile_failed'
        seconds=max(error.seconds if isinstance(error,ProfileError) else 900,min(86400,900*2**min(attempts-1,7)))
        with store.connect() as db:
            db.execute("UPDATE instrument_category_sync SET status='retry',retry_at=?,error_code=? WHERE symbol=? AND exchange=? AND currency=? AND attempted_at=?",((stamp+timedelta(seconds=seconds)).isoformat(),code,*key,stamp.isoformat()))
            if code in ('connection_error','http_401','http_403','http_406','http_429','http_503','session_unavailable'):
                current=time.time();db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',('provider-cooldown','yahoo-profile','{}',current,current+seconds))
        record(store,'WARNING','market','categories_failed','Automatische categorieën ophalen mislukt; opnieuw proberen na de wachttijd.',{'symbol':key[0],'exchange':key[1],'currency':key[2],'code':code,'retry_seconds':seconds,'attempt':attempts,'error_type':type(error).__name__,**(error.details if isinstance(error,ProfileError) else {})})
        return False
