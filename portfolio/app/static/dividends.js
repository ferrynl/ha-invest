/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
/* Dividend history and a clearly labeled historical income scenario. */
let dividendData=null,dividendCurrency='',dividendAccount='',dividendGeneration=0,dividendLedgerLimit=100;
const dividendMonth=month=>new Date(month+'-01T00:00:00Z').toLocaleDateString((typeof appLocale==='function'?appLocale():'nl-NL'),{month:'short',year:'numeric',timeZone:'UTC'});
function dividendNode(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function clearDividendDashboard(){dividendGeneration++;dividendData=null;dividendCurrency='';dividendAccount='';dividendLedgerLimit=100;for(const id of ['dividend-currencies','dividend-metrics','dividend-years','dividend-calendar','dividend-contributors','dividend-exclusions','dividend-history-chart','dividend-forecast-chart','dividends'])$(id).replaceChildren();for(const id of ['dividend-dashboard-status','dividend-coverage','dividend-history-detail','dividend-forecast-detail','dividend-ledger-count','dividend-empty'])$(id).textContent='';$('dividend-more').hidden=true;$('dividend-exclusions-title').textContent=ui('Niet meegenomen in de verwachting');for(const id of ['dividend-history-chart','dividend-forecast-chart']){const chart=$(id);chart.onpointermove=null;chart.onpointerleave=null;chart.onkeydown=null;chart.onclick=null;}}
async function renderDividendDashboard(){
 if(!state||!accessSession?.user)return;const account=String(currentBroker),generation=++dividendGeneration;
 if(dividendAccount!==account){clearDividendDashboard();dividendAccount=account;return renderDividendDashboard();}
 if(!dividendData)$('dividend-dashboard-status').textContent=ui('Je dividendoverzicht laden…');
 let stage='request',httpStatus=0,logId='';
 try{
  const response=await apiFetch('api/dividends/overview?account_id='+encodeURIComponent(account)+(dividendCurrency==='ALL'?'&combined=1':''));
  httpStatus=response.status;stage='response';
  const data=await response.json();
  if(generation!==dividendGeneration||account!==String(currentBroker)||!accessSession?.user)return;
  logId=data?.log_id||'';
  if(!response.ok)throw Error();
  stage='render';dividendData=data;
  $('dividend-dashboard-status').textContent='';drawDividendDashboard();
 }catch(error){
  if(generation!==dividendGeneration)return;
  console.error('dividend_overview_failed',{stage,httpStatus,errorType:error.name,logId});
  $('dividend-dashboard-status').textContent=ui('Dividendoverzicht laden mislukt. Open de pagina opnieuw om het nog eens te proberen.')+(logId?' · Log-ID '+logId:'');
 }
}
function dividendGrowthScenario(source,growth){
 const rate=Number.isFinite(growth)?Math.max(0,Math.min(10,growth))/100:0.03;
 const currentYear=Number(dividendData.as_of.slice(0,4));
 const forecast=source.forecast.map(row=>{
  const factor=Math.pow(1+rate,Number(row.month.slice(0,4))-currentYear);
  return {...row,amount:String(Number(row.amount)*factor),companies:(row.companies||[]).map(company=>({...company,amount:String(Number(company.amount)*factor)}))};
 });
 const yearly=source.yearly.map(row=>({...row,expected:String(forecast.filter(p=>p.month.startsWith(row.year+'-')).reduce((sum,p)=>sum+Number(p.amount),0))}));
 const next12=forecast.slice(0,12).reduce((sum,p)=>sum+Number(p.amount),0);
 return {...source,forecast,yearly,next12:String(next12),monthly_average:String(next12/12),contributors:source.contributors.map(p=>({...p,expected:String(Number(p.expected)*(Number(source.next12)>0?next12/Number(source.next12):1))}))};
}
function drawDividendDashboard(){
 if(!dividendData)return;const groups=dividendData.currencies;if(dividendCurrency!=='ALL'&&!groups.some(g=>g.currency===dividendCurrency))dividendCurrency=groups.some(g=>g.currency==='EUR')?'EUR':groups[0]?.currency||'EUR';
 $('dividend-currencies').replaceChildren();for(const group of [{currency:'ALL'},...groups]){const button=dividendNode('button',group.currency==='ALL'?ui('Alle valuta’s in euro'):group.currency);button.type='button';button.setAttribute('aria-pressed',String(group.currency===dividendCurrency));button.addEventListener('click',()=>{dividendCurrency=group.currency;dividendLedgerLimit=100;if(group.currency==='ALL'&&!dividendData.combined){drawDividendDashboard();renderDividendDashboard();}else drawDividendDashboard();});$('dividend-currencies').append(button);}
 const source=dividendCurrency==='ALL'?dividendData.combined:groups.find(g=>g.currency===dividendCurrency);const data=source?dividendGrowthScenario(source,Number($('dividend-growth').value)):null;$('dividend-metrics').replaceChildren();
 if(dividendCurrency==='ALL'&&!data){$('dividend-dashboard-content').hidden=true;$('dividend-dashboard-status').textContent=ui('Alle dividendvaluta’s omrekenen naar euro…');return;}
 $('dividend-dashboard-content').hidden=false;
 if(!data){$('dividend-dashboard-status').textContent=ui('Je dividenddashboard begint bij je eerste aankoop of dividendbetaling.');for(const id of ['dividend-years','dividend-calendar','dividend-contributors','dividend-exclusions','dividend-history-chart','dividend-forecast-chart'])$(id).replaceChildren();$('dividend-coverage').textContent='';$('dividend-exclusions-title').textContent=ui('Nog geen posities om te beoordelen');$('dividend-history-detail').textContent=ui('Nog geen ontvangen dividend.');$('dividend-forecast-detail').textContent=ui('Nog geen historie om een verwachting op te baseren.');renderDividendLedger();return;}
 const currency=data.currency,change=Number(data.previous12)>0?(Number(data.trailing12)/Number(data.previous12)-1)*100:null;
 for(const [label,value,note] of [[ui('Totaal ontvangen'),money(data.total,currency),data.payments+ui(' geboekte betalingen')],[ui('Dit jaar ontvangen'),money(data.ytd,currency),ui('Van 1 januari tot ')+dayLabel(dividendData.as_of)],[ui('Afgelopen 12 maanden'),money(data.trailing12,currency),change==null?ui('Netto ontvangen dividend'):homePercent(change)+ui(' tegenover de 12 maanden daarvoor')],[ui('Komende 12 maanden'),data.coverage.modeled?money(data.next12,currency):ui('Nog geen basis'),data.coverage.modeled?ui('Geschat · gemiddeld ')+money(data.monthly_average,currency)+ui(' per maand'):ui('Eerst bruikbare dividendhistorie nodig')]]){const box=dividendNode('article',undefined,'home-metric');box.append(dividendNode('span',label,'home-metric-label'),dividendNode('strong',value),dividendNode('small',note));$('dividend-metrics').append(box);}
 $('dividend-coverage').textContent=(dividendCurrency==='ALL'?ui('Alle valuta’s in EUR · ontvangen op de betaaldatum omgerekend · schatting met beschikbare actuele wisselkoersen tot ')+dayLabel(data.fx_as_of):ui('Overzicht in ')+currency)+ui(' · verwachting voor ')+data.coverage.modeled+ui(' van ')+data.coverage.open+ui(' open posities.');
 if(dividendCurrency==='ALL'&&data.missing_payments.length)$('dividend-coverage').append(document.createTextNode(' '+data.missing_payments.length+ui(' betalingen zonder wisselkoers niet meegerekend: ')+data.missing_payments.slice(0,6).map(p=>p.symbol+' ('+p.currency+', '+dayLabel(p.day)+')').join(' · ')));
 let history=data.monthly;if($('dividend-history-range').value==='12')history=history.slice(-12);else if($('dividend-history-range').value==='all'){const months=new Map(data.months.map(p=>[p.month,p.amount]));history=[];const first=data.first_month;let day=new Date(first+'-01T00:00:00Z');while(day.toISOString().slice(0,7)<=dividendData.as_of.slice(0,7)){const month=day.toISOString().slice(0,7);history.push({month,amount:months.get(month)||'0'});day.setUTCMonth(day.getUTCMonth()+1);}}
 dividendBarChart('dividend-history-chart','dividend-history-detail',history,currency,false);
 const forecast=data.forecast.slice(0,Number($('dividend-forecast-range').value));dividendBarChart('dividend-forecast-chart','dividend-forecast-detail',data.coverage.modeled?forecast:[],currency,true);
 $('dividend-years').replaceChildren();const years=data.yearly.filter(row=>row.year>=Number(dividendData.as_of.slice(0,4))-3&&(row.year<=Number(dividendData.as_of.slice(0,4))||row.months_expected===12)),maximum=Math.max(1,...years.map(row=>Number(row.received)+Number(row.expected)));
 for(const row of years){const item=dividendNode('div',undefined,'dividend-year'),head=dividendNode('div',undefined,'dividend-year-label');head.append(dividendNode('strong',String(row.year)+(row.months_expected&&row.months_expected<12?' · '+row.months_expected+ui(' mnd vooruit'):'')),dividendNode('span',Number(row.expected)?(Number(row.received)?money(row.received,currency)+' + ':'')+money(row.expected,currency)+ui(' geschat'):row.year>Number(dividendData.as_of.slice(0,4))&&!data.coverage.modeled?ui('Geen basis'):money(row.received,currency)));const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 100 6');svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('aria-hidden','true');let x=0;for(const [value,color] of [[row.received,'#47dcb0'],[row.expected,'#70b7ff']]){const rect=document.createElementNS(svg.namespaceURI,'rect');rect.setAttribute('x',String(x));rect.setAttribute('width',String(Number(value)/maximum*100));rect.setAttribute('height','6');rect.setAttribute('fill',color);svg.append(rect);x+=Number(value)/maximum*100;}item.append(head,svg);$('dividend-years').append(item);}
 $('dividend-calendar').replaceChildren();
 for(const row of data.forecast.slice(0,12)){
  const tile=dividendNode('button',undefined,'dividend-month secondary');tile.type='button';
  tile.append(dividendNode('span',dividendMonth(row.month)),dividendNode('strong',data.coverage.modeled?money(row.amount,currency):'-'),dividendNode('small',data.coverage.modeled?ui('Verwacht'):ui('Onvoldoende historie')));
  const logos=dividendNode('span',undefined,'dividend-company-logos'),seen=new Set();
  for(const company of row.companies){
   const key=stockDetailLink(company);
   if(seen.has(key))continue;
   seen.add(key);
   const mark=dividendNode('span',company.symbol.slice(0,4),'dividend-company-logo');
   mark.title=company.name;mark.setAttribute('role','img');mark.setAttribute('aria-label',company.name);
   logos.append(mark);
   loadDividendLogo(mark,company).catch(()=>{});
  }
  tile.append(logos);tile.addEventListener('click',()=>openDividendMonth(row,currency,true));
  $('dividend-calendar').append(tile);
 }
 $('dividend-contributors').replaceChildren();for(const p of data.contributors.slice(0,12)){const row=dividendNode('div',undefined,'dividend-contributor'),identity=dividendNode('div'),link=dividendNode('a',p.name);link.href=stockDetailLink(p);identity.append(link,dividendNode('small',p.symbol+' · '+p.account_name));const amounts=dividendNode('div');amounts.append(dividendNode('strong',money(p.received,currency)),dividendNode('small',p.open?(Number(p.expected)?ui('Geschat per jaar ')+money(p.expected,currency):ui('Geen basis voor verwachting')):ui('Gesloten positie')));row.append(identity,amounts);$('dividend-contributors').append(row);}if(!data.contributors.length)$('dividend-contributors').append(dividendNode('p',ui('Nog geen ontvangen betalingen in deze valuta.'),'home-muted'));
 $('dividend-exclusions-title').textContent=data.coverage.excluded.length+' '+(data.coverage.excluded.length===1?ui('positie'):ui('posities'))+ui(' met ontbrekende of onvolledige basis');$('dividend-exclusions').replaceChildren();for(const p of data.coverage.excluded){const line=dividendNode('p',undefined,'home-muted'),link=dividendNode('a',p.name+' · '+p.account_name);link.href=stockDetailLink(p);line.append(link,document.createTextNode(' · '+p.reason));$('dividend-exclusions').append(line);}
 if(!data.coverage.excluded.length)$('dividend-exclusions').textContent=ui('Alle open posities in deze valuta hebben een bruikbare basis.');renderDividendLedger();
}
function openDividendMonth(point,currency,expected){
 const panel=$('dividend-month-details');
 panel.replaceChildren(dividendNode('h3',dividendMonth(point.month)),dividendNode('p',money(point.amount,currency)));
 const rows=expected?point.companies:(dividendCurrency==='ALL'?dividendData.combined.ledger:state.dividends)
  .filter(row=>row.paid_on.slice(0,7)===point.month&&row.paid_on<=dividendData.as_of&&row.currency===currency&&(dividendAccount==='all'||String(row.account_id)===dividendAccount))
  .sort((a,b)=>b.paid_on.localeCompare(a.paid_on)||b.id-a.id);
 if(!rows.length)panel.append(dividendNode('p',expected?ui('Nog geen bruikbare historie voor een verwachting.'):ui('Nog geen ontvangen dividend.')));
 for(const row of rows){
  const item=dividendNode('div',undefined,'dividend-contributor'),identity=dividendNode('div');
  const link=dividendNode('a',row.name||row.symbol);link.href=stockDetailLink(row);
  link.addEventListener('click',()=>closePopup(panel.id));
  const account=row.account_name||state.accounts.find(a=>a.id===row.account_id)?.name||'';
  identity.append(link,dividendNode('small',expected?account:dayLabel(row.paid_on)+' · '+account));
  if(!expected&&row.note)identity.append(dividendNode('small',row.note));
  item.append(identity,dividendNode('strong',money(row.amount,currency)));panel.append(item);
 }
 openPopup(panel.id);
}
const dividendLogoDomains={
 'TDIV.AS':'vaneck.com','TDT.AS':'vaneck.com','EXSA.DE':'ishares.com',
 'ABEA.DE':'google.com','ABEA.F':'google.com','SAB.MC':'bancsabadell.com'
};
async function loadDividendLogo(mark,company){
 const local=localCompanyLogo(company.name);
 const image=dividendNode('img');image.alt='';image.referrerPolicy='no-referrer';
 image.onload=()=>{if(mark.isConnected)mark.replaceChildren(image);};
 async function loadRemote(){
  const domain=Object.hasOwn(dividendLogoDomains,company.symbol)?dividendLogoDomains[company.symbol]:
   await lookupCompanyDomain({...company,currency:company.native_currency||company.currency});
  if(mark.isConnected&&domain)image.src=companyLogoUrl(domain);
 }
 if(local){
  image.onerror=()=>{image.onerror=null;loadRemote().catch(()=>{});};
  image.src=local;
 }else await loadRemote();
}
function bindDividendMonth(){
 const panel=dividendNode('section',undefined,'popup-content');panel.id='dividend-month-details';
 document.body.append(panel);registerPopup(panel.id,ui('Dividend'));
}
function renderDividendLedger(){
 const rows=(dividendCurrency==='ALL'?(dividendData?.combined?.ledger||[]):(state?.dividends||[]).filter(d=>d.currency===dividendCurrency)).slice().sort((a,b)=>b.paid_on.localeCompare(a.paid_on)||b.id-a.id);$('dividends').replaceChildren();for(const d of rows.slice(0,dividendLedgerLimit)){const row=document.createElement('tr'),position=state.positions.find(p=>p.account_id===d.account_id&&p.symbol===d.symbol&&p.exchange===d.exchange&&p.currency===(d.native_currency||d.currency));const day=cell(row,dayLabel(d.paid_on));day.dataset.sortValue=d.paid_on;const identity=cell(row,''),link=dividendNode('a',(position?.name||d.symbol)+' · '+(state.accounts.find(a=>a.id===d.account_id)?.name||''));link.href=stockDetailLink(d);identity.append(link);const amount=cell(row,money(d.amount,d.currency));amount.dataset.sortValue=d.amount;if(d.native_currency&&d.native_currency!=='EUR')amount.append(dividendNode('small',money(d.source_amount,d.native_currency)));cell(row,d.note);$('dividends').append(row);}
 $('dividend-ledger-count').textContent=Math.min(rows.length,dividendLedgerLimit)+ui(' van ')+rows.length+ui(' betalingen · ')+(dividendCurrency==='ALL'?ui('alle valuta’s in EUR'):dividendCurrency);$('dividend-empty').textContent=rows.length?'':ui('Nog geen ontvangen dividend geboekt in deze selectie.');$('dividend-more').hidden=rows.length<=dividendLedgerLimit;
}
function dividendBarChart(chartId,detailId,points,currency,expected){
 const svg=$(chartId),detail=$(detailId);svg.replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;svg.onclick=null;
 if(!points.length){detail.textContent=expected?ui('Nog geen bruikbare historie voor een verwachting.'):ui('Nog geen ontvangen dividend.');return;}
 const width=Math.max(360,Math.round(svg.getBoundingClientRect().width||900)),height=270,left=82,right=width-16,top=20,bottom=220,max=Math.max(1,...points.map(p=>Number(p.amount)))*1.12,slot=(right-left)/points.length;
 svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('aria-label',(expected?ui('Geschat'):ui('Ontvangen'))+ui(' dividend in ')+currency+ui('. Gebruik links en rechts voor maandbedragen.'));
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 for(let i=0;i<=4;i++){const y=bottom-(bottom-top)*i/4;node('line',{x1:left,x2:right,y1:y,y2:y,stroke:'#293951','stroke-dasharray':'3 5'});node('text',{x:left-10,y:y+4,fill:'#a7b6cc','font-size':10,'text-anchor':'end'},money(max*i/4,currency));}
 const bars=[];points.forEach((p,i)=>{const value=Number(p.amount),height=(bottom-top)*value/max;bars.push(node('rect',{x:left+i*slot+slot*.18,y:bottom-height,width:Math.max(1,slot*.64),height:Math.max(0,height),rx:Math.min(4,slot*.12),fill:expected?'#70b7ff':'#47dcb0',opacity:.85}));if(i%Math.max(1,Math.ceil(points.length/(width<550?4:8)))===0)node('text',{x:left+(i+.5)*slot,y:250,fill:'#a7b6cc','font-size':10,'text-anchor':'middle'},dividendMonth(p.month));});
 let cursor=points.length-1;function show(index){cursor=index;bars.forEach((bar,i)=>bar.setAttribute('opacity',i===index?'1':'.65'));detail.textContent=dividendMonth(points[index].month)+' · '+money(points[index].amount,currency)+(expected?ui(' geschat'):ui(' ontvangen'));}
 function monthIndex(event){const matrix=svg.getScreenCTM();if(!matrix)return null;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());return Math.max(0,Math.min(points.length-1,Math.floor((point.x-left)/slot)));}
 svg.onpointermove=event=>{const index=monthIndex(event);if(index!==null)show(index);};
 svg.onclick=event=>{if(!expected&&bars.includes(event.target))openDividendMonth(points[bars.indexOf(event.target)],currency,false);};
 svg.onkeydown=event=>{if(!expected&&['Enter',' '].includes(event.key)){event.preventDefault();openDividendMonth(points[cursor],currency,false);return;}if(!['ArrowLeft','ArrowRight',ui('Home'),'End'].includes(event.key))return;event.preventDefault();show(event.key===ui('Home')?0:event.key==='End'?points.length-1:Math.max(0,Math.min(points.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};detail.textContent=(expected?ui('Geschat: '):ui('Ontvangen: '))+money(points.reduce((sum,p)=>sum+Number(p.amount),0),currency)+' · '+points.length+ui(' maanden. Beweeg over de grafiek of gebruik de pijltjestoetsen.');
}
$('dividend-history-range').addEventListener('change',drawDividendDashboard);$('dividend-forecast-range').addEventListener('change',drawDividendDashboard);$('dividend-more').addEventListener('click',()=>{dividendLedgerLimit+=100;renderDividendLedger();});
window.addEventListener('resize',()=>{if(location.hash==='#dividend'&&dividendData)requestAnimationFrame(drawDividendDashboard);});

$('dividend-growth').addEventListener('change',drawDividendDashboard);
