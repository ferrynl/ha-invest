/* A bounded selection and a responsive plot keep large portfolios readable. */
function drawDashboardChart(state,range,selection,comparisonMembers=[]){
 if(!state)return;
 const svg=$('chart');svg.replaceChildren();$('chart-legend').replaceChildren();$('chart-days').replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;
 const comparison=selection==='all',holding=selection.startsWith('portfolio:')?state.portfolios.find(p=>p.currency===selection.slice(10)):state.positions[Number(selection)];
 const members=comparison?comparisonMembers.slice(0,6):holding?[holding]:[];
 $('home-chart-title').textContent=comparison?'Vergelijk je selectie':holding?.symbol?holding.name:'Je portefeuille in beeld';
 $('chart-description').textContent=comparison?'Maximaal 6 posities. Totale winst sinds aankoop als % van de totale inleg, inclusief dividend.':holding?.symbol?holding.symbol+' · '+holding.account_name+' · '+holding.currency+' · '+(holding.quote?'Koerstijd '+new Date(holding.quote.quoted_at).toLocaleString('nl-NL'):'Wacht op een koers'):'Marktwaarde en openstaande kostprijs in '+(holding?.currency??'de gekozen valuta')+'.';
 let dailyLimit=250,dailyRows=null;
 function renderDays(){
  if(!$('chart-day-details').open)return;
  if(!dailyRows)dailyRows=members.flatMap(p=>chartPeriodPoints(p.history,range).map(point=>({p,point})));
  $('chart-days').replaceChildren();for(const {p,point} of dailyRows.slice(0,dailyLimit)){const row=document.createElement('tr');for(const value of [dayLabel(point.day),p.name+(p.symbol?' · '+p.symbol:'')+' · '+p.currency,money(point.value,p.currency),money(point.cost,p.currency),money(point.dividend,p.currency),point.total_gain==null?'—':money(point.total_gain,p.currency)])cell(row,value);$('chart-days').append(row);}
  $('chart-days-note').textContent=Math.min(dailyRows.length,dailyLimit)+' van '+dailyRows.length+' dagwaarden getoond';$('chart-days-more').hidden=dailyLimit>=dailyRows.length;
 }
 $('chart-day-details').ontoggle=renderDays;$('chart-days-more').onclick=()=>{dailyLimit+=250;renderDays();};renderDays();
 if(!members.length){$('chartnote').textContent=comparison?'Selecteer hieronder maximaal 6 posities om te vergelijken.':'Nog geen historie beschikbaar. Voeg een aankoop toe of importeer je portefeuille.';$('chart-detail').textContent='';return;}
 const allDays=[...new Set(members.flatMap(p=>p.history.map(point=>point.day)))].sort(),days=chartPeriodPoints(allDays.map(day=>({day})),range).map(p=>p.day);
 const palette=['#47dcb0','#70b7ff','#ffce6b','#d49bff','#ff929d','#72dce9'],lines=[];
 if(comparison){members.forEach((p,i)=>{const history=new Map(p.history.map(point=>[point.day,point]));lines.push({name:p.symbol+' · '+p.account_name,color:palette[i],values:days.map(day=>{const point=history.get(day),basis=Number(point?.invested??point?.cost);return !point||point.total_gain==null||basis<=0?null:Number(point.total_gain)/basis*100;})});});}
 else{const history=new Map(holding.history.map(point=>[point.day,point]));for(const [field,name,color] of [['value','Marktwaarde','#47dcb0'],['cost','Openstaande kostprijs','#8694ac'],['with_dividends','Waarde + dividend','#70b7ff']])lines.push({name,color,values:days.map(day=>{const value=history.get(day)?.[field];return value==null?null:Number(value);})});}
 const format=value=>comparison?homePercent(value):money(value,holding.currency);
 let min=Infinity,max=-Infinity,hasGaps=false;for(const line of lines)for(const value of line.values){if(value==null)hasGaps=true;else{min=Math.min(min,value);max=Math.max(max,value);}}
 $('chartnote').textContent=days.length?dayLabel(days[0])+' — '+dayLabel(days.at(-1))+(comparison?' · Winst sinds aankoop, geen rendement over deze periode.':' · '+holding.currency):'Geen dagen in deze periode.';
 if(hasGaps)$('chartnote').textContent+=' Gaten geven ontbrekende koersen of dagen voor de aankoop aan.';
 $('chart-detail').textContent='Bekijk een dag met je muis, of gebruik de pijltjestoetsen op de grafiek.';
 if(!days.length||!Number.isFinite(min)){$('chartnote').textContent+=' Historische koersen zijn nog niet beschikbaar.';return;}
 const width=Math.max(360,Math.round(svg.getBoundingClientRect().width||900)),height=330,left=width<550?78:98,right=width-16,top=24,bottom=280;
 svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('tabindex','0');svg.setAttribute('aria-label','Portefeuillegrafiek. Gebruik links en rechts voor de dagwaarden.');
 const padding=Math.max((max-min)*.12,Math.abs(max)*.01,1),low=comparison?Math.min(0,min-padding):Math.max(0,min-padding),high=max+padding;
 const x=i=>left+(days.length===1?.5:i/(days.length-1))*(right-left),y=value=>bottom-(value-low)/(high-low)*(bottom-top);
 function node(tag,attrs,text,parent=svg){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;parent.append(el);return el;}
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#293951','stroke-dasharray':'3 5'});node('text',{x:left-12,y:y(value)+4,'text-anchor':'end',fill:'#91a4bf','font-size':11},format(value));}
 if(low<0&&high>0)node('line',{x1:left,x2:right,y1:y(0),y2:y(0),stroke:'#71839c','stroke-dasharray':'5 5'});
 for(const i of [...new Set([0,Math.floor((days.length-1)/2),days.length-1])])node('text',{x:x(i),y:height-20,'text-anchor':i===0?'start':i===days.length-1?'end':'middle',fill:'#91a4bf','font-size':11},dayLabel(days[i]));
 for(const line of lines){const group=node('g',{});let path='',started=false;line.values.forEach((value,i)=>{if(value==null){started=false;return;}path+=(started?'L':'M')+x(i)+' '+y(value)+' ';started=true;});node('path',{d:path,fill:'none',stroke:line.color,'stroke-width':2.5,'stroke-linejoin':'round','stroke-linecap':'round'},undefined,group);if(line.values.filter(value=>value!=null).length===1){const i=line.values.findIndex(value=>value!=null);node('circle',{cx:x(i),cy:y(line.values[i]),r:4,fill:line.color},undefined,group);}
  const label=document.createElement('button');label.type='button';label.className='home-legend-button';label.setAttribute('aria-pressed','true');const mark=document.createElementNS(svg.namespaceURI,'svg');mark.setAttribute('viewBox','0 0 20 12');node('line',{x1:1,x2:18,y1:6,y2:6,stroke:line.color,'stroke-width':3},undefined,mark);label.append(mark,document.createTextNode(line.name));label.addEventListener('click',()=>{line.hidden=!line.hidden;group.setAttribute('visibility',line.hidden?'hidden':'visible');label.setAttribute('aria-pressed',String(!line.hidden));});$('chart-legend').append(label);
 }
 let cursor=days.length-1;const guide=node('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:bottom,stroke:'#91a4bf','stroke-dasharray':'4 4',visibility:'hidden'});
 function detail(index){cursor=index;guide.setAttribute('x1',x(index));guide.setAttribute('x2',x(index));guide.setAttribute('visibility','visible');$('chart-detail').textContent=dayLabel(days[index])+' · '+lines.filter(line=>!line.hidden).map(line=>line.name+': '+(line.values[index]==null?'onbekend':format(line.values[index]))).join(' · ');}
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());detail(days.length===1?0:Math.max(0,Math.min(days.length-1,Math.round((point.x-left)/(right-left)*(days.length-1)))));};svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');svg.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();detail(event.key==='Home'?0:event.key==='End'?days.length-1:Math.max(0,Math.min(days.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};
}
