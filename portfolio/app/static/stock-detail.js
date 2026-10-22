/* One listing, shared market history, and events scoped to the chosen broker. */
let stockDetail=null,stockDetailRequest=0,categoryTarget=null;
const categoryLabels={sector:'Sector',country:'Land',asset_type:'Type belegging',category:'Eigen categorie'};
function stockDetailLink(p){return '#aandeel?'+new URLSearchParams({symbol:p.symbol,exchange:p.exchange,currency:p.currency});}
function clearStockDetail(){stockDetailRequest++;stockDetail=null;categoryTarget=null;$('stock-detail-content').hidden=true;$('stock-events').replaceChildren();$('stock-price-chart').replaceChildren();$('stock-price-chart').onpointermove=null;$('stock-price-chart').onpointerleave=null;$('stock-price-chart').onkeydown=null;$('stock-custom-categories').replaceChildren();$('stock-detail-categories').replaceChildren();for(const id of ['stock-detail-name','stock-detail-identity','stock-detail-feedback','stock-price-latest','stock-price-note','stock-price-detail','stock-events-note','stock-category-title','stock-category-feedback','stock-category-api-status'])$(id).textContent='';$('stock-category-form').reset();closePopup('stock-category-editor');}
async function loadStockDetail(){
 const params=new URLSearchParams(location.hash.split('?')[1]||'');if(!['symbol','exchange','currency'].every(k=>params.get(k))){clearStockDetail();$('stock-detail-feedback').textContent='Open een aandeel vanuit de aandelenlijst.';return;}
 const request=++stockDetailRequest,route=location.hash;params.set('account_id',currentBroker);
 stockDetail=null;$('stock-detail-content').hidden=true;$('stock-detail-feedback').textContent='Aandeel laden…';
 try{const response=await apiFetch('api/instrument?'+params);const data=await response.json();if(!response.ok)throw Error(data.error);if(request!==stockDetailRequest||route!==location.hash||!accessSession?.user)return;
  stockDetail=data;$('stock-detail-content').hidden=false;$('stock-detail-feedback').textContent='';$('stock-detail-name').textContent=data.name;document.title=data.name+' · Home Invest';$('stock-detail-identity').textContent=data.symbol+' · '+data.exchange+' · '+data.currency+' · '+(currentBroker==='all'?'Alle brokeraccounts':state.accounts.find(a=>String(a.id)===String(currentBroker))?.name||'Brokeraccount');
  const sync=data.category_sync||{status:'pending'},missing=Object.keys(categoryLabels).filter(field=>field!=='category'&&!data.categories[field]).map(field=>categoryLabels[field]);
  $('stock-category-api-status').textContent=sync.status==='pending'?'Sector, land en type belegging worden eenmalig opgehaald bij de automatische koerscontrole.':sync.status==='fetching'?'Automatische categorieën worden opgehaald…':sync.status==='retry'?'Automatisch ophalen is nog niet gelukt ('+(sync.error_code||'providerfout')+'). De app probeert het na de wachttijd opnieuw. Bekijk bij aanhoudende fouten de diagnostische logs.':'Eenmalig via Yahoo Finance opgehaald op '+new Date(sync.attempted_at).toLocaleString('nl-NL')+'.'+(missing.length?' Nog niet ingedeeld: '+missing.join(', ')+'. De API levert niet voor iedere belegging alle velden; je kunt deze aanvullen.':'');
  $('stock-category-open').hidden=accessSession.user.role!=='admin';$('stock-detail-categories').replaceChildren();
  for(const [field,label] of Object.entries(categoryLabels)){const group=document.createElement('div'),term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;value.textContent=data.categories[field]||'Niet ingedeeld';group.append(term,value);$('stock-detail-categories').append(group);}
  $('stock-events').replaceChildren();for(const event of data.events){const row=document.createElement('tr');let note=event.note||'';if(event.type==='SPLIT')note='Aantal vóór splitsing: '+(event.split_before==='0'?'niet in bronbestand':quantityLabel(event.split_before))+' → '+quantityLabel(event.quantity);
   for(const value of [event.day+(event.trade_time?' '+event.trade_time.slice(11,19):''),transactionLabels[event.type]||event.type,event.account_name,event.quantity==null?'—':quantityLabel(event.quantity),event.amount?money(event.amount,event.currency):event.type==='SPLIT'||!event.price?'—':money(event.price,event.currency),event.currency||'—',event.status,note])cell(row,value);$('stock-events').append(row);
  }
  $('stock-events-note').textContent=data.events.length+' gebeurtenissen: aankopen, verkopen, dividend, splitsingen en gekoppelde kapitaalterugbetalingen.'+(accessSession.user.role==='admin'?' Ook gekoppelde regels die nog te beoordelen zijn worden getoond. Bronregels zonder eenduidige aandelenkoppeling staan bij Imports → Te beoordelen.':'');
  drawStockPrice();
 }catch(error){if(request===stockDetailRequest){stockDetail=null;$('stock-detail-feedback').textContent=error.message||'Aandeel laden mislukt.';}}
}
function drawStockPrice(){
 const svg=$('stock-price-chart');svg.replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;$('stock-price-detail').textContent='';if(!stockDetail)return;
 const data=stockDetail,observations=data.prices.map(p=>({...p,source:'Slotkoers'})),quote=data.quote;
 if(quote){const day=quote.quoted_at.slice(0,10),today=new Date().toISOString().slice(0,10);if(!observations.length||day>observations.at(-1).day)observations.push({day,price:quote.price,source:'Koersmeting'});else if(day===today&&day===observations.at(-1).day)observations[observations.length-1]={day,price:quote.price,source:'Koersmeting'};}
 $('stock-price-latest').textContent=quote?'Laatste koers: '+money(quote.price,data.currency)+' · '+new Date(quote.quoted_at).toLocaleString('nl-NL'):(observations.length?'Laatste opgeslagen slotkoers: '+money(observations.at(-1).price,data.currency)+' · '+dayLabel(observations.at(-1).day):'Nog geen koers beschikbaar.');
 const points=chartPeriodPoints(observations,$('stock-price-range').value);$('stock-price-note').textContent=points.length?dayLabel(points[0].day)+' — '+dayLabel(points.at(-1).day)+' · '+points.length+' koerspunten · '+data.currency:'Geen opgeslagen koersen voor deze periode.';
 if(!points.length)return;
 const width=Math.max(360,Math.round(svg.getBoundingClientRect().width||900)),height=330,left=90,right=width-16,top=22,bottom=280;
 svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('aria-label','Koersgrafiek '+data.name+' in '+data.currency+'. Gebruik links en rechts voor de koersen.');
 const prices=points.map(p=>Number(p.price)),min=Math.min(...prices),max=Math.max(...prices),padding=Math.max((max-min)*.12,Math.abs(max)*.01,.0001),low=Math.max(0,min-padding),high=max+padding;
 const x=i=>left+(points.length===1?.5:i/(points.length-1))*(right-left),y=value=>bottom-(value-low)/(high-low)*(bottom-top);
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 const priceLabel=value=>new Intl.NumberFormat('nl-NL',{style:'currency',currency:data.currency,maximumFractionDigits:6}).format(Number(value));
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#293951','stroke-dasharray':'3 5'});node('text',{x:left-10,y:y(value)+4,'text-anchor':'end',fill:'#a7b6cc','font-size':11},priceLabel(value));}
 for(const i of [...new Set([0,Math.floor((points.length-1)/2),points.length-1])])node('text',{x:x(i),y:height-20,'text-anchor':i===0?'start':i===points.length-1?'end':'middle',fill:'#a7b6cc','font-size':11},dayLabel(points[i].day));
 node('path',{d:points.map((p,i)=>(i?'L':'M')+x(i)+' '+y(Number(p.price))).join(' '),fill:'none',stroke:'#47dcb0','stroke-width':2.5,'stroke-linejoin':'round'});if(points.length===1)node('circle',{cx:x(0),cy:y(prices[0]),r:4,fill:'#47dcb0'});
 let cursor=points.length-1;const guide=node('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:bottom,stroke:'#a7b6cc','stroke-dasharray':'4 4',visibility:'hidden'});
 function detail(index){cursor=index;guide.setAttribute('x1',x(index));guide.setAttribute('x2',x(index));guide.setAttribute('visibility','visible');$('stock-price-detail').textContent=dayLabel(points[index].day)+' · '+priceLabel(points[index].price)+' · '+points[index].source;}
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());detail(points.length===1?0:Math.max(0,Math.min(points.length-1,Math.round((point.x-left)/(right-left)*(points.length-1)))));};svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');svg.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();detail(event.key==='Home'?0:event.key==='End'?points.length-1:Math.max(0,Math.min(points.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};
 $('stock-price-detail').textContent='Beweeg over de grafiek of gebruik de pijltjestoetsen voor de dagkoersen.';
}
$('stock-price-range').addEventListener('change',drawStockPrice);
window.addEventListener('resize',()=>{if(location.hash.startsWith('#aandeel?'))requestAnimationFrame(drawStockPrice);});
$('stock-category-open').addEventListener('click',()=>{
 if(!stockDetail||accessSession?.user?.role!=='admin')return;categoryTarget={symbol:stockDetail.symbol,exchange:stockDetail.exchange,currency:stockDetail.currency};$('stock-category-title').textContent=stockDetail.name+' · '+stockDetail.symbol;
 for(const field of Object.keys(categoryLabels))$('stock-category-form').elements.namedItem(field).value=stockDetail.categories[field]||'';
 $('stock-custom-categories').replaceChildren();for(const category of [...new Set((state.instrument_categories||[]).map(c=>c.category).filter(Boolean))].sort()){const option=document.createElement('option');option.value=category;$('stock-custom-categories').append(option);}
 $('stock-category-feedback').textContent='Deze indeling wordt gedeeld door alle brokeraccounts met dezelfde beursnotering. Handmatige wijzigingen aan sector, land of type blijven behouden bij automatisch aanvullen. Je eigen categorie wordt niet door de API ingevuld.';openPopup('stock-category-editor');
});
$('stock-category-cancel').addEventListener('click',()=>closePopup('stock-category-editor'));
$('stock-category-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!categoryTarget)return;const target={...categoryTarget},button=event.target.querySelector('button[type="submit"]');button.disabled=true;
 try{await jsonAction('api/instrument/categories',{...target,...Object.fromEntries(new FormData(event.target))});closePopup('stock-category-editor');stateETag=null;await load();}catch(error){$('stock-category-feedback').textContent=error.message;}finally{button.disabled=false;}
});
