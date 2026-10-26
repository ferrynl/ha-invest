/* Reports retain broker scoping from state and keep currencies separate. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let reportType='portfolio';
const reportDefinitions=[['portfolio',ui('Huidige portefeuille')],['stocks',ui('Resultaat per aandeel')],['months',ui('Dividend per maand')],['income',ui('Dividend per aandeel')]];
function reportKey(p){return JSON.stringify([p.symbol,p.exchange,p.currency]);}
function reportNumber(value){return (typeof value==='number'||typeof value==='string'&&value.trim()!=='')&&Number.isFinite(Number(value));}
function reportInstrument(p){return typeof p.symbol==='string'&&p.symbol.trim()!==''&&typeof p.exchange==='string'&&p.exchange.trim()!==''&&typeof p.currency==='string'&&/^[A-Z]{3}$/.test(p.currency);}
function reportDate(value){if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const date=new Date(value+'T00:00:00Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===value;}
function reportData(positions,dividends,type,year,stock,currency){
 const matches=p=>(!stock||reportKey(p)===stock)&&(!currency||p.currency===currency),groups=new Map();let skipped=0;
 if(type==='portfolio'||type==='stocks')for(const p of positions.filter(matches)){
  if(!reportInstrument(p)||![p.cost,p.value,p.realised,p.dividend].every(reportNumber)){skipped++;continue;}
  const key=type==='portfolio'?p.currency:reportKey(p),g=groups.get(key)||{name:p.name||p.symbol,currency:p.currency,cost:0,value:0,realised:0,dividend:0,count:0};
  g.count++;g.cost+=Number(p.cost);g.value+=Number(p.value);g.realised+=Number(p.realised);g.dividend+=Number(p.dividend);groups.set(key,g);
 }else for(const d of dividends.filter(matches)){
  if(!reportDate(d.paid_on)){skipped++;continue;}if(d.paid_on.slice(0,4)!==year)continue;
  if(!reportInstrument(d)||!reportNumber(d.amount)){skipped++;continue;}
  const key=(type==='months'?d.paid_on.slice(0,7):reportKey(d))+'|'+d.currency,g=groups.get(key)||{name:type==='months'?d.paid_on.slice(0,7):(d.name||d.symbol),currency:d.currency,count:0,dividend:0};g.count++;g.dividend+=Number(d.amount);groups.set(key,g);
 }
 return {rows:[...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([,g])=>g),skipped};
}
function reportRows(...args){return reportData(...args).rows;}
function reportOptions(id,items,label){const select=$(id),previous=select.value;select.replaceChildren();for(const [value,text] of [['',label],...items]){const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option);}if(items.some(([value])=>value===previous))select.value=previous;}
function renderReports(){
 if(!state)return;const instruments=new Map();for(const p of [...state.positions,...state.dividends])if(reportInstrument(p)&&!instruments.has(reportKey(p)))instruments.set(reportKey(p),(p.name||p.symbol)+' · '+p.symbol+' · '+p.currency);
 reportOptions('report-stock',[...instruments].sort((a,b)=>a[1].localeCompare(b[1])),ui('Alle aandelen'));reportOptions('report-currency',[...new Set([...state.positions,...state.dividends].filter(reportInstrument).map(p=>p.currency))].sort().map(c=>[c,c]),ui('Alle valuta’s'));
 const income=reportType==='months'||reportType==='income';$('report-year-filter').hidden=!income;$('report-title').textContent=reportDefinitions.find(d=>d[0]===reportType)[1];
 $('report-types').replaceChildren();for(const [key,title] of reportDefinitions){const button=document.createElement('button');button.type='button';button.className='report-type';button.setAttribute('aria-pressed',String(key===reportType));button.textContent=title;button.onclick=()=>{reportType=key;renderReports();$('report-types').querySelector('[aria-pressed="true"]').focus();};$('report-types').append(button);}
 $('report-description').textContent=income?ui('Ontvangen netto dividend in het gekozen jaar. Bedragen blijven per valuta gescheiden.'):ui('Actuele stand, inclusief gerealiseerde winst en alle geboekte dividenden. Geen historische jaarstand of fiscale jaaropgave.');
 const {rows,skipped}=reportData(state.positions,state.dividends,reportType,$('report-year').value,$('report-stock').value,$('report-currency').value);
 const headings=income?[reportType==='months'?ui('Maand'):ui('Aandeel'),ui('Valuta'),ui('Uitkeringen'),ui('Netto dividend')]:[reportType==='stocks'?ui('Aandeel'):ui('Valuta'),...(reportType==='stocks'?[ui('Valuta')]:[ui('Aandelen')]),ui('Inleg'),ui('Marktwaarde'),ui('Koerswinst incl. gerealiseerd'),ui('Dividend'),ui('Totale winst')];
 $('report-head').replaceChildren();const head=document.createElement('tr');for(const title of headings){const th=document.createElement('th');th.scope='col';th.textContent=title;head.append(th);}$('report-head').append(head);
 $('report-rows').replaceChildren();for(const g of rows){const row=document.createElement('tr');let values;if(income){const name=reportType==='months'?new Date(g.name+'-01T00:00:00Z').toLocaleDateString(appLocale(),{month:'long',year:'numeric',timeZone:'UTC'}):g.name;values=[name,g.currency,g.count,money(g.dividend,g.currency)];}else values=[reportType==='stocks'?g.name:g.currency,reportType==='stocks'?g.currency:g.count,money(g.cost,g.currency),money(g.value,g.currency),money(g.value-g.cost+g.realised,g.currency),money(g.dividend,g.currency),money(g.value-g.cost+g.realised+g.dividend,g.currency)];for(const value of values)cell(row,value);$('report-rows').append(row);}
 $('report-count').textContent=new Intl.NumberFormat(appLocale()).format(rows.length);$('report-status').textContent=[rows.length?'':ui('Geen gegevens voor deze selectie.'),skipped?ui('Regels met ontbrekende of ongeldige gegevens overgeslagen:')+' '+new Intl.NumberFormat(appLocale()).format(skipped)+'. '+ui('De totalen zijn alleen gebaseerd op de meegenomen regels.'):''].filter(Boolean).join(' ');
 $('report-metrics').replaceChildren();for(const currency of [...new Set(rows.map(g=>g.currency))]){const group=rows.filter(g=>g.currency===currency),amount=group.reduce((sum,g)=>sum+(income?g.dividend:g.value-g.cost+g.realised+g.dividend),0),box=homeNode('article',undefined,'home-metric');box.append(homeNode('span',income?ui('Netto dividend'):ui('Totale winst'),'home-metric-label'),homeNode('strong',money(amount,currency)));$('report-metrics').append(box);}
}
if(typeof document!=='undefined')for(const id of ['report-stock','report-currency'])$(id).addEventListener('change',renderReports);
if(typeof module!=='undefined')module.exports={reportRows,reportData};
