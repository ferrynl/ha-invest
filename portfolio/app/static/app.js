let state;
const $ = id => document.getElementById(id);
const money = (n,c) => n === null ? 'Nog geen koers' : new Intl.NumberFormat('nl-NL',{style:'currency',currency:c}).format(Number(n));
function cell(row,value){const td=document.createElement('td');td.textContent=value;row.append(td);return td;}
async function load(){
 try{
 const response=await fetch('api/state');if(!response.ok)throw Error();state=await response.json();
 $('status').textContent=state.status.message+' Automatische controle elke '+state.refresh_minutes+' minuten.';
 $('positions').replaceChildren();$('purchases').replaceChildren();$('totals').replaceChildren();
 const totals={};
 for(const p of state.positions){
  const row=document.createElement('tr');cell(row,p.name+' · '+p.symbol);cell(row,p.quantity);cell(row,money(p.cost,p.currency));cell(row,p.quote?money(p.quote.price,p.currency):'—');cell(row,money(p.value,p.currency));cell(row,p.gain===null?'—':money(p.gain,p.currency)).className=Number(p.gain)>=0?'positive':'negative';cell(row,p.quote?new Date(p.quote.quoted_at).toLocaleString('nl-NL'):'Wacht op koers');$('positions').append(row);
  const t=totals[p.currency]??={cost:0,value:0,missing:0};t.cost+=Number(p.cost);if(p.value===null)t.missing++;else t.value+=Number(p.value);
 }
 for(const [currency,t] of Object.entries(totals)){const box=document.createElement('article');box.className='total';const label=document.createElement('small');label.textContent='PORTEFEUILLE · '+currency;const amount=document.createElement('strong');amount.textContent=t.missing?'Waarde onvolledig':money(t.value,currency);const detail=document.createElement('div');detail.textContent='Inleg '+money(t.cost,currency)+(t.missing?' · '+t.missing+' zonder koers':' · Resultaat '+money(t.value-t.cost,currency));box.append(label,amount,detail);$('totals').append(box);}
 for(const p of state.purchases){const row=document.createElement('tr');for(const v of [p.purchased_on,p.name+' · '+p.symbol,p.exchange,p.quantity,money(p.price,p.currency)])cell(row,v);$('purchases').append(row);}
 $('empty').textContent=state.positions.length?'':'Voeg je eerste aankoop toe. Er worden geen voorbeeldbedragen als echte gegevens opgeslagen.';
 const selected=$('instrument').value;$('instrument').replaceChildren();state.positions.forEach((p,i)=>{const o=document.createElement('option');o.value=i;o.textContent=p.name+' · '+p.currency;$('instrument').append(o);});if(selected&&Number(selected)<state.positions.length)$('instrument').value=selected;draw();
 }catch{$('status').textContent='Gegevens laden mislukt. Probeer de pagina opnieuw te openen.';}
}
let chartRange='1M';
const dayLabel=day=>new Date(day+'T00:00:00Z').toLocaleDateString('nl-NL',{timeZone:'UTC'});
function draw(){
 const svg=$('chart');svg.replaceChildren();$('chart-days').replaceChildren();svg.onpointermove=null;
 const p=state.positions[Number($('instrument').value)];if(!p){$('chartnote').textContent='Voeg een aankoop toe om de historie te bekijken.';return;}
 const points=chartPeriodPoints(p.history??[],chartRange);
 const known=points.filter(point=>point.value!==null);
 $('chartnote').textContent=points.length?dayLabel(points[0].day)+' — '+dayLabel(points.at(-1).day)+' · '+points.length+' kalenderdagen · '+p.currency:'';
 if(!known.length)$('chartnote').textContent+=' Historische koersen worden opgehaald. Bij een storing probeert de app het bij de volgende controle opnieuw.';
 else if(known.length<points.length)$('chartnote').textContent+=' Voor '+(points.length-known.length)+' dag(en) ontbreekt nog een koers.';
 $('chart-detail').textContent='Beweeg over de grafiek of bekijk de dagwaarden hieronder.';
 for(const point of points){const row=document.createElement('tr');for(const value of [dayLabel(point.day),money(point.price,p.currency),money(point.value,p.currency),money(point.cost,p.currency),point.value===null?'—':money(Number(point.value)-Number(point.cost),p.currency),point.price===null?'Koers ontbreekt':point.carried?'Laatst bekende koers':'Dagkoers'])cell(row,value);$('chart-days').append(row);}
 if(!points.length)return;
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 const values=points.flatMap(point=>point.value===null?[Number(point.cost)]:[Number(point.value),Number(point.cost)]);
 const min=Math.min(...values),max=Math.max(...values),padding=Math.max((max-min)*.1,max*.01,1),low=Math.max(0,min-padding),high=max+padding;
 const x=i=>90+(points.length===1?.5:i/(points.length-1))*790,y=value=>250-(Number(value)-low)/(high-low)*220;
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:90,x2:880,y1:y(value),y2:y(value),stroke:'#293951'});node('text',{x:80,y:y(value)+4,'text-anchor':'end',fill:'#9eacc2','font-size':12},money(value,p.currency));}
 const ticks=[...new Set([0,Math.floor((points.length-1)/2),points.length-1])];
 for(const i of ticks)node('text',{x:x(i),y:280,'text-anchor':i===0?'start':i===points.length-1?'end':'middle',fill:'#9eacc2','font-size':12},dayLabel(points[i].day));
 for(const [field,color] of [['cost','#8694ac'],['value','#4de0b3']]){
  let path='',started=false;points.forEach((point,i)=>{if(point[field]===null){started=false;return;}path+=(started?'L':'M')+x(i)+' '+y(point[field])+' ';started=true;});
  node('path',{d:path,fill:'none',stroke:color,'stroke-width':3,'stroke-linejoin':'round'});
  if(points.length===1&&points[0][field]!==null)node('circle',{cx:x(0),cy:y(points[0][field]),r:5,fill:color});
 }
 const guide=node('line',{x1:90,x2:90,y1:25,y2:250,stroke:'#9eacc2','stroke-dasharray':'4 4',visibility:'hidden'});
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const location=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());const i=points.length===1?0:Math.max(0,Math.min(points.length-1,Math.round((location.x-90)/790*(points.length-1))));const point=points[i];guide.setAttribute('x1',x(i));guide.setAttribute('x2',x(i));guide.setAttribute('visibility','visible');$('chart-detail').textContent=dayLabel(point.day)+' · Waarde '+money(point.value,p.currency)+' · Inleg '+money(point.cost,p.currency)+(point.carried?' · Laatst bekende koers':' · Dagkoers');};
 svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');
}
$('chart-ranges').addEventListener('click',event=>{const button=event.target.closest('button[data-range]');if(!button)return;chartRange=button.dataset.range;for(const choice of $('chart-ranges').querySelectorAll('button'))choice.setAttribute('aria-pressed',String(choice===button));draw();});
$('instrument').addEventListener('change',draw);
let selectedStock=null,searchTimer,searchController,searchVersion=0;
const stockFields=['name','symbol','exchange','currency'];
function closeSearch(){ $('search-results').replaceChildren();$('search-results').hidden=true;$('stock-search').setAttribute('aria-expanded','false'); }
function clearSelection(){selectedStock=null;for(const field of stockFields)$('purchase').elements.namedItem(field).value='';}
function chooseStock(stock){
 selectedStock=stock;for(const field of stockFields)$('purchase').elements.namedItem(field).value=stock[field];
 $('stock-search').value=stock.name;closeSearch();$('search-status').textContent=stock.symbol+' · '+stock.exchange+' · '+stock.currency+' geselecteerd.';$('purchase').elements.namedItem('quantity').focus();
}
$('stock-search').addEventListener('input',()=>{
 clearTimeout(searchTimer);searchController?.abort();const version=++searchVersion;clearSelection();closeSearch();
 const query=$('stock-search').value.trim();
 if(query.length<2){$('search-status').textContent='Typ minimaal twee letters van een bedrijfsnaam of symbool.';return;}
 $('search-status').textContent='Aandelen zoeken…';
 searchTimer=setTimeout(async()=>{
  searchController=new AbortController();
  try{
   const response=await fetch('api/search?q='+encodeURIComponent(query),{signal:searchController.signal});const data=await response.json();
   if(version!==searchVersion)return;if(!response.ok)throw Error(data.error);
   for(const stock of data.results){const button=document.createElement('button');button.type='button';button.setAttribute('role','option');button.setAttribute('aria-selected','false');button.textContent=stock.name+' · '+stock.symbol+' · '+stock.exchange+' · '+stock.currency;button.addEventListener('click',()=>chooseStock(stock));$('search-results').append(button);}
   $('search-results').hidden=!data.results.length;$('stock-search').setAttribute('aria-expanded',String(Boolean(data.results.length)));
   $('search-status').textContent=data.results.length?data.results.length+' resultaten van Yahoo voor Amsterdam, Nasdaq en NYSE. Kies de juiste beursnotering; typ verder om te verfijnen.':'Geen passende aandelen gevonden op deze beurzen. Probeer meer letters of het symbool.';
  }catch(error){if(error.name!=='AbortError'&&version===searchVersion)$('search-status').textContent=error.message||'Zoeken mislukt. Probeer opnieuw.';}
 },350);
});
$('stock-search').addEventListener('keydown',event=>{if(event.key==='ArrowDown'){const first=$('search-results').querySelector('button');if(first){event.preventDefault();first.focus();}}if(event.key==='Escape'){clearTimeout(searchTimer);searchController?.abort();searchVersion++;closeSearch();}if(event.key==='Enter'){event.preventDefault();$('search-results').querySelector('button')?.focus();}});
$('search-results').addEventListener('keydown',event=>{const buttons=[...$('search-results').querySelectorAll('button')],index=buttons.indexOf(document.activeElement);if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();buttons[(index+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(event.key==='Escape'){closeSearch();$('stock-search').focus();}});
$('purchase').addEventListener('submit',async event=>{event.preventDefault();if(!selectedStock){$('feedback').textContent='Zoek en selecteer eerst een aandeel.';$('stock-search').focus();return;}const button=event.target.querySelector('button[type="submit"]');button.disabled=true;try{const response=await fetch('api/purchases',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))});const result=await response.json();if(!response.ok)throw Error(result.error);$('feedback').textContent='Aankoop opgeslagen. De koers wordt opgehaald; het overzicht ververst automatisch.';event.target.reset();clearSelection();closeSearch();$('search-status').textContent='Zoek op bedrijfsnaam of symbool. Amsterdam, Nasdaq en NYSE.';await load();}catch(error){$('feedback').textContent=error.message;}finally{button.disabled=false;}});
load();setInterval(load,60000);
