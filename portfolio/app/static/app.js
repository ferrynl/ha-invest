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
function draw(){
 const svg=$('chart');svg.replaceChildren();const p=state.positions[Number($('instrument').value)];if(!p)return;
 const points=state.quotes.filter(q=>q.symbol===p.symbol&&q.exchange===p.exchange&&q.currency===p.currency).map(q=>{const lots=state.purchases.filter(l=>l.symbol===p.symbol&&l.exchange===p.exchange&&l.currency===p.currency&&l.purchased_on<=q.quoted_at.slice(0,10));return {time:new Date(q.quoted_at).getTime(),value:lots.reduce((s,l)=>s+Number(l.quantity),0)*Number(q.price),cost:lots.reduce((s,l)=>s+Number(l.quantity)*Number(l.price),0)};}).filter(x=>x.cost>0);
 $('chartnote').textContent=points.length?new Date(points[0].time).toLocaleString('nl-NL')+' — '+new Date(points.at(-1).time).toLocaleString('nl-NL')+' · '+p.currency:'Nog geen koershistorie. De grafiek begint zodra een koers na je aankoop is opgeslagen.';
 if(!points.length)return;
 const values=points.flatMap(x=>[x.value,x.cost]),low=Math.min(...values)*.98,high=Math.max(...values)*1.02,span=high-low||1,start=points[0].time,end=points.at(-1).time;
 for(const [field,color] of [['cost','#8694ac'],['value','#4de0b3']]){const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');line.setAttribute('points',points.map(x=>`${40+(end===start?0.5:(x.time-start)/(end-start))*820},${210-(x[field]-low)/span*180}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke',color);line.setAttribute('stroke-width','3');svg.append(line);if(points.length===1){const dot=document.createElementNS(svg.namespaceURI,'circle');dot.setAttribute('cx','450');dot.setAttribute('cy',String(210-(points[0][field]-low)/span*180));dot.setAttribute('r','5');dot.setAttribute('fill',color);svg.append(dot);}}
}
$('instrument').addEventListener('change',draw);
$('purchase').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const response=await fetch('api/purchases',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))});const result=await response.json();if(!response.ok)throw Error(result.error);$('feedback').textContent='Aankoop opgeslagen. De koers wordt opgehaald; het overzicht ververst automatisch.';event.target.reset();await load();}catch(error){$('feedback').textContent=error.message;}finally{button.disabled=false;}});
load();setInterval(load,60000);
