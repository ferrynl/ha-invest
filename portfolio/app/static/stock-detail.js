/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
/* One listing, shared market history, and events scoped to the chosen broker. */
let stockDetail=null,stockDetailRequest=0,categoryTarget=null;
const categoryLabels={sector:ui('Sector'),country:ui('Land'),asset_type:ui('Type belegging'),category:ui('Eigen categorie')};
function stockDetailLink(p){return '#aandeel?'+new URLSearchParams({symbol:p.symbol,exchange:p.exchange,currency:p.native_currency??p.currency});}
function clearStockDetail(){closePopup('stock-valuation-editor');$('stock-valuation-form').reset();$('stock-valuation-status').textContent='';$('stock-valuation-feedback').textContent='';$('stock-detail-metrics').replaceChildren();$('stock-company-description').textContent='';$('stock-company-logo').onload=null;$('stock-company-logo').onerror=null;$('stock-company-logo').removeAttribute('src');stockDetailRequest++;stockDetail=null;categoryTarget=null;$('stock-detail-content').hidden=true;$('stock-events').replaceChildren();$('stock-price-chart').replaceChildren();$('stock-price-chart').onpointermove=null;$('stock-price-chart').onpointerleave=null;$('stock-price-chart').onkeydown=null;$('stock-custom-categories').replaceChildren();$('stock-detail-categories').replaceChildren();for(const id of ['stock-detail-name','stock-detail-identity','stock-detail-feedback','stock-price-latest','stock-price-note','stock-price-detail','stock-events-note','stock-category-title','stock-category-feedback'])$(id).textContent='';$('stock-category-form').reset();closePopup('stock-category-editor');}
async function loadStockDetail(){
 const params=new URLSearchParams(location.hash.split('?')[1]||'');if(!['symbol','exchange','currency'].every(k=>params.get(k))){clearStockDetail();$('stock-detail-feedback').textContent=ui('Open een aandeel vanuit de aandelenlijst.');return;}
 const request=++stockDetailRequest,route=location.hash;params.set('account_id',currentBroker);
 stockDetail=null;$('stock-detail-content').hidden=true;$('stock-detail-feedback').textContent=ui('Aandeel laden…');
 try{const response=await apiFetch('api/instrument?'+params);const data=await response.json();if(!response.ok)throw Error(data.error);if(request!==stockDetailRequest||route!==location.hash||!accessSession?.user)return;
  stockDetail=data;$('stock-detail-content').hidden=false;$('stock-detail-feedback').textContent='';$('stock-detail-name').textContent=data.name;document.title=data.name+' · Home Invest';$('stock-detail-identity').textContent=data.symbol+' · '+data.exchange+' · '+data.currency+(currentBroker==='all'?ui(' · Alle brokeraccounts'):' · '+(state.accounts.find(a=>String(a.id)===String(currentBroker))?.name||''));
  renderStockMetrics(data);
  $('stock-conversion-link').hidden=accessSession.user.role!=='admin'||data.symbol!=='TMX.AS'||data.exchange!=='AMSTERDAM';
  $('stock-valuation-open').hidden=accessSession.user.role!=='admin';$('stock-valuation-status').textContent=data.manual_valuation?ui('Handmatige laatste koers: ')+money(data.manual_valuation.price,data.currency)+' · '+dayLabel(data.manual_valuation.day)+ui(' · automatisch ophalen uitgeschakeld.'):data.exchange==='PRIVATE'?(data.symbol==='LU3170240538'&&data.currency==='EUR'?ui('Apollo · automatisch via DivvyDiary. De bron vermeldt geen koersdatum; de getoonde datum is het ophaalmoment.'):ui('Niet-beursgenoteerd fonds · actuele fondskoers handmatig instellen.')):'';
  $('stock-company-description').textContent=ui('Bedrijfsinformatie laden…');$('stock-company-logo').hidden=true;$('stock-company-logo').onload=null;$('stock-company-logo').onerror=null;$('stock-company-logo').removeAttribute('src');$('stock-company-initials').hidden=false;$('stock-company-initials').textContent=data.name.split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase();
  loadStockCompany(params,request,route);
  $('stock-fundamentals-panel').hidden=!data.fundamentals_supported;
  if(data.fundamentals_supported)loadStockFundamentals(params,request,route);
  $('stock-category-open').hidden=accessSession.user.role!=='admin';$('stock-detail-categories').replaceChildren();
  for(const [field,label] of Object.entries(categoryLabels)){const group=document.createElement('div'),term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;value.textContent=data.categories[field]||ui('Niet ingedeeld');group.append(term,value);$('stock-detail-categories').append(group);}
  $('stock-events').replaceChildren();for(const event of data.events){const row=document.createElement('tr');let note=event.note||'';if(event.type==='SPLIT')note=ui('Aantal vóór splitsing: ')+(event.split_before==='0'?ui('niet in bronbestand'):quantityLabel(event.split_before))+' → '+quantityLabel(event.quantity);
   for(const value of [event.day+(event.trade_time?' '+event.trade_time.slice(11,19):''),transactionLabels[event.type]||event.type,event.account_name,event.quantity==null?'—':quantityLabel(event.quantity),event.amount?money(event.amount,event.currency):event.type==='SPLIT'||event.type==='TRANSFER'||!event.price?'—':money(event.price,event.currency),event.currency||'—',event.status,note])cell(row,value);$('stock-events').append(row);
  }
  $('stock-events-note').textContent=data.events.length+ui(' gebeurtenissen: aankopen, verkopen, dividend, splitsingen en gekoppelde kapitaalterugbetalingen.')+(accessSession.user.role==='admin'?ui(' Ook gekoppelde regels die nog te beoordelen zijn worden getoond. Bronregels zonder eenduidige aandelenkoppeling staan bij Imports → Te beoordelen.'):'');
  drawStockPrice();
 }catch(error){if(request===stockDetailRequest){stockDetail=null;$('stock-detail-feedback').textContent=error.message||ui('Aandeel laden mislukt.');}}
}
function drawStockPrice(){
 const svg=$('stock-price-chart');svg.replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;$('stock-price-detail').textContent='';if(!stockDetail)return;
 const data=stockDetail,observations=data.prices.map(p=>({...p,source:ui('Slotkoers')})),quote=data.quote;
 if(quote){const day=quote.quoted_at.slice(0,10),today=new Date().toISOString().slice(0,10);if(!observations.length||day>observations.at(-1).day)observations.push({day,price:quote.price,source:ui('Koersmeting')});else if(day===today&&day===observations.at(-1).day)observations[observations.length-1]={day,price:quote.price,source:ui('Koersmeting')};}
 $('stock-price-latest').textContent=quote?ui('Laatste koers: ')+money(quote.price,data.currency)+' · '+new Date(quote.quoted_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')):(observations.length?ui('Laatste opgeslagen slotkoers: ')+money(observations.at(-1).price,data.currency)+' · '+dayLabel(observations.at(-1).day):ui('Nog geen koers beschikbaar.'));
 const points=chartPeriodPoints(observations,$('stock-price-range').value);$('stock-price-note').textContent=points.length?dayLabel(points[0].day)+' — '+dayLabel(points.at(-1).day)+' · '+points.length+ui(' koerspunten · ')+data.currency:ui('Geen opgeslagen koersen voor deze periode.');
 if(!points.length)return;
 const width=Math.max(360,Math.round(svg.getBoundingClientRect().width||900)),height=330,left=90,right=width-16,top=22,bottom=280;
 svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('aria-label',ui('Koersgrafiek ')+data.name+ui(' in ')+data.currency+ui('. Gebruik links en rechts voor de koersen.'));
 const prices=points.map(p=>Number(p.price)),min=Math.min(...prices),max=Math.max(...prices),padding=Math.max((max-min)*.12,Math.abs(max)*.01,.0001),low=Math.max(0,min-padding),high=max+padding;
 const x=i=>left+(points.length===1?.5:i/(points.length-1))*(right-left),y=value=>bottom-(value-low)/(high-low)*(bottom-top);
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 const priceLabel=value=>new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{style:'currency',currency:data.currency,maximumFractionDigits:6}).format(Number(value));
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#293951','stroke-dasharray':'3 5'});node('text',{x:left-10,y:y(value)+4,'text-anchor':'end',fill:'#a7b6cc','font-size':11},priceLabel(value));}
 for(const i of [...new Set([0,Math.floor((points.length-1)/2),points.length-1])])node('text',{x:x(i),y:height-20,'text-anchor':i===0?'start':i===points.length-1?'end':'middle',fill:'#a7b6cc','font-size':11},dayLabel(points[i].day));
 node('path',{d:points.map((p,i)=>(i?'L':'M')+x(i)+' '+y(Number(p.price))).join(' '),fill:'none',stroke:'#47dcb0','stroke-width':2.5,'stroke-linejoin':'round'});if(points.length===1)node('circle',{cx:x(0),cy:y(prices[0]),r:4,fill:'#47dcb0'});
 let cursor=points.length-1;const guide=node('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:bottom,stroke:'#a7b6cc','stroke-dasharray':'4 4',visibility:'hidden'});
 function detail(index){cursor=index;guide.setAttribute('x1',x(index));guide.setAttribute('x2',x(index));guide.setAttribute('visibility','visible');$('stock-price-detail').textContent=dayLabel(points[index].day)+' · '+priceLabel(points[index].price)+' · '+points[index].source;}
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());detail(points.length===1?0:Math.max(0,Math.min(points.length-1,Math.round((point.x-left)/(right-left)*(points.length-1)))));};svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');svg.onkeydown=event=>{if(!['ArrowLeft','ArrowRight',ui('Home'),'End'].includes(event.key))return;event.preventDefault();detail(event.key===ui('Home')?0:event.key==='End'?points.length-1:Math.max(0,Math.min(points.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};
 $('stock-price-detail').textContent=ui('Beweeg over de grafiek of gebruik de pijltjestoetsen voor de dagkoersen.');
}
$('stock-price-range').addEventListener('change',drawStockPrice);
window.addEventListener('resize',()=>{if(location.hash.startsWith('#aandeel?'))requestAnimationFrame(drawStockPrice);});
$('stock-category-open').addEventListener('click',()=>{
 if(!stockDetail||accessSession?.user?.role!=='admin')return;categoryTarget={symbol:stockDetail.symbol,exchange:stockDetail.exchange,currency:stockDetail.currency};$('stock-category-title').textContent=stockDetail.name+' · '+stockDetail.symbol;
 for(const field of Object.keys(categoryLabels))$('stock-category-form').elements.namedItem(field).value=stockDetail.categories[field]||'';
 $('stock-custom-categories').replaceChildren();for(const category of [...new Set((state.instrument_categories||[]).map(c=>c.category).filter(Boolean))].sort()){const option=document.createElement('option');option.value=category;$('stock-custom-categories').append(option);}
 $('stock-category-feedback').textContent=ui('Deze indeling wordt gedeeld door alle brokeraccounts met dezelfde beursnotering. Handmatige wijzigingen aan sector, land of type blijven behouden bij automatisch aanvullen. Je eigen categorie wordt niet door de API ingevuld.');openPopup('stock-category-editor');
});
$('stock-category-cancel').addEventListener('click',()=>closePopup('stock-category-editor'));
$('stock-category-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!categoryTarget)return;const target={...categoryTarget},button=event.target.querySelector('button[type="submit"]');button.disabled=true;
 try{await jsonAction('api/instrument/categories',{...target,...Object.fromEntries(new FormData(event.target))});closePopup('stock-category-editor');stateETag=null;await load();}catch(error){$('stock-category-feedback').textContent=error.message;}finally{button.disabled=false;}
});

function renderStockMetrics(data){
 const summary=data.summary||{};const boxes=$('stock-detail-metrics');boxes.replaceChildren();
 const metrics=[[ui('Aantal'),quantityLabel(summary.quantity),ui('In bezit')],[ui('Waarde in valuta'),summary.value==null?ui('Geen koers beschikbaar'):money(summary.value,data.currency),data.currency],[ui('Waarde in euro'),summary.value_eur==null?ui('Niet beschikbaar'):money(summary.value_eur,'EUR'),summary.fx_day?ui('Wisselkoers van ')+dayLabel(summary.fx_day):ui('Geen wisselkoers beschikbaar')],[ui('Dividend'),money(summary.dividend||'0',data.currency),summary.dividend_percent==null?ui('Totaal ontvangen'):new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{maximumFractionDigits:2}).format(Number(summary.dividend_percent))+ui('% van totale inleg sinds ')+dayLabel(summary.first_purchase)]];
 for(const [label,value,note] of metrics){const box=document.createElement('article');box.className='home-metric';for(const [tag,text,style] of [['span',label,'home-metric-label'],['strong',value,''],['small',note,'']]){const el=document.createElement(tag);el.textContent=text;el.className=style;box.append(el);}boxes.append(box);}
}
async function loadStockCompany(params,request,route){
 try{const response=await apiFetch('api/instrument/company?'+params);if(!response.ok)throw Error();const info=await response.json();if(request!==stockDetailRequest||route!==location.hash||!accessSession?.user)return;
 $('stock-company-description').textContent=info.description||ui('Geen bedrijfsomschrijving beschikbaar.');
 if(info.domain){const image=$('stock-company-logo');image.onload=()=>{if(request!==stockDetailRequest)return;image.hidden=false;$('stock-company-initials').hidden=true;};image.onerror=()=>{image.hidden=true;$('stock-company-initials').hidden=false;};image.src='https://www.google.com/s2/favicons?sz=128&domain='+encodeURIComponent(info.domain);}
 }catch{if(request===stockDetailRequest)$('stock-company-description').textContent=ui('Bedrijfsinformatie is tijdelijk niet beschikbaar.');}
}

function syncValuationForm(){const manual=$('stock-valuation-form').elements.mode.value==='manual';for(const name of ['price','day'])$('stock-valuation-form').elements.namedItem(name).disabled=!manual;}
$('stock-valuation-open').addEventListener('click',()=>{
 if(!stockDetail||accessSession?.user?.role!=='admin')return;
 const form=$('stock-valuation-form'),manual=stockDetail.manual_valuation;form.elements.mode.querySelector('[value="automatic"]').disabled=stockDetail.exchange==='PRIVATE'&&!(stockDetail.symbol==='LU3170240538'&&stockDetail.currency==='EUR');form.elements.mode.value=manual||form.elements.mode.querySelector('[value="automatic"]').disabled?'manual':'automatic';form.elements.price.value=manual?.price??stockDetail.quote?.price??'';form.elements.day.value=manual?.day??stockDetail.quote?.quoted_at.slice(0,10)??new Date().toISOString().slice(0,10);form.elements.day.max=new Date().toISOString().slice(0,10);$('stock-valuation-title').textContent=stockDetail.name+' · '+stockDetail.symbol;$('stock-valuation-currency').textContent=stockDetail.currency;$('stock-valuation-feedback').textContent='';$('stock-valuation-help').textContent=stockDetail.symbol==='LU3170240538'&&stockDetail.exchange==='PRIVATE'&&stockDetail.currency==='EUR'?ui('Automatisch gebruikt de openbare DivvyDiary-koers voor dit ISIN in EUR, maximaal elke zes uur. De bron vermeldt geen koersdatum. Een handmatige fondswaardering heeft voorrang.'):stockDetail.exchange==='PRIVATE'?ui('Vul de intrinsieke waarde per aandeel en de bijbehorende datum in. Dit fonds heeft geen openbare beurskoers. De waardering wordt gedeeld door alle brokeraccounts.'):ui('De laatste koers wordt voor deze beursnotering bij alle brokeraccounts gebruikt. Automatische koers- en historieaanvragen stoppen tot je Automatisch weer inschakelt. Een laatste koers van nul is toegestaan.');syncValuationForm();openPopup('stock-valuation-editor');
});
$('stock-valuation-form').elements.mode.addEventListener('change',syncValuationForm);
$('stock-valuation-cancel').addEventListener('click',()=>closePopup('stock-valuation-editor'));
$('stock-valuation-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!stockDetail)return;const form=event.target,button=form.querySelector('button[type="submit"]');button.disabled=true;
 const target={symbol:stockDetail.symbol,exchange:stockDetail.exchange,currency:stockDetail.currency};
 try{await jsonAction('api/instrument/valuation',{...target,automatic:form.elements.mode.value==='automatic',price:form.elements.price.value,day:form.elements.day.value});closePopup('stock-valuation-editor');stateETag=null;await load();}catch(error){$('stock-valuation-feedback').textContent=error.message;}finally{button.disabled=false;}
});

async function loadStockFundamentals(params,request,route){
 const active=()=>request===stockDetailRequest&&route===location.hash&&!!accessSession?.user;
 $('stock-fundamentals-rows').replaceChildren();$('stock-fundamentals-table').hidden=true;$('stock-fundamentals-source').textContent='';$('stock-fundamentals-status').textContent=ui('Bedrijfscijfers laden…');
 try{
  const response=await apiFetch('api/instrument/fundamentals?'+params);const data=await response.json();if(!active())return;if(!response.ok)throw Error();
  const statuses={unsupported:ui('Defeat Beta ondersteunt hier alleen Amerikaanse beursnoteringen in USD. Voor deze notering zijn geen bedrijfscijfers gekoppeld.'),no_data:ui('Geen jaarcijfers beschikbaar voor deze notering.'),unavailable:ui('Defeat Beta is tijdelijk niet beschikbaar. Probeer later opnieuw.')};
  $('stock-fundamentals-status').textContent=data.status==='ok'?(data.stale?ui('Opgeslagen cijfers; vernieuwen is tijdelijk niet gelukt.'):''):statuses[data.status]||statuses.unavailable;
  if(data.status!=='ok')return;
  $('stock-fundamentals-source').textContent=data.source+' · '+ui('Dataset bijgewerkt: ')+new Date(data.dataset_updated_at).toLocaleString(appLocale())+' · '+ui('Opgehaald: ')+new Date(data.fetched_at).toLocaleString(appLocale());
  for(const period of data.periods){const row=document.createElement('tr');for(const value of [dayLabel(period.day),period.currency,...['revenue','net_income','operating_cash_flow','free_cash_flow'].map(field=>period[field]==null?'—':money(period[field],period.currency)),period.net_margin==null?'—':new Intl.NumberFormat(appLocale(),{maximumFractionDigits:2}).format(Number(period.net_margin))+'%'])cell(row,value);$('stock-fundamentals-rows').append(row);}
  $('stock-fundamentals-table').hidden=false;
 }catch(error){if(active())$('stock-fundamentals-status').textContent=ui('Defeat Beta is tijdelijk niet beschikbaar. Probeer later opnieuw.');}
}
