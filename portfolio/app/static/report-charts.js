/* Local SVG charts: no external scripts, tracking or portfolio uploads. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
const reportPalette=['#47dcb0','#70b7ff','#bea0ff','#ffcb83','#6ed4dd','#f49ab4','#97b2cb'];
let reportPlotId=0;
function reportPercent(value){return new Intl.NumberFormat(appLocale(),{maximumFractionDigits:1}).format(value)+'%';}
function reportMonth(value,short=false){return new Date(value+'-01T00:00:00Z').toLocaleDateString(appLocale(),{month:short?'short':'long',...(short?{}:{year:'numeric'}),timeZone:'UTC'});}
function reportTop(values,limit=7){const ordered=[...values].filter(p=>p.value>0).sort((a,b)=>b.value-a.value);return ordered.length>limit?[...ordered.slice(0,limit),{name:ui('Overige'),value:ordered.slice(limit).reduce((sum,p)=>sum+p.value,0)}]:ordered;}
function reportSvgNode(tag,attrs={},text,parent){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;if(parent)parent.append(node);return node;}
function reportSvg(card,height=300){const svg=reportSvgNode('svg',{viewBox:'0 0 640 '+height,role:'group','aria-label':card.plot.closest('section').querySelector('h3').textContent});card.plot.append(svg);return svg;}
function reportEmpty(card){card.plot.append(homeNode('p',ui('Geen gegevens voor deze selectie.'),'report-chart-empty'));card.detail.textContent='';}
function reportHover(node,label,card){node.setAttribute('tabindex','0');node.setAttribute('role','img');node.setAttribute('aria-label',label);reportSvgNode('title',{},label,node);const show=()=>{card.detail.textContent=label;};node.onpointerenter=show;node.onfocus=show;node.onclick=show;}
function reportDonut(card,values,currency){
 const groups=reportTop(values,6),total=groups.reduce((sum,p)=>sum+p.value,0);if(!total){reportEmpty(card);return;}
 card.plot.classList.add('report-donut-layout');const svg=reportSvg(card,280);svg.setAttribute('viewBox','0 0 300 280');
 reportSvgNode('circle',{cx:150,cy:137,r:88,fill:'none',stroke:'#243348','stroke-width':28},undefined,svg);
 const length=2*Math.PI*88;let start=0;
 for(const [index,p] of groups.entries()){const fraction=p.value/total;const circle=reportSvgNode('circle',{cx:150,cy:137,r:88,fill:'none',stroke:reportPalette[index%reportPalette.length],'stroke-width':28,'stroke-dasharray':Math.max(0,fraction*length-3)+' '+length,'stroke-dashoffset':-start*length,transform:'rotate(-90 150 137)'},undefined,svg);reportHover(circle,p.name+' · '+money(p.value,currency)+' · '+reportPercent(fraction*100),card);start+=fraction;}
 reportSvgNode('text',{x:150,y:132,'text-anchor':'middle',fill:'#eef4ff','font-size':25,'font-weight':700},money(total,currency),svg);
 reportSvgNode('text',{x:150,y:158,'text-anchor':'middle',fill:'#91a4bf','font-size':11},ui('bekend totaal'),svg);
 const legend=homeNode('div',undefined,'report-donut-legend');for(const [index,p] of groups.entries()){const row=homeNode('div'),mark=reportSvgNode('svg',{viewBox:'0 0 12 12','aria-hidden':'true'});reportSvgNode('rect',{width:12,height:12,rx:3,fill:reportPalette[index%reportPalette.length]},undefined,mark);const text=homeNode('span',p.name),number=homeNode('strong',reportPercent(p.value/total*100));row.append(mark,text,number);legend.append(row);}card.plot.append(legend);
}
function reportBars(card,values,currency,signed=false){
 if(!values.length){reportEmpty(card);return;}
 const rows=values.slice(0,14),height=Math.max(210,rows.length*38+30),svg=reportSvg(card,height),max=Math.max(1,...rows.map(p=>Math.abs(p.value))),left=180,right=540,zero=signed?360:left,width=signed?170:right-left;
 reportSvgNode('line',{x1:zero,x2:zero,y1:8,y2:height-8,stroke:'#42516a'},undefined,svg);
 for(const [i,p] of rows.entries()){const y=18+i*38,size=Math.abs(p.value)/max*width;
  reportSvgNode('text',{x:0,y:y+15,fill:'#cbd8e9','font-size':12},p.name.length>24?p.name.slice(0,22)+'…':p.name,svg);
  const bar=reportSvgNode('rect',{x:p.value<0?zero-size:zero,y,width:Math.max(1,size),height:23,rx:4,fill:p.value<0?'#f08091':signed?'#47dcb0':reportPalette[i%reportPalette.length]},undefined,svg);reportHover(bar,p.name+' · '+money(p.value,currency),card);
  reportSvgNode('text',{x:630,y:y+16,'text-anchor':'end',fill:p.value<0?'#ff929d':'#e7f1ff','font-size':12},money(p.value,currency),svg);
 }
}
function reportWaterfall(card,values,currency){
 const total=values.reduce((sum,p)=>sum+p.value,0),items=[...values,{name:ui('Totale winst'),value:total,total:true}];let cumulative=0;const bars=items.map(p=>{const from=p.total?0:cumulative,to=p.total?p.value:cumulative+p.value;if(!p.total)cumulative=to;return {...p,from,to};});
 const low=Math.min(0,...bars.flatMap(p=>[p.from,p.to])),high=Math.max(1,...bars.flatMap(p=>[p.from,p.to])),span=high-low,svg=reportSvg(card,310),top=35,bottom=240,y=value=>bottom-(value-low)/span*(bottom-top);
 reportSvgNode('line',{x1:20,x2:620,y1:y(0),y2:y(0),stroke:'#42516a'},undefined,svg);
 for(const [i,p] of bars.entries()){const x=40+i*150;const rect=reportSvgNode('rect',{x,y:Math.min(y(p.from),y(p.to)),width:100,height:Math.max(2,Math.abs(y(p.to)-y(p.from))),rx:5,fill:p.total?'#70b7ff':p.value<0?'#f08091':'#47dcb0'},undefined,svg);reportHover(rect,p.name+' · '+money(p.value,currency),card);
  reportSvgNode('text',{x:x+50,y:Math.max(18,Math.min(y(p.from),y(p.to))-10),'text-anchor':'middle',fill:'#e7f1ff','font-size':12},money(p.value,currency),svg);
  reportSvgNode('text',{x:x+50,y:285,'text-anchor':'middle',fill:'#a7bad1','font-size':12},p.name,svg);
  if(i<bars.length-2)reportSvgNode('line',{x1:x+100,x2:x+150,y1:y(p.to),y2:y(p.to),stroke:'#61758f','stroke-dasharray':'4 4'},undefined,svg);
 }
}
function reportColumns(card,values,currency){
 if(!values.some(p=>p.value)){reportEmpty(card);return;}
 const svg=reportSvg(card,310),max=Math.max(1,...values.map(p=>p.value)),top=30,bottom=252;
 for(let i=0;i<=4;i++){const y=bottom-i/4*(bottom-top);reportSvgNode('line',{x1:58,x2:630,y1:y,y2:y,stroke:'#293951','stroke-dasharray':'3 5'},undefined,svg);reportSvgNode('text',{x:52,y:y+4,'text-anchor':'end',fill:'#91a4bf','font-size':10},new Intl.NumberFormat(appLocale(),{notation:'compact',maximumFractionDigits:1}).format(max*i/4),svg);}
 for(const [i,p] of values.entries()){const x=70+i*46,size=p.value/max*(bottom-top),bar=reportSvgNode('rect',{x,y:bottom-size,width:28,height:Math.max(2,size),rx:5,fill:i===values.findIndex(v=>v.value===max)?'#47dcb0':'#3c8f84'},undefined,svg);reportHover(bar,reportMonth(p.name)+' · '+money(p.value,currency),card);reportSvgNode('text',{x:x+14,y:279,'text-anchor':'middle',fill:'#a7bad1','font-size':10},reportMonth(p.name,true),svg);}
}
function reportLine(card,points,series,currency){
 const valid=points.filter(p=>series.every(s=>reportNumber(p[s.key])));if(!valid.length){reportEmpty(card);return;}
 const values=valid.flatMap(p=>series.map(s=>Number(p[s.key]))),low=Math.min(0,...values),high=Math.max(1,...values),padding=(high-low)*.08,svg=reportSvg(card,330),left=85,right=620,top=24,bottom=265;
 const x=i=>left+(valid.length===1?.5:i/(valid.length-1))*(right-left),y=v=>bottom-(v-low)/(high-low+padding)*(bottom-top),gradientId='report-gradient-'+(++reportPlotId);
 const defs=reportSvgNode('defs',{},undefined,svg),gradient=reportSvgNode('linearGradient',{id:gradientId,x1:0,y1:0,x2:0,y2:1},undefined,defs);reportSvgNode('stop',{offset:'0%','stop-color':'#47dcb0','stop-opacity':.22},undefined,gradient);reportSvgNode('stop',{offset:'100%','stop-color':'#47dcb0','stop-opacity':0},undefined,gradient);
 for(let i=0;i<=4;i++){const value=low+(high-low+padding)*i/4;reportSvgNode('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#293951','stroke-dasharray':'3 5'},undefined,svg);reportSvgNode('text',{x:left-10,y:y(value)+4,'text-anchor':'end',fill:'#91a4bf','font-size':10},new Intl.NumberFormat(appLocale(),{style:'currency',currency,notation:'compact',maximumFractionDigits:1}).format(value),svg);}
 const step=Math.max(1,Math.ceil(valid.length/450)),sample=valid.map((p,i)=>({p,i})).filter(({i})=>i%step===0||i===valid.length-1);
 for(const [index,s] of series.entries()){const path=sample.map(({p,i},j)=>(j?'L':'M')+x(i)+' '+y(Number(p[s.key]))).join(' ');if(!index)reportSvgNode('path',{d:path+' L'+x(valid.length-1)+' '+bottom+' L'+x(0)+' '+bottom+' Z',fill:'url(#'+gradientId+')'},undefined,svg);reportSvgNode('path',{d:path,fill:'none',stroke:s.color,'stroke-width':2.5,'stroke-linejoin':'round','stroke-linecap':'round'},undefined,svg);if(valid.length===1)reportSvgNode('circle',{cx:x(0),cy:y(Number(valid[0][s.key])),r:4,fill:s.color},undefined,svg);}
 for(const i of [...new Set([0,Math.floor((valid.length-1)/2),valid.length-1])])reportSvgNode('text',{x:x(i),y:295,'text-anchor':i===0?'start':i===valid.length-1?'end':'middle',fill:'#a7bad1','font-size':11},new Date(valid[i].day+'T00:00:00Z').toLocaleDateString(appLocale(),{month:'short',year:'numeric',timeZone:'UTC'}),svg);
 const legend=homeNode('div',undefined,'report-line-legend');for(const s of series){const label=homeNode('span',s.name);const mark=reportSvgNode('svg',{viewBox:'0 0 16 8','aria-hidden':'true'});reportSvgNode('line',{x1:0,x2:16,y1:4,y2:4,stroke:s.color,'stroke-width':3},undefined,mark);label.prepend(mark);legend.append(label);}card.plot.append(legend);
 let cursor=valid.length-1;const guide=reportSvgNode('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:bottom,stroke:'#a5b7cf','stroke-dasharray':'4 4',visibility:'hidden'},undefined,svg);
 function detail(index){cursor=index;const p=valid[index];guide.setAttribute('x1',x(index));guide.setAttribute('x2',x(index));guide.setAttribute('visibility','visible');card.detail.textContent=new Date(p.day+'T00:00:00Z').toLocaleDateString(appLocale(),{timeZone:'UTC'})+' · '+series.map(s=>s.name+': '+money(p[s.key],currency)).join(' · ')+(p.skipped?' · '+ui('Overgeslagen:')+' '+p.skipped:'');}
 svg.setAttribute('tabindex','0');svg.setAttribute('aria-label',ui('Grafiek. Gebruik de pijltjestoetsen voor details.'));svg.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','End'].includes(event.key))return;event.preventDefault();detail(event.key==='End'?valid.length-1:Math.max(0,Math.min(valid.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());detail(Math.max(0,Math.min(valid.length-1,Math.round((p.x-left)/(right-left)*(valid.length-1)))));};svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');
}
function reportTiles(card,holdings,currency){
 const rows=[...holdings].sort((a,b)=>Math.abs(b.profit)-Math.abs(a.profit)).slice(0,12);if(!rows.length){reportEmpty(card);return;}
 const grid=homeNode('div',undefined,'report-tiles');for(const p of rows){const tile=homeNode('button',undefined,'report-tile '+(p.profit>0?'report-up':p.profit<0?'report-down':'report-flat'));tile.type='button';tile.append(homeNode('span',p.name),homeNode('strong',money(p.profit,currency)));tile.onclick=()=>{card.detail.textContent=p.name+' · '+ui('Marktwaarde')+': '+money(p.value,currency)+' · '+ui('Totale winst')+': '+money(p.profit,currency);};grid.append(tile);}card.plot.append(grid);
}
function reportCalendar(card,values,currency,selectedYear){
 const window=reportCalendarWindow(values,selectedYear),years=[...new Set([selectedYear,...window.map(p=>p.name.slice(0,4))])].sort().reverse(),map=new Map(window.map(p=>[p.name,p.value])),max=Math.max(1,...window.map(p=>p.value)),height=60+years.length*48,svg=reportSvg(card,height);svg.setAttribute('viewBox','0 0 760 '+height);
 for(let month=1;month<=12;month++)reportSvgNode('text',{x:86+(month-1)*55,y:22,'text-anchor':'middle',fill:'#a7bad1','font-size':10},reportMonth(selectedYear+'-'+String(month).padStart(2,'0'),true),svg);
 for(const [i,year] of years.entries()){reportSvgNode('text',{x:8,y:64+i*48,fill:'#cbd8e9','font-size':12},year,svg);for(let month=1;month<=12;month++){const key=year+'-'+String(month).padStart(2,'0'),value=map.get(key)||0,shade=value>0?Math.min(4,1+Math.floor(value/max*3)):0,rect=reportSvgNode('rect',{x:62+(month-1)*55,y:40+i*48,width:48,height:34,rx:6,fill:['#1a293e','#1b5147','#237d64','#34ae86','#54e3b4'][shade]},undefined,svg);reportHover(rect,reportMonth(key)+' · '+money(value,currency),card);if(value>0)reportSvgNode('text',{x:86+(month-1)*55,y:61+i*48,'text-anchor':'middle',fill:shade>2?'#08281e':'#c5eedf','font-size':9,'pointer-events':'none'},new Intl.NumberFormat(appLocale(),{notation:'compact',maximumFractionDigits:0}).format(value),svg);}}
}
