/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
/* Database-backed overview; request long histories only for selected positions. */
const homeKey=p=>JSON.stringify([p.account_id,p.symbol,p.exchange,p.native_currency??p.currency]);
function homeReturn(p){const basis=Number(p.history?.at(-1)?.invested??p.cost);return p.total_gain==null||basis<=0?null:Number(p.total_gain)/basis*100;}
function homeSummary(positions){
 const total={value:0,cost:0,gain:0,dividend:0,missing:0,open:0};
 for(const p of positions){total.cost+=Number(p.cost);total.dividend+=Number(p.dividend);if(Number(p.quantity)>0)total.open++;if(p.value==null)total.missing++;else total.value+=Number(p.value);if(p.total_gain!=null)total.gain+=Number(p.total_gain);}
 return total;
}
function homeRows(positions,query,filter,sort){
 const term=query.trim().toLocaleLowerCase((typeof appLocale==='function'?appLocale():'nl-NL'));
 const rows=positions.filter(p=>(!term||[p.name,p.symbol,p.account_name,p.exchange].join(' ').toLocaleLowerCase((typeof appLocale==='function'?appLocale():'nl-NL')).includes(term))&&(filter==='all'||filter==='open'&&Number(p.quantity)>0||filter==='missing'&&p.value==null||filter==='winners'&&p.total_gain!=null&&Number(p.total_gain)>0||filter==='losers'&&p.total_gain!=null&&Number(p.total_gain)<0));
 return rows.sort((a,b)=>{if(sort==='name')return a.name.localeCompare(b.name,'nl');const x=sort==='return'||sort==='loss'?homeReturn(a):a.value==null?null:Number(a.value),y=sort==='return'||sort==='loss'?homeReturn(b):b.value==null?null:Number(b.value);if(x==null)return y==null?a.name.localeCompare(b.name):1;if(y==null)return -1;return (sort==='loss'?x-y:y-x)||a.name.localeCompare(b.name);});
}
let homeCurrency='ALL',homePage=0,homeMode='overview',homeFocus='',homeSelected=new Set();
let homeEuro=null,homeEuroSource=null,homeEuroRequest=0,homeEuroPending=false,homeEuroAccount='';
let homeEuroChartController=null,homeEuroChartPending=false,homeEuroChartRefreshes=0,homeEuroError=false;
const homeDisplayCurrency=()=>homeCurrency==='ALL'?'EUR':homeCurrency;
const homeEuroFallback=()=>homeCurrency==='ALL'&&!homeEuro&&!!homeEuroError&&state?.positions?.some(p=>p.currency==='EUR');
const homeIsCombined=()=>homeCurrency==='ALL'&&!homeEuroFallback();
const homeViewState=()=>homeIsCombined()?{...state,positions:homeEuro?.positions??[],portfolios:homeEuro?.portfolios??[]}:state;
const homeScope=()=>homeIsCombined()?(homeEuro?.positions??[]):state?.positions.filter(p=>p.currency===homeDisplayCurrency())??[];
function homeChartMembers(){return homeScope().filter(p=>homeSelected.has(homeKey(p))).slice(0,6);}
function clearHomeDashboard(){homeEuroChartController?.abort();homeEuroChartController=null;homeEuroChartPending=false;homeEuroChartRefreshes=0;homeEuroError=false;$('chart-return-badge').textContent='';$('chart-measure').value='value';for(const box of document.querySelectorAll('#home-module-board .home-metric'))box.replaceChildren();homeHistoryPending.clear();homeEuroRequest++;homeEuroPending=false;homeEuro=null;homeEuroSource=null;homeEuroAccount='';$('home-euro-status').textContent='';homeCurrency='ALL';homePage=0;homeMode='overview';homeFocus='';homeSelected.clear();for(const id of ['home-currencies','home-positions','home-allocation','home-movers','home-daily-gainers','home-daily-losers'])$(id).replaceChildren();for(const id of ['home-summary','home-health','home-table-note','home-selection-count','home-page-note','home-table-empty','home-allocation-note'])$(id).textContent='';$('home-search').value='';$('home-position-filter').value='open';$('home-sort').value='value';$('home-ranking').value='best';$('chart').onpointermove=null;$('chart').onpointerleave=null;$('chart').onkeydown=null;$('chart-day-details').ontoggle=null;$('chart-days-more').onclick=null;$('chart-day-details').open=false;$('chart-days-note').textContent='';$('instrument').replaceChildren();$('chart-legend').replaceChildren();$('chartnote').textContent='';$('chart-detail').textContent='';}
function homeNode(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function homePercent(value){return value==null?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(value)+'%';}
const homeMetricOptions={
 market:()=>ui('Marktwaarde'),cost:()=>ui('Openstaande kostprijs'),gain:()=>ui('Totale winst'),income:()=>ui('Ontvangen dividend'),
 invested:()=>ui('Totale aankoopinleg'),return:()=>ui('Resultaat sinds aankoop (%)'),realised:()=>ui('Gerealiseerd resultaat'),
 unrealised:()=>ui('Ongerealiseerd'),open:()=>ui('Open posities'),closed:()=>ui('Gesloten posities'),
 missing:()=>ui('Posities zonder koers'),dividend_yield:()=>ui('Dividend als % van aankoopinleg')
};
function homeDashboardMetrics(scope,summary){
 const currency=homeDisplayCurrency();
 const counts=new Intl.NumberFormat(appLocale());
 const totals={invested:0,knownInvested:0,realised:0,unrealised:0};
 for(const p of scope){
  const invested=Number(p.history?.at(-1)?.invested??p.cost)||0;
  totals.invested+=invested;
  if(p.total_gain!=null)totals.knownInvested+=invested;
  if(p.value!=null)totals.unrealised+=Number(p.value)-Number(p.cost);
  totals.realised+=Number(p.realised)||0;
 }
 const amount=(value,detail,signed=false)=>({value:money(value,currency),detail,tone:signed?(value>=0?'positive':'negative'):''});
 const countScope=homeIsCombined()?state.positions:scope;
 const count=value=>({value:counts.format(value),detail:ui('Binnen de huidige selectie')});
 return {
  market:amount(summary.value,summary.missing?ui('Bekende waarde · ')+summary.missing+ui(' posities zonder koers'):ui('Alle posities in ')+currency+ui(' met beschikbare koers')),
  cost:amount(summary.cost,summary.open+(homeIsCombined()?ui(' omgerekende open posities'):ui(' open posities in deze valuta'))),
  gain:amount(summary.gain,summary.missing?ui('Bekende posities · ')+summary.missing+ui(' zonder koers overgeslagen'):ui('Inclusief gerealiseerde winst en gekoppeld dividend'),true),
  income:amount(summary.dividend,homeDividendLabel(scope)),
  invested:amount(totals.invested,ui('Aankopen zonder aftrek van verkopen')),
  return:{value:homePercent(totals.knownInvested>0?summary.gain/totals.knownInvested*100:null),detail:ui('Winst als % van de inleg van bekende posities')},
  realised:amount(totals.realised,ui('Verkopen met geboekt resultaat'),true),
  unrealised:amount(totals.unrealised,ui('Marktwaarde min openstaande kostprijs'),true),
  open:count(countScope.filter(p=>Number(p.quantity)>0).length),
  closed:count(countScope.filter(p=>p.quantity!=null&&Number(p.quantity)===0).length),
  missing:count(countScope.filter(p=>p.value==null).length),
  dividend_yield:{value:homePercent(totals.invested>0?summary.dividend/totals.invested*100:null),detail:ui('Dividend als % van aankoopinleg')}
 };
}
function renderHomeMetricCards(scope,summary){
 const values=homeDashboardMetrics(scope,summary);
 for(const row of activeDashboardLayout()){
  const key=row.metric||(Object.hasOwn(homeMetricOptions,row.id)?row.id:null);
  if(!key||!row.enabled)continue;
  const box=$('home-module-'+row.id),data=values[key],pending=homeIsCombined()&&!homeEuro&&!['open','closed','missing'].includes(key);
  box.dataset.style=row.style||'standard';
  box.replaceChildren(homeNode('span',row.title||homeMetricOptions[key](),'home-metric-label'),
   homeNode('strong',pending?(homeEuroPending?ui('Laden…'):ui('Niet beschikbaar')):data.value,pending?'':data.tone));
  if(row.note!==false)box.append(homeNode('small',data.detail));
 }
}
function renderHomeDashboard(){
 if(!state)return;const currencies=[...new Set(state.positions.map(p=>p.currency))].sort();if(homeEuroAccount&&homeEuroAccount!==String(currentBroker)){homeEuro=null;homeEuroSource=null;homeEuroAccount='';homeEuroRequest++;homeEuroPending=false;homeEuroChartRefreshes=0;}if(homeCurrency!=='ALL'&&!currencies.includes(homeCurrency))homeCurrency='ALL';
 if(homeEuro?.data_revision===state.data_revision&&homeEuroAccount===String(currentBroker)&&homeEuro.as_of===(state.portfolios?.[0]?.history?.at(-1)?.day||homeEuro.as_of))homeEuroSource=state;
 if(homeCurrency==='ALL'&&homeEuroSource!==state&&!homeEuroPending)loadHomeEuro();
 const keys=new Set(homeViewState().positions.map(homeKey));homeSelected=new Set([...homeSelected].filter(key=>keys.has(key)));
 $('home-currencies').replaceChildren();for(const currency of ['ALL',...currencies]){const count=state.positions.filter(p=>(currency==='ALL'||p.currency===currency)&&Number(p.quantity)>0).length;const button=homeNode('button',currency==='ALL'?ui('Alle valuta’s in euro'):currency+' · '+count+ui(' posities'));button.type='button';button.setAttribute('aria-pressed',String(currency===homeCurrency));button.addEventListener('click',()=>{homeCurrency=currency;homePage=0;homeMode='overview';homeFocus='';homeSelected.clear();renderHomeDashboard();draw();$('home-currencies').querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});});$('home-currencies').append(button);}
 const scope=homeScope(),summary=homeSummary(scope);$('home-summary').textContent=state.positions.length?state.positions.filter(p=>Number(p.quantity)>0).length+ui(' open posities · ')+currencies.length+ui(' valuta · ')+(homeIsCombined()?ui('totaal omgerekend naar EUR'):ui('overzicht in ')+homeDisplayCurrency()):ui('Voeg een aankoop toe of importeer je portefeuille om te beginnen.');
 renderHomeMetricCards(scope,summary);
 const missing=state.positions.filter(p=>p.value==null);$('home-health').replaceChildren();
 if(missing.length){$('home-health').append(homeNode('strong',ui('Zonder koers, overgeslagen bij de bekende totalen: ')));for(const [index,p] of missing.entries()){if(index)$('home-health').append(document.createTextNode(' · '));const link=homeNode('a',p.name+' ('+p.symbol+' · '+p.account_name+')');link.href=stockDetailLink(p);$('home-health').append(link);if(p.valuation_log_id)$('home-health').append(document.createTextNode(' · Log-ID '+p.valuation_log_id));}if(accessSession?.user?.role==='admin'){const manage=homeNode('a',ui('Koersproblemen en afwikkelingen'));manage.href='#instellingen-koersbeheer';$('home-health').append(homeNode('span',' · '),manage);}}
 else $('home-health').textContent=homeIsCombined()?ui('Alle bekende bedragen omgerekend naar euro. Aankopen, verkopen en dividend tegen de koers op de transactiedatum.'):ui('Bedragen blijven per valuta gescheiden. Koersen kunnen vertraagd zijn; de laatste koerstijd staat bij een geselecteerde positie.');
 if(state.history_date_issues?.length){$('home-health').append(homeNode('p',ui('Er zijn transactiedatums vóór 1900. De grafiek toont deze periode niet. Controleer de oorspronkelijke boekingen.')));const link=homeNode('a',ui('Betrokken transacties controleren'));link.href='#transacties?datum='+encodeURIComponent(state.history_date_issues[0]);$('home-health').append(link);}
 if(homeCurrency==='ALL'&&homeEuro?.excluded.length){$('home-health').append(document.createTextNode(ui(' Niet omgerekend: ')));for(const [i,p] of homeEuro.excluded.entries()){if(i)$('home-health').append(document.createTextNode(' · '));const link=homeNode('a',p.name+' ('+p.currency+' · '+p.account_name+')');link.href=stockDetailLink(p);$('home-health').append(link,document.createTextNode(ui(' · wisselkoers ontbreekt op ')+p.dates.slice(0,3).map(dayLabel).join(', ')));}}
 const cutoff=new Date();
 cutoff.setUTCDate(cutoff.getUTCDate()-5);
 const staleBefore=cutoff.toISOString().slice(0,10);
 for(const p of scope){
  if(Number(p.quantity)<=0||p.value==null)continue;
  const quoteDay=p.quote?.quoted_at?.slice(0,10);
  const oldQuote=quoteDay&&quoteDay<staleBefore&&!p.quote.manual&&!p.quote_paused&&p.exchange!=='PRIVATE';
  const oldFx=p.native_currency&&p.native_currency!=='EUR'&&p.fx_day&&p.fx_day<staleBefore;
  if(!oldQuote&&!oldFx)continue;
  const line=homeNode('p'),link=homeNode('a',p.name+' ('+p.symbol+')');
  link.href=stockDetailLink({...p,currency:p.native_currency||p.currency});
  line.append(link);
  if(oldQuote)line.append(' · '+ui('Verouderde koers')+' ('+dayLabel(quoteDay)+')');
  if(oldFx)line.append(' · '+ui('Verouderde wisselkoers')+' ('+dayLabel(p.fx_day)+')');
  line.append(' · '+ui('Meegerekend in het totaal'));
  $('home-health').append(line);
 }
 if(homeCurrency!=='ALL')$('home-euro-status').textContent='';
 else if(homeEuro&&!homeEuroPending)showHomeEuroStatus(homeEuro);
 if(homeCurrency==='ALL'&&homeEuroError&&!homeEuroPending){
  const message=homeEuroFallback()?ui('Het gecombineerde euro-overzicht is tijdelijk niet beschikbaar. Hieronder staan de posities die in EUR noteren.'):ui('Euro-overzicht laden mislukt. Beschikbare gegevens blijven staan.');
  $('home-euro-status').replaceChildren(document.createTextNode(message));
  if(typeof homeEuroError==='string')$('home-euro-status').append(homeNode('p',homeEuroError));
  const retry=homeNode('button',ui('Opnieuw proberen'),'secondary');retry.type='button';retry.onclick=loadHomeEuro;$('home-euro-status').append(retry);
 }
 const selected=$('instrument');selected.replaceChildren();const add=(value,label)=>{const option=homeNode('option',label);option.value=value;selected.append(option);};add('portfolio:'+homeDisplayCurrency(),ui('Portefeuilletotaal · ')+(homeIsCombined()?ui('alle valuta’s in EUR'):homeDisplayCurrency()));add('all',ui('Vergelijk gekozen posities · maximaal 6'));
 const focus=homeViewState().positions.findIndex(p=>homeKey(p)===homeFocus);if(focus>=0)add(String(focus),homeViewState().positions[focus].name+' · '+homeViewState().positions[focus].account_name);
 selected.value=homeMode==='compare'?'all':homeMode==='position'&&focus>=0?String(focus):'portfolio:'+homeDisplayCurrency();
 renderHomeTable();renderHomeInsights();renderHomeDailyMovers();
}
function homeDailyMovers(positions,currency,day){
 const listings=new Map();
 for(const position of positions){
  if(Number(position.quantity)<=0||currency!=='ALL'&&position.currency!==currency)continue;
  const change=Number(position.daily_moves?.sessions.find(session=>session.day===day)?.percent);
  if(!Number.isFinite(change)||!change)continue;
  const key=JSON.stringify([position.symbol,position.exchange,position.currency]);
  listings.set(key,{position,change});
 }
 const ranked=[...listings.values()].sort((a,b)=>b.change-a.change);
 return {
  gainers:ranked.filter(row=>row.change>0).slice(0,5),
  losers:ranked.filter(row=>row.change<0).reverse().slice(0,5)
 };
}
function homeDailyRankings(positions,currency,today){
 const previousDay=new Date(today+'T00:00:00Z');
 previousDay.setUTCDate(previousDay.getUTCDate()-1);
 const yesterday=previousDay.toISOString().slice(0,10);
 const current=homeDailyMovers(positions,currency,today);
 const previous=homeDailyMovers(positions,currency,yesterday);
 return Object.fromEntries(Object.entries(current).map(([side,rows])=>[
  side,{rows:rows.length?rows:previous[side],fallbackDay:!rows.length&&previous[side].length?yesterday:null}
 ]));
}
function renderHomeDailyMovers(){
 const today=state.settings.demo_day||new Date().toLocaleDateString('en-CA');
 const movers=homeDailyRankings(state.positions,homeCurrency,today);
 for(const [side,{rows,fallbackDay}] of Object.entries(movers)){
  const list=$('home-daily-'+side),notice=$('home-daily-'+side+'-empty');
  list.replaceChildren();
  notice.hidden=rows.length>0&&!fallbackDay;
  notice.textContent=fallbackDay?ui('Koerscijfers van gisteren ({date}).',{date:dayLabel(fallbackDay)}):
   side==='gainers'?ui('Vandaag zijn er geen stijgers met beschikbare koersdata.'):ui('Vandaag zijn er geen dalers met beschikbare koersdata.');
  list.append(...rows.map(({position,change},index)=>stockMoverRow(position,change,index)));
 }
}
function stockMoverRow(position,change,index){
 const row=homeNode('li',undefined,'home-daily-row');
 const mark=homeNode('span',position.name.trim().split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase(),'stock-company-mark');
 mark.setAttribute('aria-hidden','true');
 loadMoverCompanyLogo(mark,position);
 const link=homeNode('a',position.name);
 link.href=stockDetailLink(position);
 const listing=homeNode('div',undefined,'home-daily-listing');
 listing.append(link,homeNode('small',position.exchange+(position.day?' · '+dayLabel(position.day):'')));
 row.append(homeNode('span',index+1),mark,listing,homeNode('strong',homePercent(change),change>0?'positive':'negative'));
 return row;
}
async function loadMoverCompanyLogo(mark,position,minSize=0){
 const local=localCompanyLogo(position.name);
 const domain=local?'':position.logo_domain||position.daily_moves?.domain||await lookupCompanyDomain(position);
 if(!local&&!domain)return;
 const image=homeNode('img');
 image.alt='';
 image.referrerPolicy='no-referrer';
 image.onload=()=>{if(mark.isConnected&&Math.max(image.naturalWidth,image.naturalHeight)>=minSize)mark.replaceChildren(image);};
 image.src=local||companyLogoUrl(domain);
}
function homeChartChanged(){const value=$('instrument').value;homeMode=value==='all'?'compare':value.startsWith('portfolio:')?'overview':'position';if(homeMode==='compare'&&!homeSelected.size)for(const p of homeRows(homeScope(),'','open','value').slice(0,6))homeSelected.add(homeKey(p));renderHomeTable();}
function homeFocusPosition(p){if(typeof dashboardModuleEnabled==='function'&&!dashboardModuleEnabled('chart')){openDashboardEditor();return;}homeFocus=homeKey(p);homeMode='position';renderHomeDashboard();draw();$('home-chart-panel').scrollIntoView({behavior:'smooth',block:'start'});$('instrument').focus({preventScroll:true});}
function homeColumnValues(p,summary){return [homeSelected.has(homeKey(p))?ui('Geselecteerd'):ui('Niet geselecteerd'),p.name+' '+p.symbol+' · '+p.account_name,quantityLabel(p.quantity),money(p.value,p.currency),p.value==null||!summary.value?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:1}).format(Number(p.value)/summary.value*100)+'%',p.total_gain==null?'—':money(p.total_gain,p.currency),homePercent(homeReturn(p)),ui('Bekijken')];}
function renderHomeTable(){
 if(typeof dashboardModuleEnabled==='function'&&!dashboardModuleEnabled('holdings'))return;
 const scope=homeScope(),summary=homeSummary(scope),rows=homeRows(scope,$('home-search').value,$('home-position-filter').value,$('home-sort').value);
 const columnValues=p=>homeColumnValues(p,summary);
 const filtered=typeof tableColumnFilters!=='undefined'&&tableColumnFilters.get('home-positions')?.some(Boolean)
  ?rows.filter(p=>matchesTableColumns('home-positions',columnValues(p))):rows;
 const sorted=typeof sortTableData==='undefined'?filtered:sortTableData('home-positions',filtered,columnValues);
 const pages=Math.max(1,Math.ceil(filtered.length/25));homePage=Math.min(homePage,pages-1);
 $('home-positions').replaceChildren();for(const p of sorted.slice(homePage*25,homePage*25+25)){
  const row=document.createElement('tr'),choice=cell(row,'');const check=document.createElement('input');check.type='checkbox';check.dataset.key=homeKey(p);check.checked=homeSelected.has(homeKey(p));check.setAttribute('aria-label',ui('Vergelijk ')+p.name+ui(' bij ')+p.account_name);check.addEventListener('change',()=>{if(check.checked&&homeSelected.size>=6){check.checked=false;$('home-selection-count').textContent=ui('Maximaal 6 posities tegelijk. Verwijder eerst een positie uit de selectie.');return;}if(check.checked)homeSelected.add(homeKey(p));else homeSelected.delete(homeKey(p));homeMode='compare';$('instrument').value='all';renderHomeTable();draw();[...$('home-positions').querySelectorAll('input[type="checkbox"]')].find(input=>input.dataset.key===homeKey(p))?.focus({preventScroll:true});});choice.append(check);
  const name=cell(row,'');name.append(homeNode('strong',p.name),homeNode('small',p.symbol+' · '+p.account_name+(p.native_currency?ui(' · oorspronkelijk ')+p.native_currency:'')));cell(row,quantityLabel(p.quantity));const value=cell(row,money(p.value,p.currency));value.append(homeNode('small',p.quote?ui('Koers ')+new Date(p.quote.quoted_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')):ui('Geen koerstijd beschikbaar')));
  cell(row,p.value==null||!summary.value?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:1}).format(Number(p.value)/summary.value*100)+'%');cell(row,p.total_gain==null?'—':money(p.total_gain,p.currency)).className=p.total_gain==null?'':Number(p.total_gain)>=0?'positive':'negative';cell(row,homePercent(homeReturn(p))).className=homeReturn(p)==null?'':homeReturn(p)>=0?'positive':'negative';const action=cell(row,'');const button=homeNode('button',ui('Bekijken'),'secondary');button.type='button';button.setAttribute('aria-label',ui('Grafiek van ')+p.name+ui(' bij ')+p.account_name);button.addEventListener('click',()=>homeFocusPosition(p));action.append(button);$('home-positions').append(row);
 }
 $('home-table-note').textContent=filtered.length+ui(' van ')+scope.length+ui(' posities · ')+homeDisplayCurrency()+ui(' · weging op basis van bekende marktwaarde · winst % sinds aankoop');$('home-selection-count').textContent=homeSelected.size+ui(' van 6 posities geselecteerd om te vergelijken');$('home-table-empty').textContent=filtered.length?'':ui('Geen posities gevonden. Pas je zoekopdracht of filter aan.');$('home-page-note').textContent=ui('Pagina ')+(homePage+1)+ui(' van ')+pages+ui(' · 25 per pagina');$('home-prev').disabled=homePage===0;$('home-next').disabled=homePage>=pages-1;
}
function renderHomeInsights(){
 const enabled=id=>typeof dashboardModuleEnabled!=='function'||dashboardModuleEnabled(id);
 const scope=homeScope();
 if(enabled('allocation')){
 const total=homeSummary(scope);$('home-allocation').replaceChildren();$('home-allocation-note').textContent=ui('In ')+homeDisplayCurrency();
 for(const p of homeRows(scope,'','open','value').filter(p=>p.value!=null&&Number(p.value)>0).slice(0,5)){
  const item=homeNode('div',undefined,'home-allocation-item'),heading=homeNode('div',undefined,'home-allocation-label');const button=homeNode('button',p.symbol+' · '+p.name,'home-text-button');button.type='button';button.addEventListener('click',()=>homeFocusPosition(p));const weight=total.value?Number(p.value)/total.value*100:0;heading.append(button,homeNode('span',new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{minimumFractionDigits:1,maximumFractionDigits:1}).format(weight)+'%'));item.append(heading);
  const bar=document.createElementNS('http://www.w3.org/2000/svg','svg');bar.setAttribute('viewBox','0 0 100 5');bar.setAttribute('preserveAspectRatio','none');bar.setAttribute('aria-hidden','true');for(const [width,fill] of [[100,'#26344b'],[Math.max(0,Math.min(100,weight)),'#47dcb0']]){const rect=document.createElementNS(bar.namespaceURI,'rect');rect.setAttribute('width',width);rect.setAttribute('height','5');rect.setAttribute('rx','2');rect.setAttribute('fill',fill);bar.append(rect);}item.append(bar);$('home-allocation').append(item);
 }
 if(!$('home-allocation').children.length)$('home-allocation').append(homeNode('p',ui('Nog geen marktwaarden beschikbaar.')));
 }
 if(!enabled('movers'))return;
 const list=$('home-movers'), daily=chartRange==='1D', best=$('home-ranking').value==='best';
 list.previousElementSibling.textContent=daily?ui('Koersverschil ten opzichte van de vorige beschikbare slotkoers, in de noteringsvaluta.'):ui('Winst sinds aankoop als % van de totale inleg, inclusief dividend. Geen rendement over de gekozen grafiekperiode.');
 list.replaceChildren();
 const open=homeRows(scope,'','open',best?'return':'loss');
 const day=open.flatMap(p=>p.daily_moves?.sessions.map(session=>session.day)||[]).sort().at(-1);
 const rows=daily?open.map(p=>({p,change:p.daily_moves?.sessions.find(session=>session.day===day)?.percent})).filter(row=>row.change!=null&&Number.isFinite(Number(row.change))).sort((a,b)=>best?b.change-a.change:a.change-b.change):open.map(p=>({p,change:homeReturn(p)})).filter(row=>row.change!=null);
 for(const {p,change} of rows.slice(0,5)){
  const row=homeNode('a',undefined,'home-mover');
  row.href=stockDetailLink(p,daily?day:undefined);
  const title=homeNode('div');
  title.append(homeNode('span',p.name),homeNode('small',[p.symbol,p.account_name,daily?dayLabel(day):p.native_currency].filter(Boolean).join(' · ')));
  row.append(title,homeNode('strong',homePercent(Number(change)),change>=0?'positive':'negative'));
  list.append(row);
 }
 if(!list.children.length)list.append(homeNode('p',ui('Nog geen resultaten beschikbaar.')));
}
function bindHomeDashboard(){
 for(const id of ['home-search','home-position-filter','home-sort'])$(id).addEventListener(id==='home-search'?'input':'change',()=>{if(id==='home-sort')clearTableSort('home-positions');homePage=0;renderHomeTable();});$('home-ranking').addEventListener('change',renderHomeInsights);$('home-prev').addEventListener('click',()=>{homePage--;renderHomeTable();});$('home-next').addEventListener('click',()=>{homePage++;renderHomeTable();});$('home-clear-selection').addEventListener('click',()=>{homeSelected.clear();homeMode='overview';renderHomeDashboard();draw();});
}
if(typeof module!=='undefined')module.exports={homeKey,homeReturn,homeSummary,homeRows,homeDailyMovers,homeDailyRankings};

function homeDividendLabel(positions){
 const invested=positions.reduce((sum,p)=>sum+Number(p.history?.at(-1)?.invested??p.cost),0),received=positions.reduce((sum,p)=>sum+Number(p.dividend),0);
 return invested>0?new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:2}).format(received/invested*100)+ui('% van de totale inleg sinds de eerste aankoop'):ui('Dividend gekoppeld aan deze posities');
}

async function loadHomeEuro(){
 if(!state||!accessSession?.user||homeEuroPending)return;
 const source=state,account=String(currentBroker),request=++homeEuroRequest,controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),60000);
 const current=()=>request===homeEuroRequest&&accessSession?.user&&account===String(currentBroker)&&state;
 homeEuroPending=true;homeEuroAccount=account;
 $('home-euro-status').textContent=ui('Opgeslagen euro-overzicht laden; wisselkoersen worden op de achtergrond bijgewerkt…');
 try{
  const response=await apiFetch('api/home/euro?account_id='+encodeURIComponent(account)+'&compact=1',{signal:controller.signal,background:true});
  const data=await response.json();
  if(!current()||(state.data_revision!==source.data_revision&&(!response.ok||data.data_revision!==state.data_revision)))return;
  homeEuroSource=state;
  if(!response.ok){
   homeEuroError=[data.error,data.log_id?'Log-ID '+data.log_id:''].filter(Boolean).join(' · ')||true;
   return;
  }
  if(homeEuro?.data_revision===data.data_revision&&homeEuro.as_of===data.as_of&&homeEuro.chart_status==='ready'){
   data.portfolios=homeEuro.portfolios;data.chart_excluded=homeEuro.chart_excluded;data.chart_status='ready';
  }
  homeEuro=data;homeEuroError=false;showHomeEuroStatus(data);
 }catch{
  if(current()&&state.data_revision===source.data_revision){homeEuroSource=state;homeEuroError=controller.signal.aborted?ui('Het euro-overzicht duurde te lang om te laden.'):true;}
 }finally{
  clearTimeout(timer);
  if(request===homeEuroRequest){homeEuroPending=false;if(homeCurrency==='ALL'&&document.body.classList.contains('home-page')){renderHomeDashboard();draw();}}
 }
}

async function loadHomeEuroChart(){
 if(!homeEuro||homeEuroChartPending||homeEuro.chart_status!=='pending'||!accessSession?.user)return;
 const target=homeEuro,account=String(currentBroker),controller=new AbortController();homeEuroChartController=controller;homeEuroChartPending=true;target.chart_status='loading';const timer=setTimeout(()=>controller.abort(),60000);
 try{
  const response=await apiFetch('api/home/euro/history?account_id='+encodeURIComponent(account),{signal:controller.signal,background:true});
  const data=await response.json();
  if(target!==homeEuro||account!==String(currentBroker)||!accessSession?.user)return;
  const changed=response.status===409||(response.ok&&(data.data_revision!==target.data_revision||(data.as_of&&data.as_of!==target.as_of)));
  if(changed){
   target.chart_error=ui('De portefeuille is gewijzigd. Vernieuw het overzicht.');
   target.chart_status='error';
   if(homeEuroChartRefreshes++===0){
    stateETag=null;await load();
    if(target===homeEuro&&!homeEuroPending&&accessSession?.user&&account===String(currentBroker))await loadHomeEuro();
   }
   return;
  }
  if(!response.ok){
   target.chart_error=[data.error,data.log_id?'Log-ID '+data.log_id:''].filter(Boolean).join(' · ');
   target.chart_status='error';return;
  }
  target.portfolios=data.portfolios;target.chart_excluded=data.excluded;target.chart_status='ready';homeEuroChartRefreshes=0;
 }catch{
  if(target===homeEuro&&accessSession?.user){
   target.chart_error=controller.signal.aborted?ui('De koershistorie duurde te lang om te laden.'):ui('De koershistorie is niet beschikbaar door een verbindingsprobleem.');
   target.chart_status='error';
  }
 }
 finally{clearTimeout(timer);if(homeEuroChartController===controller){homeEuroChartController=null;homeEuroChartPending=false;if(homeCurrency==='ALL'&&document.body.classList.contains('home-page'))draw();}}
}
function showHomeEuroChartProgress(loadHistory=true){
 if(!homeEuro){if(homeEuroPending)$('chartnote').textContent=ui('Euro-totalen worden geladen…');return;}
 if(homeEuro.chart_status==='pending'){
  if(loadHistory)loadHomeEuroChart();
 }
 if(homeEuro.chart_status==='loading')$('chartnote').textContent=ui('Totalen geladen. De historische grafiek wordt op de achtergrond berekend…');
 if(homeEuro.chart_status==='error'){
  $('chartnote').replaceChildren(document.createTextNode(ui('Grafiek laden mislukt. De totalen blijven beschikbaar.')));
  if(homeEuro.chart_error)$('chartnote').append(homeNode('p',homeEuro.chart_error));
  const retry=homeNode('button',ui('Grafiek opnieuw laden'),'secondary');retry.type='button';
  retry.onclick=()=>{homeEuroChartRefreshes=0;homeEuro.chart_status='pending';draw();};
  $('chartnote').append(retry);
 }
 if(homeEuro.chart_status==='ready'&&homeEuro.chart_excluded?.length){
  const details=homeNode('details');
  details.append(homeNode('summary',ui('Posities overgeslagen in de grafiek')+' · '+homeEuro.chart_excluded.length));
  const list=homeNode('ul');
  for(const row of homeEuro.chart_excluded){
   const item=homeNode('li'),link=homeNode('a',row.name||row.symbol);link.href=stockDetailLink(row);
   item.append(link,document.createTextNode(' · '+[row.symbol,row.account_name,row.currency,ui(row.reason),...row.dates.map(dayLabel)].filter(Boolean).join(' · ')));
   list.append(item);
  }
  details.append(list);$('chartnote').append(details);
 }
}

let homeHistoryPending=new Set();
async function loadHomePositionHistory(members){
 const source=state,view=homeViewState(),account=String(currentBroker),combined=homeIsCombined();
 const missing=members.filter(p=>p.history_loaded===false);
 const key=JSON.stringify([stateRequest,source.data_revision,account,combined,missing.map(homeKey)]);
 if(!missing.length||homeHistoryPending.has(key))return;
 homeHistoryPending.add(key);$('chartnote').textContent=ui('Opgeslagen koershistorie laden…');
 const selections=missing.map(p=>({account_id:p.account_id,symbol:p.symbol,exchange:p.exchange,currency:p.native_currency??p.currency}));
 try{
  const response=await apiFetch('api/home/history?account_id='+encodeURIComponent(account)+'&combined='+(combined?'1':'0')+'&positions='+encodeURIComponent(JSON.stringify(selections)));
  const result=await response.json();if(!response.ok)throw Error();
  if(state!==source||!accessSession?.user||account!==String(currentBroker))return;
  if(result.data_revision!==(combined?homeEuro?.data_revision:source.data_revision)){stateETag=null;await load();return;}
  for(const record of result.histories){const position=view.positions.find(p=>homeKey(p)===homeKey(record));if(position){position.history=record.history;position.history_loaded=true;}}
  draw();
 }catch{if(state===source&&accessSession?.user)$('chartnote').textContent=ui('Historie laden mislukt. Selecteer de positie opnieuw om te proberen.');}
 finally{homeHistoryPending.delete(key);}
}

function showHomeEuroStatus(data){const dates=data.fx_dates.map(row=>row.rate_on).sort();$('home-euro-status').textContent=data.positions.length+ui(' posities omgerekend')+(data.excluded.length?' · '+data.excluded.length+ui(' overgeslagen wegens ontbrekende wisselkoersen'):'')+ui('. Marktwaarde tegen beschikbare wisselkoersen tot ')+(dates.length?dayLabel(dates.at(-1)):dayLabel(data.as_of))+ui('. Historische grafiek: bekende waarden per dag; ontbrekende omrekeningen kunnen gaten geven.');}
