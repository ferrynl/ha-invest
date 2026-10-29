"""Disposable, deterministic demonstration data in its own SQLite database."""
from datetime import date,timedelta
from decimal import Decimal
from math import sin
from threading import RLock
from urllib.parse import urlsplit,parse_qs
from storage import Store

SEED_VERSION='1'
_demo_lock=RLock()
BROKERS=['DEGIRO','Interactive Brokers','Saxo','Trading 212','Trade Republic','Revolut','BUX','Scalable Capital','LYNX','Swissquote']
MARKETS=[
 ('EUR','AMSTERDAM','Netherlands','1','ASML|ASML;SHELL|Shell;UNA|Unilever;INGA|ING;AD|Ahold Delhaize;HEIA|Heineken;PHIA|Philips;WKL|Wolters Kluwer;NN|NN Group;DSM|DSM Firmenich;AIR|Airbus;SAP|SAP;SIE|Siemens;MC|LVMH;OR|L’Oreal'),
 ('USD','NASDAQ','United States','1.08','AAPL|Apple;MSFT|Microsoft;NVDA|NVIDIA;AMZN|Amazon;GOOGL|Alphabet;META|Meta Platforms;TSLA|Tesla;AVGO|Broadcom;COST|Costco;PEP|PepsiCo;ADBE|Adobe;CSCO|Cisco;AMD|AMD;INTU|Intuit;QCOM|Qualcomm'),
 ('GBP','LONDON','United Kingdom','.84','AZN|AstraZeneca;GSK|GSK;BP|BP;HSBA|HSBC;RIO|Rio Tinto;DGE|Diageo;REL|RELX;NG|National Grid;LSEG|London Stock Exchange;BA|BAE Systems;EXPN|Experian;LLOY|Lloyds;PRU|Prudential;SSE|SSE;VOD|Vodafone'),
 ('CHF','SWISS','Switzerland','.94','NESN|Nestle;NOVN|Novartis;ROG|Roche;UBSG|UBS;ZURN|Zurich Insurance;ABBN|ABB;SREN|Swiss Re;HOLN|Holcim;SIKA|Sika;GIVN|Givaudan;ALC|Alcon;SCMN|Swisscom;LONN|Lonza;SLHN|Swiss Life;PGHN|Partners Group'),
 ('JPY','TOKYO','Japan','163','7203|Toyota;6758|Sony;9984|SoftBank;7974|Nintendo;6861|Keyence;8306|Mitsubishi UFJ;6501|Hitachi;8035|Tokyo Electron;8058|Mitsubishi;9432|NTT;4063|Shin Etsu;6367|Daikin;6098|Recruit;4519|Chugai;4502|Takeda'),
 ('CAD','TORONTO','Canada','1.48','RY|Royal Bank of Canada;TD|Toronto Dominion;ENB|Enbridge;CNR|Canadian National Railway;CP|Canadian Pacific Kansas City;BNS|Scotiabank;BMO|Bank of Montreal;CNQ|Canadian Natural Resources;SU|Suncor;BCE|BCE;TRP|TC Energy;FTS|Fortis;WCN|Waste Connections;ATD|Alimentation Couche Tard;SHOP|Shopify'),
 ('AUD','ASX','Australia','1.63','BHP|BHP;CBA|Commonwealth Bank;CSL|CSL;NAB|National Australia Bank;WBC|Westpac;ANZ|ANZ;WES|Wesfarmers;MQG|Macquarie;WOW|Woolworths;FMG|Fortescue;TLS|Telstra;GMG|Goodman;RIO.AX|Rio Tinto Australia;WDS|Woodside;QBE|QBE Insurance'),
 ('HKD','HONG KONG','Hong Kong','8.43','0700|Tencent;9988|Alibaba;1299|AIA;0941|China Mobile;0005|HSBC Hong Kong;0388|Hong Kong Exchanges;0883|CNOOC;2318|Ping An;3690|Meituan;1211|BYD;1810|Xiaomi;9618|JD;9999|NetEase;0002|CLP;0016|Sun Hung Kai'),
 ('DKK','COPENHAGEN','Denmark','7.46','NOVO.B|Novo Nordisk;DSV|DSV;VWS|Vestas;ORSTED|Orsted;CARL.B|Carlsberg;DANSKE|Danske Bank;NZYM.B|Novonesis;COLO.B|Coloplast;PNDORA|Pandora;GMAB|Genmab;MAERSK.B|Maersk;TRYG|Tryg;ISS|ISS;DEMANT|Demant;ROCK.B|Rockwool'),
 ('SEK','STOCKHOLM','Sweden','11.3','VOLV.B|Volvo;ATCO.A|Atlas Copco;INVE.B|Investor;ASSA.B|Assa Abloy;SAND|Sandvik;ERIC.B|Ericsson;SEB.A|SEB;SWED.A|Swedbank;SHB.A|Handelsbanken;HM.B|Hennes Mauritz;HEXA.B|Hexagon;ESSITY.B|Essity;SCA.B|SCA;ALFA|Alfa Laval;NIBE.B|Nibe')]
SECTORS=['Technology','Financials','Healthcare','Industrials','Consumer Staples','Energy','Utilities','Materials','Consumer Discretionary','Real Estate']

def ensure_demo(root,today=None):
    today=today or date.today();store=Store(root)
    with _demo_lock:
        with store.read() as db:
            settings=dict(db.execute('SELECT key,value FROM app_settings'))
            count=db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0]
        if settings.get('demo_seed_version')==SEED_VERSION and settings.get('demo_day')==today.isoformat():return store
        if count and 'demo_seed_version' not in settings:raise ValueError('Demo-opslag bevat onbekende gegevens.')
        seed(store,today)
    return store

def seed(store,today):
    start=today-timedelta(days=730);stamp=today.isoformat()+'T12:00:00+00:00'
    instruments=[]
    for currency,exchange,country,rate,listing in MARKETS:
        for item in listing.split(';'):
            symbol,name=item.split('|');instruments.append((currency,exchange,country,Decimal(rate),symbol,name))
    weights=[Decimal(600+(i*37)%801) for i in range(len(instruments))];scale=Decimal(150000)/sum(weights)
    purchases=[];quotes=[];prices=[];dividends=[];categories=[];rates=[]
    for i,(currency,exchange,country,fx,symbol,name) in enumerate(instruments):
        quantity=Decimal(5+i%20);sale=quantity/10 if i%10==0 else Decimal(0)
        quote=(weights[i]*scale*fx/quantity).quantize(Decimal('.00000001'))
        owner=(i%15+i//15)%10+1
        for units,day,price,side in [(quantity*Decimal('.6')+sale,start,quote*Decimal('.78'),'BUY'),(quantity*Decimal('.4'),today-timedelta(days=365),quote*Decimal('.9'),'BUY')]+([(sale,today-timedelta(days=90),quote*Decimal('1.05'),'SELL')] if sale else []):
            purchases.append((symbol,exchange,name,str(units),str(price),currency,day.isoformat(),stamp,owner,side,''))
        quotes.append((symbol,exchange,currency,str(quote),stamp,stamp,'DEMO'))
        categories.append((symbol,exchange,currency,SECTORS[i%10],country,'Stock','',stamp,1,1,1))
        for offset in range(731):
            day=start+timedelta(days=offset);factor=Decimal(str(.78+.22*offset/730+.035*sin(offset/31+i)-.035*sin(730/31+i)*offset/730))
            prices.append((symbol,exchange,currency,day.isoformat(),str((quote*factor).quantize(Decimal('.00000001')))))
            frequency=12 if i%5==0 else 4
            if day.day==10+i%16 and (frequency==12 or day.month%3==i%3):
                held=quantity*Decimal('.6')+sale if day<today-timedelta(days=365) else quantity+(sale if day<today-timedelta(days=90) else Decimal(0))
                amount=quote*held*Decimal(str(.02+(i%6)*.005))/frequency
                dividends.append((symbol,exchange,currency,str(amount.quantize(Decimal('.00000001'))),day.isoformat(),'DEMO',stamp,owner))
    for offset in range(731):
        day=(start+timedelta(days=offset)).isoformat()
        rates.extend(('EUR',currency,day,rate,'DEMO',stamp) for currency,exchange,country,rate,listing in MARKETS if currency!='EUR')
    with store.connect() as db:
        for table in ('purchases','dividends','quotes','daily_prices','broker_accounts','fx_rates','fx_currencies','instrument_categories','api_cache','app_settings'):
            db.execute('DELETE FROM '+table)
        db.executemany('INSERT INTO broker_accounts(id,name,broker,created_at) VALUES(?,?,?,?)',[(i+1,name+' Demo',name,stamp) for i,name in enumerate(BROKERS)])
        db.executemany('INSERT INTO purchases(symbol,exchange,name,quantity,price,currency,purchased_on,created_at,account_id,side,trade_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)',purchases)
        db.executemany('INSERT INTO quotes(symbol,exchange,currency,price,quoted_at,fetched_at,source) VALUES(?,?,?,?,?,?,?)',quotes)
        db.executemany('INSERT INTO daily_prices VALUES(?,?,?,?,?)',prices)
        db.executemany('INSERT INTO dividends(symbol,exchange,currency,amount,paid_on,note,created_at,account_id) VALUES(?,?,?,?,?,?,?,?)',dividends)
        db.executemany('INSERT INTO instrument_categories VALUES(?,?,?,?,?,?,?,?,?,?,?)',categories)
        db.executemany('INSERT INTO fx_rates VALUES(?,?,?,?,?,?)',rates)
        db.executemany('INSERT INTO fx_currencies VALUES(?,?,?)',[(currency,currency,stamp) for currency,*rest in MARKETS])
        db.executemany('INSERT INTO app_settings VALUES(?,?)',[('auth_enabled','false'),('default_range','1Y'),('demo_seed_version',SEED_VERSION),('demo_day',today.isoformat())])

DEMO_READS={'/api/state','/api/home/euro','/api/home/history','/api/stocks','/api/dividends/overview','/api/reports/combined','/api/reports/history','/api/transactions','/api/transactions/changes','/api/instruments/categories','/api/instrument','/api/fx/history'}

def profile_handler(primary,store,auth,factory):
    lock=RLock();active={}
    def demo_handler():
        with lock:
            today=date.today().isoformat()
            if active.get('day')!=today:
                demo=ensure_demo(store.root/'demo');active.update(day=today,store=demo,handler=factory(demo))
            return active['handler']
    class ProfileHandler(primary):
        def do_GET(self):
            path=urlsplit(self.path).path;profile=self.headers.get('X-HomeInvest-Profile','personal')
            if profile not in ('personal','demo'):return self.respond({'error':'Ongeldig profiel.'},400)
            if path=='/api/profiles':
                if not self.allowed(auth.user(self.token())):return
                return self.respond({'profiles':[{'id':'personal','name':'Eigen portefeuille'},{'id':'demo','name':'Demoportefeuille'}]})
            if profile!='demo' or not path.startswith('/api/') or path=='/api/session':return super().do_GET()
            if not self.allowed(auth.user(self.token())):return
            try:handler=demo_handler()
            except ValueError as error:return self.respond({'error':str(error)},400)
            if path in DEMO_READS:return handler.do_GET(self)
            if path=='/api/instrument/company':return self.respond({'description':'Fictieve demogegevens. Geen actuele koersen.','website':'','domain':'','name':''})
            if path=='/api/fx':
                from forex import observation
                requested=parse_qs(urlsplit(self.path).query).get('day',[date.today().isoformat()])[0] or date.today().isoformat()
                try:date.fromisoformat(requested)
                except ValueError:return self.respond({'error':'Ongeldige datum.'},400)
                demo=active['store'];items=[]
                for currency,*rest in MARKETS:
                    row=observation(demo,currency,requested)
                    items.append(dict(code=currency,name=currency,to_eur=str(Decimal(1)/Decimal(row['rate'])) if row else None,rate_on=row['day'] if row else None))
                return self.respond(dict(currencies=items,history=[],conversions=[],requested_on=requested,error=None))
            return self.respond({'error':'Deze functie is niet beschikbaar in het demoprofiel.'},403)
        def discard_demo_body(self):
            try:length=int(self.headers.get('Content-Length','0'))
            except ValueError:length=0
            if 0<length<=65536:self.rfile.read(length)
        def do_POST(self):
            profile=self.headers.get('X-HomeInvest-Profile','personal')
            if profile not in ('personal','demo') or (profile=='demo' and urlsplit(self.path).path not in ('/api/auth/login','/api/auth/logout','/api/auth/password','/api/account/language')):self.discard_demo_body()
            if self.headers.get('X-HomeInvest-Profile','personal') not in ('personal','demo'):return self.respond({'error':'Ongeldig profiel.'},400)
            if self.headers.get('X-HomeInvest-Profile')=='demo' and urlsplit(self.path).path not in ('/api/auth/login','/api/auth/logout','/api/auth/password','/api/account/language'):
                if not self.allowed(auth.user(self.token())):return
                return self.respond({'error':'Het demoprofiel is alleen-lezen. Kies je eigen portefeuille om gegevens te wijzigen.'},403)
            return super().do_POST()
    return ProfileHandler
