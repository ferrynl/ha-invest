/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
/* Listing-level portfolio presentation, shared across broker accounts. */
let stocksData=null,stocksGeneration=0;
function clearStocksDashboard(){clearStockSector();clearStockMovers();stocksGeneration++;stocksData=null;for(const id of ['stocks-metrics','stocks-sectors','stocks-countries','stocks-types','positions'])$(id).replaceChildren();$('stocks-feedback').textContent='';}
async function loadStocksDashboard(){
 if(!state||!accessSession?.user)return;const request=++stocksGeneration,account=String(currentBroker);if(!stocksData)$('stocks-feedback').textContent=ui('Alle aandelen laden…');
 try{const response=await apiFetch('api/stocks?account_id='+encodeURIComponent(account));const data=await response.json();if(request!==stocksGeneration||account!==String(currentBroker)||!accessSession?.user)return;if(!response.ok)throw Error();stocksData=data;$('stocks-feedback').textContent='';renderStocksRows();renderStockComposition();refreshCategoryOverview(true);}
 catch{if(request===stocksGeneration)$('stocks-feedback').textContent=ui('Aandelen laden mislukt. Open de pagina opnieuw om het nog eens te proberen.');}
}
function renderStocksRows(){
 $('positions').replaceChildren();for(const p of stocksData.positions){const row=document.createElement('tr');row.dataset.categoryKey=categoryKey(p);const title=cell(row,''),link=document.createElement('a');link.href=stockDetailLink(p);link.className='stock-name-link';link.textContent=p.name;const subtitle=document.createElement('small');subtitle.textContent=p.exchange+' · '+p.symbol+' · '+p.currency;title.append(link,subtitle);const metadata=categoryForPosition(p);for(const field of ['sector','country','asset_type','category']){const fieldCell=cell(row,categoryFieldLabel(metadata.categories,metadata.sync,field));fieldCell.dataset.categoryField=field;if(field==='sector')renderStockSectorField(fieldCell,fieldCell.textContent,metadata.categories.sector);}
 for(const value of [quantityLabel(p.quantity),money(p.cost,p.currency),p.quote?money(p.quote.price,p.currency):'—',money(p.value,p.currency),p.gain==null?'—':money(p.gain,p.currency),money(p.dividend,p.currency),p.total_gain==null?'—':money(p.total_gain,p.currency),p.quote?new Date(p.quote.quoted_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')):ui('Wacht op koers')])cell(row,value);$('positions').append(row);}
 $('empty').textContent=stocksData.positions.length?'':ui('Voeg je eerste aankoop toe of importeer je portefeuille.');
}
function updateStocksCategories(entries){if(!stocksData)return;const map=new Map(entries.map(p=>[categoryKey(p),p.categories]));for(const p of stocksData.positions)if(map.has(categoryKey(p)))p.categories=map.get(categoryKey(p));renderStockComposition();}
function stockDistribution(positions,field){const groups=new Map();for(const p of positions){if(Number(p.quantity)<=0)continue;const label=p.categories?.[field]||ui('Niet ingedeeld');groups.set(label,(groups.get(label)||0)+1);}return [...groups].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'nl'));}
function renderStockComposition(){
 if(!stocksData)return;const positions=stocksData.positions,open=positions.filter(p=>Number(p.quantity)>0),sectors=new Set(open.map(p=>p.categories?.sector).filter(Boolean)),countries=new Set(open.map(p=>p.categories?.country).filter(Boolean));$('stocks-metrics').replaceChildren();for(const [label,value,note] of [[ui('Unieke beursnoteringen'),positions.length,stocksData.accounts+ui(' brokeraccounts samen')],[ui('Open posities'),open.length,ui('Aantallen binnen je brokerkeuze')],[ui('Sectoren'),sectors.size,ui('Bekende sectoren in open posities')],[ui('Landen'),countries.size,ui('Bekende landen in open posities')]]){const box=homeNode('article',undefined,'home-metric');box.append(homeNode('span',label,'home-metric-label'),homeNode('strong',String(value)),homeNode('small',note));$('stocks-metrics').append(box);}
 renderStockSectors($('stocks-sectors'),stockDistribution(positions,'sector'));
 drawStockDonut($('stocks-types'),stockDistribution(positions,'asset_type'));
 const target=$('stocks-countries');target.replaceChildren();const plot=homeNode('div'),detail=homeNode('p',undefined,'report-chart-note');target.append(plot,detail);
 renderCountryMap({plot,detail},stockDistribution(positions,'country').map(([name,value])=>({name,value})),'','stocks-listings',{count:true});
}
function drawStockDonut(target,groups){
 target.replaceChildren();const total=groups.reduce((sum,p)=>sum+p[1],0);if(!total){target.append(homeNode('p',ui('Nog geen open posities.'),'home-muted'));return;}
 const displayed=groups.length>6?[...groups.slice(0,5),[ui('Overige'),groups.slice(5).reduce((sum,p)=>sum+p[1],0)]]:groups,palette=['#47dcb0','#70b7ff','#c1a1ff','#ffcf87','#79d7df','#8b9bb2'];const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 200 180');svg.setAttribute('role','img');svg.setAttribute('aria-label',groups.map(([label,count])=>label+': '+count).join(', '));let start=0;
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 node('circle',{cx:100,cy:85,r:62,fill:'none',stroke:'#27384d','stroke-width':24});for(const [i,[label,count]] of displayed.entries()){const fraction=count/total,length=2*Math.PI*62;const circle=node('circle',{cx:100,cy:85,r:62,fill:'none',stroke:palette[i],'stroke-width':24,'stroke-dasharray':(fraction*length)+' '+length,'stroke-dashoffset':-start*length,transform:'rotate(-90 100 85)'});const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=label+' · '+count+' · '+Math.round(fraction*100)+'%';circle.append(title);start+=fraction;}
 node('text',{x:100,y:84,'text-anchor':'middle',fill:'#edf4ff','font-size':30,'font-weight':700},String(total));node('text',{x:100,y:106,'text-anchor':'middle',fill:'#91a4bf','font-size':11},ui('open noteringen'));target.append(svg);const legend=homeNode('div',undefined,'stock-chart-legend');for(const [i,[label,count]] of displayed.entries()){const row=homeNode('div',undefined,'stock-chart-item'),mark=document.createElementNS(svg.namespaceURI,'svg');mark.setAttribute('viewBox','0 0 12 12');const rect=document.createElementNS(svg.namespaceURI,'rect');rect.setAttribute('width','12');rect.setAttribute('height','12');rect.setAttribute('rx','3');rect.setAttribute('fill',palette[i]);mark.append(rect);row.append(mark,homeNode('span',label),homeNode('strong',new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:1}).format(count/total*100)+'%'));legend.append(row);}target.append(legend);
}

// Sector symbols are local vector artwork; source category names remain unchanged.
const stockSectorThemes=[
 {aliases:['technology','technologie','tecnologia'],icon:'M8 8h16v16H8z M12 12h8v8h-8z M12 3v5m8-5v5m-8 16v5m8-5v5M3 12h5m-5 8h5m16-8h5m-5 8h5',info:()=>ui("Vraag naar chips, software en cloudcapaciteit, productcycli en waarderingen spelen vaak een grote rol."),note:ui('Software, chips en digitale innovatie'),color:'#79bcff'},
 {aliases:['healthcare','health care','gezondheidszorg','salud'],icon:'M16 27S3 19 3 11a7 7 0 0 1 13-3 7 7 0 0 1 13 3c0 8-13 16-13 16z M8 16h5l2-5 3 10 2-5h5',info:()=>ui("Onderzoeksresultaten, toelatingen van medicijnen en zorguitgaven beïnvloeden deze sector."),note:ui('Medicijnen, zorg en medische technologie'),color:'#f79ac2'},
 {aliases:['financial services','financials','financiele diensten','financien','servicios financieros'],icon:'M3 11l13-8 13 8H3z M5 27h22M8 14v10m8-10v10m8-10v10',info:()=>ui("Rente, kredietverliezen en regelgeving beïnvloeden de inkomsten van financiële bedrijven."),note:ui('Banken, verzekeringen en betalingsverkeer'),color:'#dbb1ff'},
 {aliases:['energy','energie','energia'],icon:'M18 2L6 18h9l-1 12 12-18h-9z',info:()=>ui("Grondstofprijzen, productievolumes en investeringen in energie-infrastructuur zijn belangrijke factoren."),note:ui('Olie, gas en energieproductie'),color:'#ffce79'},
 {aliases:['industrials','industrie','industria'],icon:'M4 28V14l8 5v-8l8 6V5h7v23H4z M8 23h2m5 0h2m5 0h2',info:()=>ui("Orderboeken, industriële investeringen en transportvolumes hangen vaak samen met de conjunctuur."),note:ui('Machines, transport en industriële productie'),color:'#a3b4cd'},
 {aliases:['real estate','vastgoed','inmobiliario','bienes raices'],icon:'M5 29V10l11-6v25M16 12l11 5v12M2 29h28M9 12v2m0 4v2m0 4v2m12-6v2m0 3v2',info:()=>ui("Huurinkomsten, bezettingsgraad en financieringsrente bepalen mede het resultaat."),note:ui('Gebouwen, verhuur en vastgoedbeheer'),color:'#70ddd3'},
 {aliases:['consumer cyclical','consumer discretionary','cyclische consumentengoederen','consument cyclisch','consumo ciclico'],icon:'M3 5h4l4 16h14l4-12H8 M13 27h1m9 0h1',info:()=>ui("Besteedbaar inkomen en consumentenvertrouwen sturen de vraag naar uitstelbare aankopen."),note:ui('Winkels, reizen en vrijetijdsbesteding'),color:'#ffac81'},
 {aliases:['consumer defensive','consumer staples','consumentengoederen','defensieve consumentengoederen','consumo defensivo'],icon:'M8 12h16l3 16H5l3-16z M11 12V9a5 5 0 0 1 10 0v3 M12 19h8',info:()=>ui("Dagelijkse producten kennen vaak stabielere vraag. Kosten en prijszetting bepalen mede de marges."),note:ui('Voeding, verzorging en dagelijkse producten'),color:'#b1dc82'},
 {aliases:['communication services','communicatiediensten','servicios de comunicacion'],icon:'M16 13v16M10 29h12 M11 9a7 7 0 0 0 0 10m10-10a7 7 0 0 1 0 10M6 4a14 14 0 0 0 0 20M26 4a14 14 0 0 1 0 20 M15 14h2',info:()=>ui("Advertentie-uitgaven, abonnementen en investeringen in netwerken spelen een rol."),note:ui('Telecom, media en online communicatie'),color:'#9b9dff'},
 {aliases:['utilities','nutsbedrijven','servicios publicos'],icon:'M11 3v8m10-8v8M7 11h18v5a9 9 0 0 1-18 0v-5z M16 25v5',info:()=>ui("Tarieven, regelgeving en financiering van netwerken en installaties zijn belangrijk."),note:ui('Elektriciteit, water en gasnetwerken'),color:'#7ddab0'},
 {aliases:['basic materials','materials','basismaterialen','materiales basicos'],icon:'M12 3h8m-6 0v10L5 27h22l-9-14V3 M9 21h14',info:()=>ui("Vraag vanuit bouw en industrie, grondstofprijzen en energiekosten beïnvloeden de marges."),note:ui('Metalen, chemie en grondstoffen'),color:'#dfb491'}
];
function stockSectorTheme(name){const token=String(name).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();return stockSectorThemes.find(t=>t.aliases.includes(token))||{icon:'M5 5h9v9H5z M18 5h9v9h-9z M5 18h9v9H5z M18 18h9v9h-9z',note:ui('Eigen of nog niet ingedeelde sector'),color:'#93abc6'};}
function renderStockSectors(target,groups){
 target.replaceChildren();target.classList.add('stock-sector-grid');const total=groups.reduce((sum,[,count])=>sum+count,0);
 if(!total){target.append(homeNode('p',ui('Nog geen open posities.'),'home-muted'));return;}
 for(const [name,count] of groups){const theme=stockSectorTheme(name),card=homeNode('a',undefined,'stock-sector-card');card.href=stockSectorLink(name===ui('Niet ingedeeld')?'':name);card.style.setProperty('--sector-color',theme.color);
 const badge=homeNode('div',undefined,'stock-sector-symbol');badge.setAttribute('aria-hidden','true');const svg=reportSvgNode('svg',{viewBox:'0 0 32 32',fill:'none',stroke:'currentColor','stroke-width':1.6,'stroke-linecap':'round','stroke-linejoin':'round'});reportSvgNode('path',{d:theme.icon},undefined,svg);badge.append(svg);
 const copy=homeNode('div',undefined,'stock-sector-copy');copy.append(homeNode('h3',name),homeNode('p',theme.note));const weight=homeNode('strong',reportPercent(count/total*100),'stock-sector-weight');
 const track=homeNode('div',undefined,'stock-sector-track'),fill=homeNode('span');fill.style.width=(count/total*100)+'%';track.setAttribute('aria-hidden','true');track.append(fill);
 card.append(badge,copy,weight,homeNode('small',new Intl.NumberFormat(appLocale()).format(count)+' '+(count===1?ui('open notering'):ui('open noteringen')),'stock-sector-count'),track);target.append(card);}
}


let stockSectorGeneration=0,stockSectorScope='';
const stockSectorLink=name=>'#sector?'+new URLSearchParams({name});
function renderStockSectorField(fieldCell,label,sector){
 if(!sector){fieldCell.textContent=label;return;}
 const link=homeNode('a',label);link.href=stockSectorLink(sector);fieldCell.replaceChildren(link);
}
function clearStockSector(){
 stockSectorGeneration++;stockSectorScope='';
 for(const id of ['stock-sector-values','stock-sector-countries','stock-sector-rows','stock-sector-benchmark'])$(id).replaceChildren();
 for(const id of ['stock-sector-title','stock-sector-about','stock-sector-loading','stock-sector-benchmark-note'])$(id).textContent='';
 $('stock-sector-compare').disabled=true;
}
function stockSectorMetric(target,label,value){
 const card=homeNode('article',undefined,'home-metric');
 card.append(homeNode('span',label,'home-metric-label'),homeNode('strong',value));target.append(card);
}
async function loadStockSector(){
 if(!state||!accessSession?.user)return;
 const route=location.hash,account=String(currentBroker),name=new URLSearchParams(route.split('?')[1]).get('name')||'';
 const key=JSON.stringify([route,account,state.data_revision]);
 if(key===stockSectorScope)return;
 clearStockSector();stockSectorScope=key;
 const generation=stockSectorGeneration,active=()=>generation===stockSectorGeneration&&route===location.hash&&account===String(currentBroker)&&!!accessSession?.user;
 const theme=stockSectorTheme(name);
 $('stock-sector-title').textContent=name||ui('Niet ingedeeld');
 $('stock-sector-about').textContent=[theme.note,theme.info?.()].filter(Boolean).join(' · ');
 $('stock-sector-loading').textContent=ui('Laden…');
 try{
  const response=await apiFetch('api/stocks?account_id='+encodeURIComponent(account));
  const result=await response.json();
  if(!active())return;
  if(!response.ok)throw Error();
  const positions=result.positions.filter(p=>(p.categories?.sector||'')===name);
  const open=positions.filter(p=>Number(p.quantity)>0),totals=new Map();
  $('stock-sector-loading').textContent=positions.length?'':ui('Geen noteringen in deze selectie.');
  stockSectorMetric($('stock-sector-values'),ui('Open posities'),new Intl.NumberFormat(appLocale()).format(open.length));
  for(const p of open)if(p.value!=null)totals.set(p.currency,(totals.get(p.currency)||0)+Number(p.value));
  for(const [currency,value] of [...totals].sort())stockSectorMetric($('stock-sector-values'),ui('Bekende marktwaarde')+' · '+currency,money(value,currency));
  for(const [country,count] of stockDistribution(open,'country')){
   const item=homeNode('div',undefined,'stock-sector-country');
   item.append(homeNode('span',country),homeNode('strong',new Intl.NumberFormat(appLocale()).format(count)));
   $('stock-sector-countries').append(item);
  }
  if(!open.length)$('stock-sector-countries').textContent=ui('Nog geen open posities.');
  for(const p of positions){
   const row=homeNode('tr'),link=homeNode('a',p.name+' · '+p.symbol);
   link.href=stockDetailLink(p);cell(row,'').append(link);
   for(const value of [p.categories?.country||ui('Niet ingedeeld'),p.categories?.asset_type||ui('Niet ingedeeld'),quantityLabel(p.quantity),money(p.value,p.currency)])cell(row,value);
   $('stock-sector-rows').append(row);
  }
  const button=$('stock-sector-compare');
  button.disabled=!open.length||!theme.info;
  if(!theme.info)$('stock-sector-benchmark-note').textContent=ui('Geen benchmark voor deze sector beschikbaar.');
  button.onclick=async()=>{
   button.disabled=true;$('stock-sector-benchmark').replaceChildren();$('stock-sector-benchmark-note').textContent=ui('Laden…');
   const messages={unsupported:ui('Geen benchmark voor deze sector beschikbaar.'),unavailable:ui('Onvoldoende gedeelde koersdagen of wisselkoersen voor een betrouwbare vergelijking.'),provider:ui('Benchmarkkoersen konden niet worden geladen. Probeer het later opnieuw.')};
   try{
    const query=new URLSearchParams({account_id:account,sector:name});
    const response=await apiFetch('api/stocks/sector-benchmark?'+query),data=await response.json();
    if(!active())return;
    if(!response.ok)throw Error();
    if(data.status!=='ready'){$('stock-sector-benchmark-note').textContent=messages[data.status];return;}
    const target=$('stock-sector-benchmark');
    stockSectorMetric(target,ui('Jouw huidige aandelen'),homePercent(Number(data.portfolio)));
    stockSectorMetric(target,data.ticker,homePercent(Number(data.benchmark)));
    stockSectorMetric(target,ui('Verschil in procentpunten'),new Intl.NumberFormat(appLocale(),{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(Number(data.difference)));
    const difference=Number(data.difference);
    const outcome=difference>0?ui('Je huidige aandelen presteerden beter dan de benchmark.'):difference<0
     ?ui('Je huidige aandelen presteerden minder goed dan de benchmark.'):ui('Je huidige aandelen en de benchmark kwamen gelijk uit.');
    $('stock-sector-benchmark-note').textContent=outcome+' · '+dayLabel(data.start)+' – '+dayLabel(data.end);
   }catch{if(active())$('stock-sector-benchmark-note').textContent=messages.provider;}
   finally{if(active())button.disabled=false;}
  };
 }catch{
  if(active()){
   stockSectorScope='';
   $('stock-sector-loading').textContent=ui('Aandelen laden mislukt. Open de pagina opnieuw om het nog eens te proberen.');
  }
 }
}
if(typeof document!=='undefined')$('stocks-add').addEventListener('click',()=>openPopup('purchase-editor'));
if(typeof module!=='undefined')module.exports={stockDistribution,stockSectorTheme};


let stockMoversRequest=null;
function clearStockMovers(){
 stockMoversRequest?.abort();
 stockMoversRequest=null;
 $('stock-movers-results').hidden=true;
 for(const side of ['gainers','losers'])$('stock-movers-'+side).replaceChildren();
 $('stock-movers-status').textContent='';
}
async function loadStockMovers(){
 clearStockMovers();
 if(!state||!accessSession?.user)return;
 const account=currentBroker,period=$('stock-movers-period').value,controller=new AbortController();
 stockMoversRequest=controller;
 const status=$('stock-movers-status');
 status.textContent=ui('Ranglijsten laden…');
 const params=new URLSearchParams({account_id:account,days:period});
 try{
  const signal=AbortSignal.any([controller.signal,AbortSignal.timeout(30000)]);
  const response=await apiFetch('api/stocks/movers?'+params,{signal,background:true});
  if(!response.ok)throw Error();
  const data=await response.json();
  if(controller.signal.aborted||!accessSession?.user||location.hash!=='#stijgers-dalers'||account!==currentBroker)return;
  status.textContent=data.day?ui('Handelsdag {date}',{date:dayLabel(data.day)}):'';
  for(const side of ['gainers','losers']){
   const rows=data[side];
   $('stock-movers-'+side).append(...rows.map((position,index)=>stockMoverRow(position,Number(position.change),index)));
   $('stock-movers-'+side+'-empty').hidden=rows.length>0;
  }
  $('stock-movers-results').hidden=false;
 }catch{
  if(!controller.signal.aborted)status.textContent=ui('Ranglijsten laden mislukt. Open de pagina opnieuw om het nogmaals te proberen.');
 }
}
