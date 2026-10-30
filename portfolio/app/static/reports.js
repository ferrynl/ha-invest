/* Reports retain broker scoping from state and keep currencies separate. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
function reportKey(p){return JSON.stringify([p.symbol,p.exchange,p.native_currency||p.currency]);}
function reportNumber(value){return (typeof value==='number'||typeof value==='string'&&value.trim()!=='')&&Number.isFinite(Number(value));}
function reportInstrument(p){return typeof p.symbol==='string'&&p.symbol.trim()!==''&&typeof p.exchange==='string'&&p.exchange.trim()!==''&&typeof p.currency==='string'&&/^[A-Z]{3}$/.test(p.currency);}
function reportDate(value){if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const date=new Date(value+'T00:00:00Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===value;}
function reportData(positions,dividends,type,year,stock,currency){
 const matches=p=>(!stock||reportKey(p)===stock)&&(!currency||p.currency===currency),groups=new Map(),names=new Map(positions.filter(reportInstrument).map(p=>[reportKey(p),p.name||p.symbol]));let skipped=0;
 if(type==='portfolio'||type==='stocks')for(const p of positions.filter(matches)){
  if(!reportInstrument(p)||![p.cost,p.value,p.realised,p.dividend].every(reportNumber)){skipped++;continue;}
  const key=type==='portfolio'?p.currency:reportKey(p),g=groups.get(key)||{name:p.name||p.symbol,currency:p.currency,cost:0,value:0,realised:0,dividend:0,count:0};
  g.count++;g.cost+=Number(p.cost);g.value+=Number(p.value);g.realised+=Number(p.realised);g.dividend+=Number(p.dividend);groups.set(key,g);
 }else for(const d of dividends.filter(matches)){
  if(!reportDate(d.paid_on)){skipped++;continue;}if(d.paid_on.slice(0,4)!==year)continue;
  if(!reportInstrument(d)||!reportNumber(d.amount)){skipped++;continue;}
  const key=(type==='months'?d.paid_on.slice(0,7):reportKey(d))+'|'+d.currency,g=groups.get(key)||{name:type==='months'?d.paid_on.slice(0,7):(names.get(reportKey(d))||d.name||d.symbol),currency:d.currency,count:0,dividend:0};g.count++;g.dividend+=Number(d.amount);groups.set(key,g);
 }
 return {rows:[...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([,g])=>g),skipped};
}
function reportRows(...args){return reportData(...args).rows;}

/* Every chart uses the same validated rows as its supporting table. */
let reportType='portfolio',reportRange='1Y',reportHistory=null,reportHistoryKey='',reportHistoryGeneration=0,reportHistoryPending=false,reportHistoryError=false;
const reportDefinitions=[
 ['performance',ui('Rendementsoverzicht'),ui('Jaarresultaat, inleg en rendementsopbouw.'),'↗'],
 ['portfolio',ui('Portefeuilleoverzicht'),ui('Waarde, winst en spreiding in één blik.'),'◈'],
 ['growth',ui('Waardeontwikkeling'),ui('Marktwaarde en kostprijs door de tijd.'),'⌁'],
 ['allocation',ui('Spreiding & concentratie'),ui('Je grootste posities en hun weging.'),'◉'],
 ['stocks',ui('Winnaars & verliezers'),ui('Welke aandelen dragen het meeste bij?'),'↗'],
 ['components',ui('Opbouw van je resultaat'),ui('Koerswinst, gerealiseerd en dividend.'),'▥'],
 ['months',ui('Dividend per maand'),ui('Maandinkomen en cumulatieve groei.'),'▤'],
 ['income',ui('Dividend per aandeel'),ui('Ontdek je belangrijkste inkomstenbronnen.'),'€'],
 ['calendar',ui('Dividendkalender'),ui('Je dividendritme over meerdere jaren.'),'▦'],
 ['sectors',ui('Sectorverdeling'),ui('Waar zit je economische blootstelling?'),'◫'],
 ['countries',ui('Landenverdeling'),ui('De geografische verdeling van je aandelen.'),'◎']
];
const reportIncome=type=>['months','income','calendar'].includes(type);
function reportCalendarWindow(values,year){return values.filter(p=>Number(p.name.slice(0,4))<=Number(year)&&Number(p.name.slice(0,4))>=Number(year)-5);}
function reportHistoryWindow(group,range){const end=group.as_of||group.history.at(-1)?.day;if(!end)return [];const start=chartPeriodStart(end,range);return group.history.filter(p=>p.day>=start);}
function reportAnalytics(positions,dividends,year,stock='',currency=''){
 const current=reportData(positions,dividends,'stocks',year,stock,currency),income=reportData(positions,dividends,'income',year,stock,currency),months=reportData(positions,dividends,'months',year,stock,currency);
 const matches=p=>(!stock||reportKey(p)===stock)&&(!currency||p.currency===currency);
 const valid=positions.filter(p=>matches(p)&&reportInstrument(p)&&[p.cost,p.value,p.realised,p.dividend].every(reportNumber));
 const annual=dividends.filter(d=>matches(d)&&reportInstrument(d)&&reportDate(d.paid_on)&&reportNumber(d.amount));
 const currencies=[...new Set([...current.rows,...income.rows,...annual].map(p=>p.currency))].sort();
 const calendarSkipped=dividends.filter(matches).filter(d=>!reportDate(d.paid_on)||Number(d.paid_on.slice(0,4))>=Number(year)-5&&Number(d.paid_on.slice(0,4))<=Number(year)&&(!reportInstrument(d)||!reportNumber(d.amount))).length;
 return {skipped:current.skipped,incomeSkipped:income.skipped,calendarSkipped,groups:currencies.map(code=>{
  const holdings=current.rows.filter(p=>p.currency===code).map(p=>({...p,profit:p.value-p.cost+p.realised+p.dividend}));
  const total=holdings.reduce((t,p)=>({value:t.value+p.value,cost:t.cost+p.cost,realised:t.realised+p.realised,dividend:t.dividend+p.dividend,profit:t.profit+p.profit}),{value:0,cost:0,realised:0,dividend:0,profit:0});
  const allocation=holdings.filter(p=>p.value>0).sort((a,b)=>b.value-a.value).map(p=>({...p,weight:total.value>0?p.value/total.value*100:0}));
  const category=field=>{const map=new Map();for(const p of valid.filter(p=>p.currency===code&&Number(p.value)>0)){const label=p.categories?.[field]||ui('Niet ingedeeld');map.set(label,(map.get(label)||0)+Number(p.value));}return [...map].map(([name,value])=>({name,value})).sort((a,b)=>b.value-a.value);};
  const monthValues=Array.from({length:12},(_,index)=>{const key=year+'-'+String(index+1).padStart(2,'0');return {name:key,value:months.rows.find(p=>p.currency===code&&p.name===key)?.dividend||0};});
  let cumulative=0;const cumulativeIncome=monthValues.map(p=>({...p,value:cumulative+=p.value}));
  const calendar=new Map();for(const d of annual.filter(d=>d.currency===code)){const key=d.paid_on.slice(0,7);calendar.set(key,(calendar.get(key)||0)+Number(d.amount));}
  const incomeRows=income.rows.filter(p=>p.currency===code).sort((a,b)=>b.dividend-a.dividend);
  const prior=annual.filter(d=>d.currency===code&&d.paid_on.slice(0,4)===String(Number(year)-1)).reduce((sum,d)=>sum+Number(d.amount),0);
  return {currency:code,holdings,total,allocation,sectors:category('sector'),countries:category('country'),months:monthValues,cumulative:cumulativeIncome,income:incomeRows,calendar:[...calendar].map(([name,value])=>({name,value})),annualIncome:monthValues.reduce((sum,p)=>sum+p.value,0),priorIncome:prior,concentration:allocation.slice(0,5).reduce((sum,p)=>sum+p.weight,0)};
 })};
}
function reportOptions(id,items,label){const select=$(id),previous=select.value;select.replaceChildren();for(const [value,text] of [['',label],...items]){const option=homeNode('option',text);option.value=value;select.append(option);}if(items.some(([value])=>value===previous))select.value=previous;}
function clearReports(){if(typeof clearPerformance==='function')clearPerformance();reportCombinedRequest?.cancel();reportHistoryRequest?.cancel();reportCombinedRefreshes=0;reportHistoryRefreshes=0;reportCombinedGeneration++;reportCombined=null;reportCombinedKey='';reportCombinedPending=false;reportCombinedError=false;reportHistoryGeneration++;reportHistory=null;reportHistoryKey='';reportHistoryPending=false;reportHistoryError=false;for(const id of ['report-charts','report-insights','report-metrics','report-rows','report-stock','report-currency'])$(id).replaceChildren();$('report-status').textContent='';$('report-count').textContent='';$('report-year').replaceChildren();}
function reportHistoryScope(){return JSON.stringify([String(currentBroker),state?.data_revision,$('report-stock').value,$('report-currency').value]);}
async function loadReportHistory(){
 if(!state||!accessSession?.user||reportType!=='growth')return;
 const key=reportHistoryScope();if(key===reportHistoryKey&&(reportHistory||reportHistoryPending||reportHistoryError))return;
 const source=state,generation=++reportHistoryGeneration;reportHistoryKey=key;reportHistory=null;reportHistoryPending=true;reportHistoryError=false;
 try{
  reportHistoryRequest?.cancel();const request=reportHistoryRequest=reportRequest('api/reports/history?account_id='+encodeURIComponent(currentBroker)+'&instrument='+encodeURIComponent($('report-stock').value)+'&currency='+encodeURIComponent($('report-currency').value));const result=await request.promise;
  if(generation!==reportHistoryGeneration||!accessSession?.user||key!==reportHistoryScope())return;
  if(result.data_revision!==source.data_revision){if(reportHistoryRefreshes>=1)throw Error();reportHistoryRefreshes++;reportHistoryKey='';stateETag=null;await load();return;}
  reportHistoryRefreshes=0;reportHistory=result;
 }catch{if(generation===reportHistoryGeneration)reportHistoryError=true;}
 finally{if(generation===reportHistoryGeneration){reportHistoryPending=false;if(state&&location.hash.startsWith('#rapporten'))renderReports();}}
}
function reportMetric(label,value,detail,tone=''){const box=homeNode('article',undefined,'home-metric');box.append(homeNode('span',label,'home-metric-label'),homeNode('strong',value,tone),homeNode('small',detail));$('report-metrics').append(box);}
function reportInsight(label,value,detail){const box=homeNode('article',undefined,'report-insight');box.append(homeNode('small',label),homeNode('strong',value),homeNode('p',detail));$('report-insights').append(box);}
function renderReportNavigation(){
 const nav=$('report-types');nav.replaceChildren();for(const [key,title] of reportDefinitions){const link=homeNode('a',title);link.href='#rapporten-'+key;if(key===reportType)link.setAttribute('aria-current','page');nav.append(link);}
}
function reportChartCard(group,title,note,wide=false){const card=homeNode('section',undefined,'panel report-chart-card'+(wide?' report-wide':''));const heading=homeNode('div',undefined,'section-head'),copy=homeNode('div');copy.append(homeNode('small',group.label||group.currency,'eyebrow'),homeNode('h3',title));heading.append(copy);card.append(heading,homeNode('p',note,'report-chart-note'));const plot=homeNode('div',undefined,'report-plot'),detail=homeNode('p',ui('Bekijk details met je muis of toetsenbord.'),'report-chart-detail');detail.setAttribute('aria-live','polite');card.append(plot,detail);$('report-charts').append(card);return {plot,detail};}
function reportMoney(value,currency){return money(value,currency);}
function renderReports(){
 if(!state)return;const income=reportIncome(reportType),year=$('report-year').value||String(new Date().getFullYear());
 const instruments=new Map();for(const p of [...state.positions,...state.dividends])if(reportInstrument(p)&&!instruments.has(reportKey(p)))instruments.set(reportKey(p),(p.name||p.symbol)+' · '+p.symbol+' · '+p.currency);
 reportOptions('report-stock',[...instruments].sort((a,b)=>a[1].localeCompare(b[1])),ui('Alle aandelen'));
 reportOptions('report-currency',[...new Set([...state.positions,...state.dividends].filter(reportInstrument).map(p=>p.currency))].sort().map(c=>[c,c]),ui('Alle valuta’s'));
 renderReportNavigation();$('report-growth-filter').hidden=reportType!=='calendar';$('report-year-filter').hidden=!income;$('report-range-filter').hidden=reportType!=='growth';
 const definition=reportDefinitions.find(d=>d[0]===reportType);$('report-title').textContent=definition[1];$('report-active-description').textContent=definition[2];
 $('report-description').textContent=reportType==='calendar'?ui('Schatting op basis van de laatste twaalf maanden en jaarlijkse groei. Datums zijn indicatief. Aangekondigde uitkeringen zijn niet gekoppeld.'):income?ui('Ontvangen netto dividend in het gekozen jaar. Eerst het totaal in euro, daarna per valuta.'):reportType==='growth'?ui('Opgeslagen dagwaarden. Ontbrekende posities worden per dag overgeslagen; dit is geen rendementspercentage.'):ui('Actuele stand, inclusief gerealiseerde winst en alle geboekte dividenden. Geen historische jaarstand of fiscale jaaropgave.');
 if(reportType==='performance'){renderPerformanceReport();return;}
 const model=reportAnalytics(state.positions,state.dividends,year,$('report-stock').value,$('report-currency').value);
 let groups=model.groups.filter(g=>income?reportType==='calendar'?(g.calendar.length||g.holdings.length):g.income.length:g.holdings.length);
 $('report-metrics').replaceChildren();$('report-charts').replaceChildren();$('report-insights').replaceChildren();
 const combinedKey=reportCombinedScope();if(reportCombinedKey!==combinedKey){reportCombined=null;reportCombinedError=false;}
 if(reportCombined){const total=reportAnalytics(reportCombined.positions,reportCombined.dividends,year).groups;for(const g of total){g.label=ui('Totaal alle valuta’s in EUR');g.combined=true;g.reportSource=reportCombined;}groups=[...total,...groups];}
 else{reportMetric(ui('Totaal alle valuta’s in EUR'),reportCombinedError?ui('Niet beschikbaar'):ui('Laden…'),ui('Totaal in euro laden…'));const box=homeNode('section',undefined,'panel report-wide');box.append(homeNode('h3',ui('Totaal alle valuta’s in EUR')),homeNode('p',reportCombinedError?ui('Totaal laden mislukt. Probeer opnieuw.'):ui('Totaal in euro laden…')));if(reportCombinedError){const button=homeNode('button',ui('Opnieuw proberen'),'secondary');button.type='button';button.onclick=()=>{reportCombinedKey='';reportCombinedError=false;reportCombinedRefreshes=0;renderReports();};box.append(button);}$('report-charts').append(box);if(!reportCombinedError)loadReportCombined();}
 const coverage=reportCombined?reportCombined.excluded.length+reportCombined.missing_dividends.length:0;
 if(reportCombined&&!groups.some(g=>g.combined)){reportMetric(ui('Totaal alle valuta’s in EUR'),coverage?ui('Onvolledig'):ui('Geen gegevens voor deze selectie.'),ui('Totaal alle valuta’s in EUR'));$('report-charts').append(homeNode('h3',ui('Totaal alle valuta’s in EUR'),'report-group-heading report-wide'),homeNode('p',coverage?ui('Onvolledig totaal: regels met ontbrekende of ongeldige gegevens overgeslagen.'):ui('Geen gegevens voor deze selectie.'),'report-total-note report-wide'));}
 if(reportCombined){const note=homeNode('p',(coverage?ui('Onvolledig totaal: regels met ontbrekende of ongeldige gegevens overgeslagen.')+' '+coverage+' / ':'')+ui('Dividend tegen de koers op betaaldatum; marktwaarde tegen beschikbare recente koersen.')+' '+ui('Koersdatum')+': '+dayLabel(reportCombined.fx_dates.map(p=>p.rate_on).sort().at(-1)||reportCombined.as_of),'report-total-note report-wide');$('report-charts').append(note);}

 for(const g of groups){
  const c=g.currency,scope=(g.label||c)+(g.combined&&coverage?' · '+ui('Onvolledig'):'');
  if(reportType!=='growth')$('report-charts').append(homeNode('h3',g.combined?scope:ui('Uitsplitsing per valuta')+' · '+c,'report-group-heading report-wide'));
  $('report-metrics').append(homeNode('h3',g.combined?scope:ui('Uitsplitsing per valuta')+' · '+c,'report-metric-heading'));
  if(income){reportMetric(ui('Ontvangen dividend'),money(g.annualIncome,c),scope+' · '+year+' · '+g.income.length+' '+ui('inkomstenbronnen'));if(reportType!=='calendar')reportMetric(ui('Gemiddeld per maand'),money(g.annualIncome/12,c),scope+' · '+ui('Jaartotaal gedeeld door twaalf'));}
  else{reportMetric(ui('Marktwaarde'),money(g.total.value,c),scope+' · '+g.holdings.length+' '+ui('aandelen meegenomen'));reportMetric(ui('Totale winst'),money(g.total.profit,c),scope+' · '+ui('Inclusief gerealiseerd resultaat en dividend'),g.total.profit>=0?'positive':'negative');}
  if(reportType==='portfolio'){
   let card=reportChartCard(g,ui('Waar zit je vermogen?'),ui('Weging op basis van bekende marktwaarde.'));reportDonut(card,g.allocation.map(p=>({name:p.name,value:p.value})),c);
   card=reportChartCard(g,ui('Wat levert het op?'),ui('De drie bouwstenen van je totale resultaat.'));reportWaterfall(card,[{name:ui('Ongerealiseerd'),value:g.total.value-g.total.cost},{name:ui('Gerealiseerd'),value:g.total.realised},{name:ui('Dividend'),value:g.total.dividend}],c);
  }else if(reportType==='allocation'){
   let card=reportChartCard(g,ui('Verdeling van je portefeuille'),ui('Alleen posities met een positieve marktwaarde.'));reportDonut(card,g.allocation.map(p=>({name:p.name,value:p.value})),c);
   card=reportChartCard(g,ui('Grootste posities'),ui('De tien grootste posities; overige posities zijn gegroepeerd.'));reportBars(card,reportTop(g.allocation.map(p=>({name:p.name,value:p.value})),10),c);
   reportInsight(ui('Concentratie top 5'),reportPercent(g.concentration),c+' · '+ui('Aandeel van de vijf grootste posities in de bekende marktwaarde.'));
  }else if(reportType==='stocks'){
   let card=reportChartCard(g,ui('Bijdrage per aandeel'),ui('Totale winst in geld, inclusief gerealiseerd resultaat en dividend.'));reportBars(card,[...g.holdings].sort((a,b)=>Math.abs(b.profit)-Math.abs(a.profit)).slice(0,12).map(p=>({name:p.name,value:p.profit})),c,true);
   card=reportChartCard(g,ui('Resultaat in kleur'),ui('Tegels tonen winst of verlies in geld. Dit is geen perioderendement.'));reportTiles(card,g.holdings,c);
  }else if(reportType==='components'){
   let card=reportChartCard(g,ui('Van koersresultaat naar totale winst'),ui('Elke stap telt op bij de vorige; het laatste blok is de totale winst.'),true);reportWaterfall(card,[{name:ui('Ongerealiseerd'),value:g.total.value-g.total.cost},{name:ui('Gerealiseerd'),value:g.total.realised},{name:ui('Dividend'),value:g.total.dividend}],c);
   reportInsight(ui('Gerealiseerd resultaat'),money(g.total.realised,c),ui('Resultaat uit geboekte verkopen binnen de meegenomen posities.'));
   reportInsight(ui('Ongerealiseerd resultaat'),money(g.total.value-g.total.cost,c),ui('Bekende marktwaarde min de openstaande kostprijs.'));
  }else if(reportType==='months'){
   let card=reportChartCard(g,ui('Je maandelijkse dividend'),ui('Twaalf maanden naast elkaar, inclusief maanden zonder uitkering.'));reportColumns(card,g.months,c);
   card=reportChartCard(g,ui('Dividend groeit door'),ui('Cumulatief ontvangen dividend binnen het gekozen jaar.'));reportLine(card,g.cumulative.map(p=>({day:p.name+'-01',value:p.value})),[{key:'value',name:ui('Netto dividend'),color:'#47dcb0'}],c);
  }else if(reportType==='income'){
   let card=reportChartCard(g,ui('Je grootste dividendbetalers'),ui('Ontvangen netto bedragen in het gekozen jaar.'));reportBars(card,reportTop(g.income.map(p=>({name:p.name,value:p.dividend})),10),c);
   card=reportChartCard(g,ui('Verdeling van je dividend'),ui('Weging van iedere inkomstenbron in het ontvangen dividend.'));reportDonut(card,g.income.map(p=>({name:p.name,value:p.dividend})),c);
  }else if(reportType==='calendar'){
   const source=g.reportSource||state,events=reportPaymentCalendar(source.positions,source.dividends,year,g.combined?'':$('report-stock').value,c,Number($('report-growth').value));
   renderPaymentCalendar(g,events,year);
   reportMetric(ui('Verwacht'),money(events.filter(e=>e.estimated).reduce((sum,e)=>sum+e.amount,0),c),scope+' · '+year+' · '+$('report-growth').value+'%');
  }else if(reportType==='sectors'||reportType==='countries'){
   const values=reportType==='sectors'?g.sectors:g.countries;
   let card=reportChartCard(g,reportType==='sectors'?ui('Spreiding over sectoren'):ui('Spreiding over landen'),ui('Op basis van opgeslagen indelingen en bekende marktwaarde. Niet ingedeeld blijft apart zichtbaar.'));reportDonut(card,values,c);
   card=reportChartCard(g,ui('Blootstelling in bedragen'),ui('Directe indeling van je aandelen; geen doorkijk in onderliggende fondsposities.'));reportBars(card,reportTop(values,10),c);
  }
 }
 if(reportType==='growth')renderReportHistory();
 const skipped=reportType==='calendar'?model.calendarSkipped:income?model.incomeSkipped:model.skipped;
 $('report-status').textContent=[groups.length||reportType==='growth'?'':ui('Geen gegevens voor deze selectie.'),skipped?ui('Regels met ontbrekende of ongeldige gegevens overgeslagen:')+' '+new Intl.NumberFormat(appLocale()).format(skipped)+'. '+ui('De totalen zijn alleen gebaseerd op de meegenomen regels.'):''].filter(Boolean).join(' ');
 renderReportTable({...model,groups},year);
}
function renderReportHistory(){
 const key=reportHistoryScope();if(reportHistoryKey!==key){reportHistory=null;reportHistoryError=false;reportHistoryPending=false;}
 if(!reportHistory){
  const message=homeNode('div',undefined,'panel report-wide');message.append(homeNode('p',reportHistoryError?ui('Historie laden mislukt. Probeer het opnieuw.'):ui('Opgeslagen koershistorie laden…')));
  if(reportHistoryError){const button=homeNode('button',ui('Opnieuw proberen'),'secondary');button.type='button';button.onclick=()=>{reportHistoryKey='';reportHistoryError=false;reportHistoryRefreshes=0;renderReports();};message.append(button);}
  $('report-charts').append(message);if(!reportHistoryError)loadReportHistory();return;
 }
 for(const g of [...(reportCombined?.history?[{...reportCombined.history,label:ui('Totaal alle valuta’s in EUR')}]:[]),...reportHistory.currencies]){$('report-charts').append(homeNode('h3',g.label||ui('Uitsplitsing per valuta')+' · '+g.currency,'report-group-heading report-wide'));const points=reportHistoryWindow(g,reportRange);const card=reportChartCard(g,ui('Marktwaarde naast kostprijs'),ui('Bekende dagwaarden; aankopen en verkopen beïnvloeden de waarde. Ontbrekende posities tellen die dag niet mee.'),true);reportLine(card,points,[{key:'value',name:ui('Marktwaarde'),color:'#47dcb0'},{key:'cost',name:ui('Openstaande kostprijs'),color:'#70b7ff'}],g.currency);
  const start=g.as_of?chartPeriodStart(g.as_of,reportRange):'0001-01-01',missing=points.filter(p=>p.skipped).length+(g.omitted_dates||[]).filter(day=>day>=start).length;if(missing)card.detail.textContent=ui('Dagen met overgeslagen gegevens:')+' '+missing+'. '+ui('De totalen zijn alleen gebaseerd op de meegenomen regels.');
 }
 if(!reportHistory.currencies.length)$('report-charts').append(homeNode('p',ui('Geen gegevens voor deze selectie.'),'report-wide'));
}
function renderReportTable(model,year){
 const income=reportIncome(reportType),head=$('report-head'),body=$('report-rows');head.replaceChildren();body.replaceChildren();
 if(reportType==='growth'){
  const header=document.createElement('tr');for(const label of [ui('Datum'),ui('Valuta'),ui('Marktwaarde'),ui('Openstaande kostprijs'),ui('Dividend'),ui('Overgeslagen:')]){const th=homeNode('th',label);th.scope='col';header.append(th);}head.append(header);
  let count=0;for(const g of [...(reportCombined?.history?[{...reportCombined.history,label:ui('Totaal alle valuta’s in EUR')}]:[]),...(reportHistory?.currencies||[])]){const points=reportHistoryWindow(g,reportRange);count+=points.length;for(const p of points.slice(-250)){const row=document.createElement('tr');for(const value of [new Date(p.day+'T00:00:00Z').toLocaleDateString(appLocale(),{timeZone:'UTC'}),g.label||g.currency,money(p.value,g.currency),money(p.cost,g.currency),money(p.dividend,g.currency),p.skipped])cell(row,value);body.append(row);}}
  $('report-count').textContent=new Intl.NumberFormat(appLocale()).format(count)+' · '+ui('Laatste 250 dagwaarden per valuta');return;
 }
 const headings=income?[reportType==='calendar'?ui('Betaaldatum'):reportType==='months'?ui('Maand'):ui('Aandeel'),ui('Valuta'),ui('Netto dividend')]:[ui('Aandeel'),ui('Valuta'),ui('Inleg'),ui('Marktwaarde'),ui('Gerealiseerd'),ui('Dividend'),ui('Totale winst')];const tr=document.createElement('tr');for(const label of headings){const th=homeNode('th',label);th.scope='col';tr.append(th);}head.append(tr);
 let count=0;for(const g of model.groups){if(income&&!(reportType==='calendar'?(g.calendar.length||g.holdings.length):g.income.length))continue;let records;if(income){records=reportType==='months'?g.months.map(p=>({name:reportMonth(p.name),value:p.value})):reportType==='calendar'?reportPaymentCalendar((g.reportSource||state).positions,(g.reportSource||state).dividends,year,g.combined?'':$('report-stock').value,g.currency,Number($('report-growth').value)).map(p=>({name:dayLabel(p.day)+' / '+p.name+' / '+(p.estimated?ui('Geschat'):ui('Ontvangen')),value:p.amount})):g.income.map(p=>({name:p.name,value:p.dividend}));}else records=g.holdings;
  for(const p of records){const row=document.createElement('tr'),values=income?[p.name,g.label||g.currency,money(p.value,g.currency)]:[p.name,g.label||g.currency,money(p.cost,g.currency),money(p.value,g.currency),money(p.realised,g.currency),money(p.dividend,g.currency),money(p.profit,g.currency)];for(const value of values)cell(row,value);body.append(row);count++;}
 }$('report-count').textContent=new Intl.NumberFormat(appLocale()).format(count)+' · '+ui('regels');
}
if(typeof document!=='undefined'){
 for(const id of ['report-stock','report-currency'])$(id).addEventListener('change',renderReports);
 $('report-growth').addEventListener('change',renderReports);
 $('report-range').addEventListener('change',()=>{reportRange=$('report-range').value;renderReports();});
}
if(typeof module!=='undefined')module.exports={reportMonthGrid,reportPaymentCalendar,reportRows,reportData,reportAnalytics,reportCalendarWindow,reportHistoryWindow};

function reportPaymentCalendar(positions,dividends,year,stock='',currency='',growth=3,today=new Date().toISOString().slice(0,10)){
 const valid=dividends.filter(d=>reportInstrument(d)&&reportDate(d.paid_on)&&reportNumber(d.amount)&&(!stock||reportKey(d)===stock)&&(!currency||d.currency===currency));
 const names=new Map(positions.map(p=>[reportKey(p),p.name||p.symbol]));
 const events=valid.filter(d=>d.paid_on.slice(0,4)===String(year)&&d.paid_on<=today).map(d=>({day:d.paid_on,name:names.get(reportKey(d))||d.symbol,amount:Number(d.amount),estimated:false}));
 const start=new Date(today+'T00:00:00Z');start.setUTCFullYear(start.getUTCFullYear()-1);
 for(const d of valid.filter(d=>d.paid_on>start.toISOString().slice(0,10)&&d.paid_on<=today)){
  const position=positions.find(p=>reportKey(p)===reportKey(d)&&p.account_id===d.account_id&&Number(p.quantity)>0);if(!position)continue;
  const offset=Number(year)-Number(d.paid_on.slice(0,4));if(offset<0)continue;
  let day=String(year)+d.paid_on.slice(4);if(!reportDate(day))day=String(year)+'-02-28';if(day<=today)continue;
  events.push({day,name:position.name||d.symbol,amount:Number(d.amount)*Math.pow(1+growth/100,offset),estimated:true,basis:d.paid_on});
 }return events.sort((a,b)=>a.day.localeCompare(b.day)||a.name.localeCompare(b.name));
}

let reportCalendarMonth=new Date().getMonth(),reportCalendarDay='';
function reportMonthGrid(year,month){
 const first=new Date(Date.UTC(Number(year),month,1)),offset=(first.getUTCDay()+6)%7,days=new Date(Date.UTC(Number(year),month+1,0)).getUTCDate();
 return Array.from({length:Math.ceil((offset+days)/7)*7},(_,i)=>i<offset||i>=offset+days?null:String(year)+'-'+String(month+1).padStart(2,'0')+'-'+String(i-offset+1).padStart(2,'0'));
}
function renderPaymentCalendar(group,events,year){
 const card=reportChartCard(group,ui('Dividendkalender'),ui('Kies een betaaldag voor de uitkeringen en details.'),true);card.plot.classList.add('payment-calendar');card.detail.hidden=true;
 const toolbar=homeNode('div',undefined,'payment-toolbar'),controls=homeNode('div',undefined,'payment-controls'),previous=homeNode('button','‹','secondary'),next=homeNode('button','›','secondary'),select=homeNode('select');
 previous.type=next.type='button';previous.setAttribute('aria-label',ui('Vorige maand'));next.setAttribute('aria-label',ui('Volgende maand'));select.setAttribute('aria-label',ui('Maand'));
 for(let month=0;month<12;month++){const option=homeNode('option',new Date(Date.UTC(Number(year),month,1)).toLocaleDateString(appLocale(),{month:'long',year:'numeric',timeZone:'UTC'}));option.value=String(month);select.append(option);}select.value=String(reportCalendarMonth);
 previous.disabled=reportCalendarMonth===0;next.disabled=reportCalendarMonth===11;
 const change=month=>{reportCalendarMonth=month;reportCalendarDay='';renderReports();};previous.onclick=()=>change(reportCalendarMonth-1);next.onclick=()=>change(reportCalendarMonth+1);select.onchange=()=>change(Number(select.value));controls.append(previous,select,next);
 const legend=homeNode('div',undefined,'payment-legend');legend.append(homeNode('span',ui('Ontvangen'),'payment-received'),homeNode('span',ui('Geschat'),'payment-estimated'));toolbar.append(controls,legend);card.plot.append(toolbar);
 const prefix=String(year)+'-'+String(reportCalendarMonth+1).padStart(2,'0'),monthly=events.filter(e=>e.day.startsWith(prefix)),layout=homeNode('div',undefined,'payment-layout'),calendar=homeNode('div',undefined,'payment-month'),week=homeNode('div',undefined,'payment-week');
 for(let i=0;i<7;i++)week.append(homeNode('span',new Date(Date.UTC(2026,0,5+i)).toLocaleDateString(appLocale(),{weekday:'short',timeZone:'UTC'})));calendar.append(week);
 const grid=homeNode('div',undefined,'payment-grid'),agenda=homeNode('div',undefined,'payment-agenda');agenda.setAttribute('aria-live','polite');const today=new Date().toLocaleDateString('en-CA');
 function details(day){
  reportCalendarDay=day||'';for(const button of grid.querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.day===day));agenda.replaceChildren();
  agenda.append(homeNode('small',ui('UITKERINGEN'),'eyebrow'),homeNode('h3',day?dayLabel(day):ui('Deze maand')));const rows=day?monthly.filter(e=>e.day===day):monthly;
  const total=rows.reduce((sum,e)=>sum+e.amount,0);agenda.append(homeNode('strong',money(total,group.currency),'payment-total'));
  if(!rows.length)agenda.append(homeNode('p',ui('Geen dividendbetalingen voor deze selectie.'),'home-muted'));
  for(const event of rows){const item=homeNode('article',undefined,'payment-event '+(event.estimated?'payment-estimated':'payment-received')),heading=homeNode('div');heading.append(homeNode('strong',event.name),homeNode('strong',money(event.amount,group.currency)));item.append(heading,homeNode('small',dayLabel(event.day)+' / '+(event.estimated?ui('Geschat'):ui('Ontvangen'))));if(event.estimated)item.append(homeNode('small',ui('Basisdatum')+': '+dayLabel(event.basis)+' / '+$('report-growth').value+'% '+ui('jaarlijkse groei')));agenda.append(item);}
 }
 for(const day of reportMonthGrid(year,reportCalendarMonth)){
  if(!day){grid.append(homeNode('div',undefined,'payment-day payment-padding'));continue;}
  const rows=monthly.filter(e=>e.day===day),button=homeNode('button',undefined,'payment-day'+(day===today?' payment-today':'')+(rows.length?' payment-has-events':'')+(rows.length&&rows.every(e=>e.estimated)?' payment-has-estimates':''));button.type='button';button.dataset.day=day;button.setAttribute('aria-label',dayLabel(day)+' / '+rows.length+' '+ui('uitkeringen'));button.setAttribute('aria-pressed','false');button.append(homeNode('span',String(Number(day.slice(-2))),'payment-day-number'));
  if(rows.length){const amount=homeNode('strong',money(rows.reduce((sum,e)=>sum+e.amount,0),group.currency),'payment-day-amount');button.append(amount);const dots=homeNode('span',undefined,'payment-dots');for(const event of rows.slice(0,4))dots.append(homeNode('i',undefined,event.estimated?'payment-dot-estimated':'payment-dot-received'));button.append(dots);button.append(homeNode('small',rows.map(e=>e.name).join(', '),'payment-day-names'));}button.onclick=()=>details(day);grid.append(button);
 }calendar.append(grid);layout.append(calendar,agenda);card.plot.append(layout);details(reportCalendarDay.startsWith(prefix)?reportCalendarDay:'');
}

let reportCombined=null,reportCombinedKey='',reportCombinedPending=false,reportCombinedError=false,reportCombinedGeneration=0;
function reportCombinedScope(){return JSON.stringify([String(currentBroker),state?.data_revision,$('report-stock').value,$('report-currency').value,reportType==='growth']);}
async function loadReportCombined(){
 if(!state||!accessSession?.user)return;const key=reportCombinedScope();if(key===reportCombinedKey&&(reportCombined||reportCombinedPending||reportCombinedError))return;
 const source=state,generation=++reportCombinedGeneration;reportCombinedKey=key;reportCombinedPending=true;reportCombinedError=false;reportCombined=null;
 try{reportCombinedRequest?.cancel();const request=reportCombinedRequest=reportRequest('api/reports/combined?account_id='+encodeURIComponent(currentBroker)+'&instrument='+encodeURIComponent($('report-stock').value)+'&currency='+encodeURIComponent($('report-currency').value)+'&history='+(reportType==='growth'?'1':'0'));const data=await request.promise;if(generation!==reportCombinedGeneration||!accessSession?.user||key!==reportCombinedScope())return;
 if(data.data_revision!==source.data_revision){if(reportCombinedRefreshes>=1)throw Error();reportCombinedRefreshes++;reportCombinedKey='';stateETag=null;await load();return;}reportCombinedRefreshes=0;reportCombined=data;
 }catch{if(generation===reportCombinedGeneration)reportCombinedError=true;}
 finally{if(generation===reportCombinedGeneration){reportCombinedPending=false;if(state&&location.hash.startsWith('#rapporten'))renderReports();}}
}

let reportCombinedRequest=null,reportHistoryRequest=null,reportCombinedRefreshes=0,reportHistoryRefreshes=0;
function reportRequest(url,timeout=15000){
 const controller=typeof AbortController==='function'?new AbortController():null;let timer,rejectWait;
 const pending=(async()=>{const response=await apiFetch(url,controller?{signal:controller.signal}:{});if(!response.ok){let result;try{result=await response.json();}catch{}const error=Error(result?.error||ui('Rapportaanvraag mislukt.'));error.code='report_server';throw error;}return await response.json();})();
 const stopped=new Promise((resolve,reject)=>{rejectWait=reject;});
 const cancel=()=>{controller?.abort();const error=Error(ui('De rapportaanvraag duurde te lang. Probeer opnieuw.'));error.code='report_timeout';rejectWait(error);};
 if(typeof setTimeout==='function')timer=setTimeout(cancel,timeout);
 return {cancel,promise:Promise.race([pending,stopped]).finally(()=>{if(timer!==undefined)clearTimeout(timer);})};
}
