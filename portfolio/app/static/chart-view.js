/* Multiple holdings share a percentage axis; absolute totals stay per currency. */
function drawDashboardChart(state, range, selection){
 const svg=$('chart');svg.replaceChildren();$('chart-days').replaceChildren();$('chart-legend').replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;
 const comparison=selection==='all';
 $('chart-description').textContent=comparison?'Totale winst per aandeel als percentage van de inleg, inclusief ontvangen dividend':'Dagelijkse marktwaarde, inleg en ontvangen dividend vanaf je aankoopdatum';
 const holding=selection.startsWith('portfolio:')?state.portfolios.find(p=>p.currency===selection.slice(10)):state.positions[Number(selection)];
 const members=comparison?state.positions:holding?[holding]:[];
 if(!members.length){$('chartnote').textContent='Voeg een aankoop toe om de historie te bekijken.';return;}
 const allDays=[...new Set(members.flatMap(p=>p.history.map(point=>point.day)))].sort();
 const days=chartPeriodPoints(allDays.map(day=>({day})),range).map(p=>p.day);
 const palette=['#4de0b3','#70b7ff','#ffce6b','#e89cff','#ff9090','#b2d96b','#72dce9','#ffaf73'];
 const lines=[];
 if(comparison){
  members.forEach((p,i)=>{const byDay=new Map(p.history.map(point=>[point.day,point]));lines.push({name:p.name+' · '+p.symbol+' · '+p.account_name+' · '+p.currency,color:palette[i]??`hsl(${(i*137.5)%360} 70% 65%)`,values:days.map(day=>{const point=byDay.get(day);return !point||point.total_gain===null||Number(point.invested??point.cost)<=0?null:Number(point.total_gain)/Number(point.invested??point.cost)*100;})});});
 }else{
  const byDay=new Map(holding.history.map(point=>[point.day,point]));
  for(const [field,name,color] of [['cost','Inleg','#8694ac'],['value','Marktwaarde','#4de0b3'],['with_dividends','Waarde + ontvangen dividend','#70b7ff']])lines.push({name,color,values:days.map(day=>{const value=byDay.get(day)?.[field];return value==null?null:Number(value);})});
 }
 for(const line of lines){const label=document.createElement('span');const swatch=document.createElement('span');swatch.textContent='━ ';swatch.setAttribute('class','legend-swatch');swatch.dataset.color=line.color;label.append(swatch,document.createTextNode(line.name));$('chart-legend').append(label);}
 const format=value=>comparison?new Intl.NumberFormat('nl-NL',{maximumFractionDigits:2}).format(value)+'%':money(value,holding.currency);
 const known=lines.flatMap(line=>line.values.filter(value=>value!==null));
 $('chartnote').textContent=days.length?dayLabel(days[0])+' — '+dayLabel(days.at(-1))+(comparison?' · Totale winst / inleg sinds aankoop, inclusief ontvangen dividend.':' · '+holding.currency):'';
 if(!known.length)$('chartnote').textContent+=' Historische koersen worden opgehaald.';
 if(lines.some(line=>line.values.includes(null)))$('chartnote').textContent+=' Lijnen ontbreken vóór aankoop of waar nog geen koers beschikbaar is.';
 $('chart-detail').textContent='Beweeg over de grafiek of bekijk de dagwaarden hieronder.';
 for(const p of members)for(const point of chartPeriodPoints(p.history,range)){if(!days.includes(point.day))continue;const row=document.createElement('tr');for(const value of [dayLabel(point.day),p.name+(p.symbol?' · '+p.symbol:'')+' · '+p.currency,money(point.value,p.currency),money(point.cost,p.currency),money(point.dividend,p.currency),point.total_gain===null?'—':money(point.total_gain,p.currency)])cell(row,value);$('chart-days').append(row);}
 if(!days.length||!known.length)return;
 function node(tag,attrs,text){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;}
 // Legend colors are SVG strokes, avoiding inline styles under the strict CSP.
 [...$('chart-legend').querySelectorAll('.legend-swatch')].forEach(swatch=>{const mark=document.createElementNS(svg.namespaceURI,'svg');mark.setAttribute('width','20');mark.setAttribute('height','12');const stroke=document.createElementNS(svg.namespaceURI,'line');for(const [key,value] of Object.entries({x1:0,x2:18,y1:6,y2:6,stroke:swatch.dataset.color,'stroke-width':3}))stroke.setAttribute(key,String(value));mark.append(stroke);swatch.replaceWith(mark);});
 const min=Math.min(...known),max=Math.max(...known),padding=Math.max((max-min)*.1,Math.abs(max)*.01,comparison?1:1),low=comparison?min-padding:Math.max(0,min-padding),high=max+padding;
 const x=i=>90+(days.length===1?.5:i/(days.length-1))*790,y=value=>250-(value-low)/(high-low)*220;
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:90,x2:880,y1:y(value),y2:y(value),stroke:'#293951'});node('text',{x:80,y:y(value)+4,'text-anchor':'end',fill:'#9eacc2','font-size':12},format(value));}
 for(const i of [...new Set([0,Math.floor((days.length-1)/2),days.length-1])])node('text',{x:x(i),y:280,'text-anchor':i===0?'start':i===days.length-1?'end':'middle',fill:'#9eacc2','font-size':12},dayLabel(days[i]));
 for(const line of lines){let path='',started=false;line.values.forEach((value,i)=>{if(value===null){started=false;return;}path+=(started?'L':'M')+x(i)+' '+y(value)+' ';started=true;});node('path',{d:path,fill:'none',stroke:line.color,'stroke-width':3,'stroke-linejoin':'round'});if(line.values.filter(value=>value!==null).length===1){const i=line.values.findIndex(value=>value!==null);node('circle',{cx:x(i),cy:y(line.values[i]),r:4,fill:line.color});}}
 const guide=node('line',{x1:90,x2:90,y1:25,y2:250,stroke:'#9eacc2','stroke-dasharray':'4 4',visibility:'hidden'});
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const location=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());const i=days.length===1?0:Math.max(0,Math.min(days.length-1,Math.round((location.x-90)/790*(days.length-1))));guide.setAttribute('x1',x(i));guide.setAttribute('x2',x(i));guide.setAttribute('visibility','visible');$('chart-detail').textContent=dayLabel(days[i])+' · '+lines.map(line=>line.name+': '+(line.values[i]===null?'onbekend':format(line.values[i]))).join(' · ');};
 svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');
}
