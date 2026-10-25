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
let homeCurrency='',homePage=0,homeMode='overview',homeFocus='',homeSelected=new Set();
let homeEuro=null,homeEuroSource=null,homeEuroRequest=0,homeEuroPending=false,homeEuroAccount='';
const homeDisplayCurrency=()=>homeCurrency==='ALL'?'EUR':homeCurrency;
const homeViewState=()=>homeCurrency==='ALL'?{...state,positions:homeEuro?.positions??[],portfolios:homeEuro?.portfolios??[]}:state;
const homeScope=()=>homeCurrency==='ALL'?(homeEuro?.positions??[]):state?.positions.filter(p=>p.currency===homeCurrency)??[];
function homeChartMembers(){return homeScope().filter(p=>homeSelected.has(homeKey(p))).slice(0,6);}
function clearHomeDashboard(){homeHistoryPending.clear();homeEuroRequest++;homeEuroPending=false;homeEuro=null;homeEuroSource=null;homeEuroAccount='';$('home-euro-status').textContent='';homeCurrency='';homePage=0;homeMode='overview';homeFocus='';homeSelected.clear();for(const id of ['home-currencies','home-positions','home-allocation','home-movers'])$(id).replaceChildren();for(const id of ['home-summary','home-health','home-table-note','home-selection-count','home-page-note','home-table-empty','home-allocation-note'])$(id).textContent='';$('home-search').value='';$('home-position-filter').value='open';$('home-sort').value='value';$('home-ranking').value='best';$('chart').onpointermove=null;$('chart').onpointerleave=null;$('chart').onkeydown=null;$('chart-day-details').ontoggle=null;$('chart-days-more').onclick=null;$('chart-day-details').open=false;$('chart-days-note').textContent='';$('instrument').replaceChildren();$('chart-legend').replaceChildren();$('chartnote').textContent='';$('chart-detail').textContent='';}
function homeNode(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function homePercent(value){return value==null?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(value)+'%';}
function homeMetric(label,value,detail,tone){const box=homeNode('article',undefined,'home-metric');box.append(homeNode('span',label,'home-metric-label'),homeNode('strong',value,tone??''),homeNode('small',detail));$('totals').append(box);}
function renderHomeDashboard(){
 if(!state)return;const currencies=[...new Set(state.positions.map(p=>p.currency))].sort();if(homeEuroAccount&&homeEuroAccount!==String(currentBroker)){homeEuro=null;homeEuroSource=null;homeEuroAccount='';homeEuroRequest++;homeEuroPending=false;}if(homeCurrency!=='ALL'&&!currencies.includes(homeCurrency))homeCurrency=currencies.includes('EUR')?'EUR':currencies[0]??'EUR';
 if(homeCurrency==='ALL'&&homeEuroSource!==state&&!homeEuroPending)loadHomeEuro();
 const keys=new Set(homeViewState().positions.map(homeKey));homeSelected=new Set([...homeSelected].filter(key=>keys.has(key)));
 $('home-currencies').replaceChildren();for(const currency of ['ALL',...currencies]){const count=state.positions.filter(p=>(currency==='ALL'||p.currency===currency)&&Number(p.quantity)>0).length;const button=homeNode('button',currency==='ALL'?ui('Alle valuta’s in euro'):currency+' · '+count+ui(' posities'));button.type='button';button.setAttribute('aria-pressed',String(currency===homeCurrency));button.addEventListener('click',()=>{homeCurrency=currency;homePage=0;homeMode='overview';homeFocus='';homeSelected.clear();renderHomeDashboard();draw();$('home-currencies').querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});});$('home-currencies').append(button);}
 const scope=homeScope(),summary=homeSummary(scope);$('home-summary').textContent=state.positions.length?state.positions.filter(p=>Number(p.quantity)>0).length+ui(' open posities · ')+currencies.length+ui(' valuta · ')+(homeCurrency==='ALL'?ui('totaal omgerekend naar EUR'):ui('overzicht in ')+homeCurrency):ui('Voeg een aankoop toe of importeer je portefeuille om te beginnen.');
 $('totals').replaceChildren();homeMetric(ui('Marktwaarde'),money(summary.value,homeDisplayCurrency()),summary.missing?ui('Bekende waarde · ')+summary.missing+ui(' posities zonder koers'):ui('Alle posities in ')+homeDisplayCurrency()+ui(' met beschikbare koers'));homeMetric(ui('Openstaande kostprijs'),money(summary.cost,homeDisplayCurrency()),summary.open+(homeCurrency==='ALL'?ui(' omgerekende open posities'):ui(' open posities in deze valuta')));homeMetric(ui('Totale winst'),money(summary.gain,homeDisplayCurrency()),summary.missing?ui('Bekende posities · ')+summary.missing+ui(' zonder koers overgeslagen'):ui('Inclusief gerealiseerde winst en gekoppeld dividend'),summary.gain>=0?'positive':'negative');homeMetric(ui('Ontvangen dividend'),money(summary.dividend,homeDisplayCurrency()),homeDividendLabel(scope));
 const missing=state.positions.filter(p=>p.value==null);$('home-health').replaceChildren();
 if(missing.length){$('home-health').append(homeNode('strong',ui('Zonder koers, overgeslagen bij de bekende totalen: ')));for(const [index,p] of missing.entries()){if(index)$('home-health').append(document.createTextNode(' · '));const link=homeNode('a',p.name+' ('+p.symbol+' · '+p.account_name+')');link.href=stockDetailLink(p);$('home-health').append(link);if(p.valuation_log_id)$('home-health').append(document.createTextNode(' · Log-ID '+p.valuation_log_id));}}
 else $('home-health').textContent=homeCurrency==='ALL'?ui('Alle bekende bedragen omgerekend naar euro. Aankopen, verkopen en dividend tegen de koers op de transactiedatum.'):ui('Bedragen blijven per valuta gescheiden. Koersen kunnen vertraagd zijn; de laatste koerstijd staat bij een geselecteerde positie.');
 if(homeCurrency==='ALL'&&homeEuro?.excluded.length){$('home-health').append(document.createTextNode(ui(' Niet omgerekend: ')));for(const [i,p] of homeEuro.excluded.entries()){if(i)$('home-health').append(document.createTextNode(' · '));const link=homeNode('a',p.name+' ('+p.currency+' · '+p.account_name+')');link.href=stockDetailLink(p);$('home-health').append(link,document.createTextNode(ui(' · wisselkoers ontbreekt op ')+p.dates.slice(0,3).map(dayLabel).join(', ')));}}
 if(homeCurrency==='ALL'&&!homeEuro)for(const box of $('totals').children)box.querySelector('strong').textContent=homeEuroPending?ui('Laden…'):ui('Niet beschikbaar');
 if(homeCurrency!=='ALL')$('home-euro-status').textContent='';
 else if(homeEuro&&!homeEuroPending)showHomeEuroStatus(homeEuro);
 const selected=$('instrument');selected.replaceChildren();const add=(value,label)=>{const option=homeNode('option',label);option.value=value;selected.append(option);};add('portfolio:'+homeDisplayCurrency(),ui('Portefeuilletotaal · ')+(homeCurrency==='ALL'?ui('alle valuta’s in EUR'):homeCurrency));add('all',ui('Vergelijk gekozen posities · maximaal 6'));
 const focus=homeViewState().positions.findIndex(p=>homeKey(p)===homeFocus);if(focus>=0)add(String(focus),homeViewState().positions[focus].name+' · '+homeViewState().positions[focus].account_name);
 selected.value=homeMode==='compare'?'all':homeMode==='position'&&focus>=0?String(focus):'portfolio:'+homeDisplayCurrency();
 renderHomeTable();renderHomeInsights();
}
function homeChartChanged(){const value=$('instrument').value;homeMode=value==='all'?'compare':value.startsWith('portfolio:')?'overview':'position';if(homeMode==='compare'&&!homeSelected.size)for(const p of homeRows(homeScope(),'','open','value').slice(0,6))homeSelected.add(homeKey(p));renderHomeTable();}
function homeFocusPosition(p){homeFocus=homeKey(p);homeMode='position';renderHomeDashboard();draw();$('home-chart-panel').scrollIntoView({behavior:'smooth',block:'start'});$('instrument').focus({preventScroll:true});}
function homeColumnValues(p,summary){return [homeSelected.has(homeKey(p))?ui('Geselecteerd'):ui('Niet geselecteerd'),p.name+' '+p.symbol+' · '+p.account_name,quantityLabel(p.quantity),money(p.value,p.currency),p.value==null||!summary.value?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:1}).format(Number(p.value)/summary.value*100)+'%',p.total_gain==null?'—':money(p.total_gain,p.currency),homePercent(homeReturn(p)),ui('Bekijken')];}
function renderHomeTable(){
 const scope=homeScope(),summary=homeSummary(scope),rows=homeRows(scope,$('home-search').value,$('home-position-filter').value,$('home-sort').value).filter(p=>typeof matchesTableColumns==='undefined'||matchesTableColumns('home-positions',homeColumnValues(p,summary)));const sorted=typeof sortTableData==='undefined'?rows:sortTableData('home-positions',rows,p=>homeColumnValues(p,summary)),pages=Math.max(1,Math.ceil(rows.length/25));homePage=Math.min(homePage,pages-1);
 $('home-positions').replaceChildren();for(const p of sorted.slice(homePage*25,homePage*25+25)){
  const row=document.createElement('tr'),choice=cell(row,'');const check=document.createElement('input');check.type='checkbox';check.dataset.key=homeKey(p);check.checked=homeSelected.has(homeKey(p));check.setAttribute('aria-label',ui('Vergelijk ')+p.name+ui(' bij ')+p.account_name);check.addEventListener('change',()=>{if(check.checked&&homeSelected.size>=6){check.checked=false;$('home-selection-count').textContent=ui('Maximaal 6 posities tegelijk. Verwijder eerst een positie uit de selectie.');return;}if(check.checked)homeSelected.add(homeKey(p));else homeSelected.delete(homeKey(p));homeMode='compare';$('instrument').value='all';renderHomeTable();draw();[...$('home-positions').querySelectorAll('input[type="checkbox"]')].find(input=>input.dataset.key===homeKey(p))?.focus({preventScroll:true});});choice.append(check);
  const name=cell(row,'');name.append(homeNode('strong',p.name),homeNode('small',p.symbol+' · '+p.account_name+(p.native_currency?ui(' · oorspronkelijk ')+p.native_currency:'')));cell(row,quantityLabel(p.quantity));const value=cell(row,money(p.value,p.currency));value.append(homeNode('small',p.quote?ui('Koers ')+new Date(p.quote.quoted_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')):ui('Geen koerstijd beschikbaar')));
  cell(row,p.value==null||!summary.value?'—':new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:1}).format(Number(p.value)/summary.value*100)+'%');cell(row,p.total_gain==null?'—':money(p.total_gain,p.currency)).className=p.total_gain==null?'':Number(p.total_gain)>=0?'positive':'negative';cell(row,homePercent(homeReturn(p))).className=homeReturn(p)==null?'':homeReturn(p)>=0?'positive':'negative';const action=cell(row,'');const button=homeNode('button',ui('Bekijken'),'secondary');button.type='button';button.setAttribute('aria-label',ui('Grafiek van ')+p.name+ui(' bij ')+p.account_name);button.addEventListener('click',()=>homeFocusPosition(p));action.append(button);$('home-positions').append(row);
 }
 $('home-table-note').textContent=rows.length+ui(' van ')+scope.length+ui(' posities · ')+homeDisplayCurrency()+ui(' · weging op basis van bekende marktwaarde · winst % sinds aankoop');$('home-selection-count').textContent=homeSelected.size+ui(' van 6 posities geselecteerd om te vergelijken');$('home-table-empty').textContent=rows.length?'':ui('Geen posities gevonden. Pas je zoekopdracht of filter aan.');$('home-page-note').textContent=ui('Pagina ')+(homePage+1)+ui(' van ')+pages+ui(' · 25 per pagina');$('home-prev').disabled=homePage===0;$('home-next').disabled=homePage>=pages-1;
}
function renderHomeInsights(){
 const scope=homeScope(),total=homeSummary(scope);$('home-allocation').replaceChildren();$('home-allocation-note').textContent=ui('In ')+homeDisplayCurrency();
 for(const p of homeRows(scope,'','open','value').filter(p=>p.value!=null&&Number(p.value)>0).slice(0,5)){
  const item=homeNode('div',undefined,'home-allocation-item'),heading=homeNode('div',undefined,'home-allocation-label');const button=homeNode('button',p.symbol+' · '+p.name,'home-text-button');button.type='button';button.addEventListener('click',()=>homeFocusPosition(p));const weight=total.value?Number(p.value)/total.value*100:0;heading.append(button,homeNode('span',new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{minimumFractionDigits:1,maximumFractionDigits:1}).format(weight)+'%'));item.append(heading);
  const bar=document.createElementNS('http://www.w3.org/2000/svg','svg');bar.setAttribute('viewBox','0 0 100 5');bar.setAttribute('preserveAspectRatio','none');bar.setAttribute('aria-hidden','true');for(const [width,fill] of [[100,'#26344b'],[Math.max(0,Math.min(100,weight)),'#47dcb0']]){const rect=document.createElementNS(bar.namespaceURI,'rect');rect.setAttribute('width',width);rect.setAttribute('height','5');rect.setAttribute('rx','2');rect.setAttribute('fill',fill);bar.append(rect);}item.append(bar);$('home-allocation').append(item);
 }
 if(!$('home-allocation').children.length)$('home-allocation').append(homeNode('p',ui('Nog geen marktwaarden beschikbaar.')));
 $('home-movers').replaceChildren();for(const p of homeRows(scope,'','open',$('home-ranking').value==='best'?'return':'loss').filter(p=>homeReturn(p)!=null).slice(0,5)){const row=homeNode('div',undefined,'home-mover');const button=homeNode('button',p.name,'home-text-button');button.type='button';button.addEventListener('click',()=>homeFocusPosition(p));const title=homeNode('div');title.append(button,homeNode('small',p.symbol+' · '+p.account_name+(p.native_currency?ui(' · oorspronkelijk ')+p.native_currency:'')));row.append(title,homeNode('strong',homePercent(homeReturn(p)),homeReturn(p)>=0?'positive':'negative'));$('home-movers').append(row);}if(!$('home-movers').children.length)$('home-movers').append(homeNode('p',ui('Nog geen resultaten beschikbaar.')));
}
function bindHomeDashboard(){
 for(const id of ['home-search','home-position-filter','home-sort'])$(id).addEventListener(id==='home-search'?'input':'change',()=>{if(id==='home-sort')clearTableSort('home-positions');homePage=0;renderHomeTable();});$('home-ranking').addEventListener('change',renderHomeInsights);$('home-prev').addEventListener('click',()=>{homePage--;renderHomeTable();});$('home-next').addEventListener('click',()=>{homePage++;renderHomeTable();});$('home-clear-selection').addEventListener('click',()=>{homeSelected.clear();homeMode='overview';renderHomeDashboard();draw();});
}
if(typeof module!=='undefined')module.exports={homeKey,homeReturn,homeSummary,homeRows};

function homeDividendLabel(positions){
 const invested=positions.reduce((sum,p)=>sum+Number(p.history?.at(-1)?.invested??p.cost),0),received=positions.reduce((sum,p)=>sum+Number(p.dividend),0);
 return invested>0?new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:2}).format(received/invested*100)+ui('% van de totale inleg sinds de eerste aankoop'):ui('Dividend gekoppeld aan deze posities');
}

async function loadHomeEuro(){
 if(!state||!accessSession?.user)return;const source=state,account=String(currentBroker),request=++homeEuroRequest;homeEuroPending=true;homeEuroAccount=account;$('home-euro-status').textContent=ui('Opgeslagen euro-overzicht laden; wisselkoersen worden op de achtergrond bijgewerkt…');
 try{const response=await apiFetch('api/home/euro?account_id='+encodeURIComponent(account)+'&compact=1');const data=await response.json();if(request!==homeEuroRequest||!accessSession?.user||account!==String(currentBroker))return;if(!response.ok)throw Error();if(state!==source)return;
 homeEuro=data;homeEuroSource=source;showHomeEuroStatus(data);
 }catch{if(request===homeEuroRequest){homeEuroSource=source;$('home-euro-status').textContent=ui('Het totaal in euro kon niet worden geladen. Kies een valuta of probeer het opnieuw.');}}
 finally{if(request===homeEuroRequest){homeEuroPending=false;if(homeCurrency==='ALL'&&document.body.classList.contains('home-page')){renderHomeDashboard();draw();}}}
}

let homeHistoryPending=new Set();
async function loadHomePositionHistory(members){
 const source=state,view=homeViewState(),account=String(currentBroker),combined=homeCurrency==='ALL';
 const missing=members.filter(p=>p.history_loaded===false);
 const key=JSON.stringify([stateRequest,source.data_revision,account,combined,missing.map(homeKey)]);
 if(!missing.length||homeHistoryPending.has(key))return;
 homeHistoryPending.add(key);$('chartnote').textContent=ui('Opgeslagen koershistorie laden…');
 const selections=missing.map(p=>({account_id:p.account_id,symbol:p.symbol,exchange:p.exchange,currency:p.native_currency??p.currency}));
 try{
  const response=await apiFetch('api/home/history?account_id='+encodeURIComponent(account)+'&combined='+(combined?'1':'0')+'&positions='+encodeURIComponent(JSON.stringify(selections)));
  const result=await response.json();if(!response.ok)throw Error();
  if(state!==source||!accessSession?.user||account!==String(currentBroker))return;
  if(result.data_revision!==source.data_revision){stateETag=null;await load();return;}
  for(const record of result.histories){const position=view.positions.find(p=>homeKey(p)===homeKey(record));if(position){position.history=record.history;position.history_loaded=true;}}
  draw();
 }catch{if(state===source&&accessSession?.user)$('chartnote').textContent=ui('Historie laden mislukt. Selecteer de positie opnieuw om te proberen.');}
 finally{homeHistoryPending.delete(key);}
}

function showHomeEuroStatus(data){const dates=data.fx_dates.map(row=>row.rate_on).sort();$('home-euro-status').textContent=data.positions.length+ui(' posities omgerekend')+(data.excluded.length?' · '+data.excluded.length+ui(' overgeslagen wegens ontbrekende wisselkoersen'):'')+ui('. Marktwaarde tegen beschikbare wisselkoersen tot ')+(dates.length?dayLabel(dates.at(-1)):dayLabel(data.as_of))+ui('. Historische grafiek: bekende waarden per dag; ontbrekende omrekeningen kunnen gaten geven.');}
