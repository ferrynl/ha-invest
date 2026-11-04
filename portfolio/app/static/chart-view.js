/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);

const chartPresets={
 value:{label:()=>ui('Marktwaarde en kostprijs'),fields:['value','cost','with_dividends']},
 area:{label:()=>ui('Marktwaarde als vlakgrafiek'),fields:['value'],shape:'area'},
 columns:{label:()=>ui('Marktwaarde als kolommen'),fields:['value'],shape:'columns'},
 cost:{label:()=>ui('Openstaande kostprijs'),fields:['cost']},
 invested:{label:()=>ui('Totale aankoopinleg'),fields:['invested']},
 dividend:{label:()=>ui('Cumulatief ontvangen dividend'),fields:['dividend'],shape:'step'},
 gain:{label:()=>ui('Resultaat sinds aankoop (bedrag)'),fields:['total_gain'],shape:'area'},
 return:{label:()=>ui('Resultaat sinds aankoop (%)'),fields:[]},
 income_value:{label:()=>ui('Marktwaarde en ontvangen dividend'),fields:['value','dividend']},
 value_invested:{label:()=>ui('Marktwaarde en aankoopinleg'),fields:['value','invested']}
};
function fillChartPresets(select){
 for(const [id,preset] of Object.entries(chartPresets)){
  const option=document.createElement('option');option.value=id;option.textContent=preset.label();select.append(option);
 }
}
function chartSeriesValue(point,field){
 const value=field==='total_gain'?(point?.return_gain??(point?.missing>0?null:point?.total_gain)):point?.[field];
 return value!=null&&Number.isFinite(Number(value))?Number(value):null;
}
if(typeof document!=='undefined')fillChartPresets(document.getElementById('chart-measure'));
/* A bounded selection and a responsive plot keep large portfolios readable. */
function drawDashboardChart(state,range,selection,comparisonMembers=[]){
 if(!state)return;
 const svg=$('chart');svg.replaceChildren();$('chart-legend').replaceChildren();$('chart-days').replaceChildren();svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;
 const comparison=selection==='all',holding=selection.startsWith('portfolio:')?state.portfolios.find(p=>p.currency===selection.slice(10)):state.positions[Number(selection)];
 const measure=$('chart-measure').value,preset=chartPresets[measure]||chartPresets.value;
 const returnMode=!comparison&&measure==='return',gainMode=!comparison&&measure==='gain';
 $('chart-measure').disabled=comparison;$('chart-return-badge').textContent='';
 const breakdown=measure==='value'&&selection.startsWith('portfolio:')?state.portfolios.filter(p=>p.native_currency):[];
 const members=breakdown.length?breakdown:comparison?comparisonMembers.slice(0,6):holding?[holding]:[];
 $('home-chart-title').textContent=comparison?ui('Vergelijk je selectie'):holding?.symbol?holding.name:ui('Je portefeuille in beeld');
 $('chart-description').textContent=comparison?ui('Maximaal 6 posities. Totale winst sinds aankoop als % van de totale inleg, inclusief dividend.'):holding?.symbol?holding.symbol+' · '+holding.account_name+' · '+holding.currency+' · '+(holding.quote?ui('Koerstijd ')+new Date(holding.quote.quoted_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')):ui('Wacht op een koers')):ui('Marktwaarde en openstaande kostprijs in ')+(holding?.currency??ui('de gekozen valuta'))+'.';
 if(breakdown.length)$('chart-description').textContent=ui('Marktwaarde per valuta, omgerekend naar EUR.');
 if(returnMode)$('chart-description').textContent=ui('Resultaat sinds aankoop als percentage van de totale aankoopinleg, inclusief dividend en gerealiseerd resultaat. De periodeknoppen kiezen welke dagwaarden je ziet.');
 if(!comparison&&measure!=='value'&&!returnMode)$('chart-description').textContent=gainMode
  ?ui('Resultaat sinds aankoop in geld, inclusief dividend en gerealiseerd resultaat.')
  :preset.label()+' · '+(holding?.currency??ui('de gekozen valuta'));
 const end=members.reduce((last,p)=>{const day=p.history.at(-1)?.day;return day>last?day:last;},'');
 const start=end?chartPeriodStart(end,range):'';
 const histories=members.map(p=>chartPointsSince(p.history,start));
 let dailyLimit=250,dailyRows=null;
 function renderDays(){
  if(!$('chart-day-details').open)return;
  if(!dailyRows)dailyRows=members.flatMap((p,index)=>histories[index].map(point=>({p,point})));
  $('chart-days').replaceChildren();for(const {p,point} of dailyRows.slice(0,dailyLimit)){const row=document.createElement('tr');for(const value of [dayLabel(point.day),p.name+(p.symbol?' · '+p.symbol:'')+' · '+p.currency,money(point.value,p.currency),money(point.cost,p.currency),money(point.dividend,p.currency),point.total_gain==null?'—':money(point.total_gain,p.currency)])cell(row,value);$('chart-days').append(row);}
  $('chart-days-note').textContent=Math.min(dailyRows.length,dailyLimit)+ui(' van ')+dailyRows.length+ui(' dagwaarden getoond');$('chart-days-more').hidden=dailyLimit>=dailyRows.length;
 }
 $('chart-day-details').ontoggle=renderDays;$('chart-days-more').onclick=()=>{dailyLimit+=250;renderDays();};renderDays();
 if(!members.length){$('chartnote').textContent=comparison?ui('Selecteer hieronder maximaal 6 posities om te vergelijken.'):ui('Nog geen historie beschikbaar. Voeg een aankoop toe of importeer je portefeuille.');$('chart-detail').textContent='';return;}
 const dateSet=new Set();for(const history of histories)for(const point of history)dateSet.add(point.day);
 const days=[...dateSet].sort();
 const missingCount=returnMode||gainMode?histories[0].reduce((max,p)=>Math.max(max,Number(p.missing)||0),0)+(Number(holding.excluded_count)||0):0;
 if(missingCount)$('chart-description').textContent=ui('Resultaat van bekende posities. Winst en aankoopinleg worden per dag voor dezelfde posities berekend. Ontbrekende posities: maximaal {count}. De samenstelling van dit deel kan per dag verschillen.',{count:missingCount});
 const palette=['#47dcb0','#70b7ff','#ffce6b','#d49bff','#ff929d','#72dce9','#f39757','#a8de72','#eb8bd9','#b3a5ff','#f1ed8a','#6ccac0'],lines=[];
 const byDay=histories.map(points=>new Map(points.map(point=>[point.day,point])));
 if(breakdown.length)breakdown.forEach((p,i)=>lines.push({name:p.native_currency,color:palette[i%palette.length],values:days.map(day=>chartSeriesValue(byDay[i].get(day),'value'))}));
 else if(comparison)members.forEach((p,i)=>lines.push({name:p.symbol+' · '+p.account_name,color:palette[i],values:days.map(day=>{
  const point=byDay[i].get(day),basis=Number(point?.invested??point?.cost);
  return !point||point.total_gain==null||basis<=0?null:Number(point.total_gain)/basis*100;
 })}));
 else if(returnMode)lines.push({name:missingCount?ui('Resultaat bekende posities (%)'):ui('Resultaat sinds aankoop (%)'),color:'#20c79b',values:days.map(day=>chartProfitValue(byDay[0].get(day)))});
 else{
  const fields={value:[ui('Marktwaarde'),'#47dcb0'],cost:[ui('Openstaande kostprijs'),'#8694ac'],
   with_dividends:[ui('Waarde + dividend'),'#70b7ff'],invested:[ui('Totale aankoopinleg'),'#ffce6b'],
   dividend:[ui('Cumulatief ontvangen dividend'),'#70b7ff'],total_gain:[preset.label(),'#47dcb0']};
  for(const field of preset.fields){
   const [name,color]=fields[field];
   lines.push({name,color,values:days.map(day=>chartSeriesValue(byDay[0].get(day),field))});
  }
 }
 const format=value=>comparison||returnMode?homePercent(value):money(value,holding.currency);
 let min=Infinity,max=-Infinity,hasGaps=false;for(const line of lines)for(const value of line.values){if(value==null)hasGaps=true;else{min=Math.min(min,value);max=Math.max(max,value);}}
 $('chartnote').textContent=days.length?dayLabel(days[0])+' — '+dayLabel(days.at(-1))+(comparison?ui(' · Winst sinds aankoop, geen rendement over deze periode.'):' · '+holding.currency):ui('Geen dagen in deze periode.');
 if(hasGaps)$('chartnote').textContent+=ui(' Gaten geven ontbrekende koersen of dagen voor de aankoop aan.');
 if(returnMode)$('chartnote').textContent+=ui(' · Resultaat sinds aankoop; geen tijdgewogen rendement over de gekozen periode.');
 $('chart-detail').textContent=ui('Bekijk een dag met je muis, of gebruik de pijltjestoetsen op de grafiek.');
 if(!days.length||!Number.isFinite(min)){$('chartnote').textContent+=ui(' Historische koersen zijn nog niet beschikbaar.');return;}
 const width=Math.max(360,Math.round(svg.getBoundingClientRect().width||900)),height=330,left=width<550?78:98,right=width-16,top=24,bottom=280;
 svg.setAttribute('viewBox','0 0 '+width+' '+height);svg.setAttribute('tabindex','0');svg.setAttribute('aria-label',ui('Portefeuillegrafiek. Gebruik links en rechts voor de dagwaarden.'));
 const shape=comparison?'':preset.shape,zeroBased=['area','columns'].includes(shape),signed=comparison||returnMode||gainMode;
 const padding=Math.max((max-min)*.12,Math.abs(max)*.01,1);
 const low=signed?Math.min(0,min-padding):zeroBased?0:Math.max(0,min-padding);
 const high=signed?Math.max(padding,max+padding):max+padding;
 const x=i=>left+(days.length===1?.5:i/(days.length-1))*(right-left),y=value=>bottom-(value-low)/(high-low)*(bottom-top);
 function node(tag,attrs,text,parent=svg){const el=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;parent.append(el);return el;}
 if(returnMode){const defs=node('defs',{});for(const [id,from,to] of [['chart-positive',top,y(0)],['chart-negative',y(0),bottom]]){const clip=node('clipPath',{id},undefined,defs);node('rect',{x:left,y:from,width:right-left,height:Math.max(0,to-from)},undefined,clip);}const last=lines[0].values.at(-1);if(last!=null){$('chart-return-badge').textContent=format(last);$('chart-return-badge').className=last>=0?'chart-return-badge positive':'chart-return-badge negative';}}
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4;node('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#293951','stroke-dasharray':'3 5'});node('text',{x:left-12,y:y(value)+4,'text-anchor':'end',fill:'#91a4bf','font-size':11},format(value));}
 if(low<0&&high>0)node('line',{x1:left,x2:right,y1:y(0),y2:y(0),stroke:'#71839c','stroke-dasharray':'5 5'});
 for(const i of [...new Set([0,Math.floor((days.length-1)/2),days.length-1])])node('text',{x:x(i),y:height-20,'text-anchor':i===0?'start':i===days.length-1?'end':'middle',fill:'#91a4bf','font-size':11},dayLabel(days[i]));
 for(const line of lines){const group=node('g',{});let path='',started=false;line.values.forEach((value,i)=>{if(value==null){started=false;return;}path+=started&&shape==='step'?'H'+x(i)+' V'+y(value)+' ':(started?'L':'M')+x(i)+' '+y(value)+' ';started=true;});if(returnMode){for(const run of chartRuns(line.values)){const area='M'+x(run[0].i)+' '+y(0)+' '+run.map(p=>'L'+x(p.i)+' '+y(p.value)).join(' ')+' L'+x(run.at(-1).i)+' '+y(0)+' Z';for(const [clip,color] of [['chart-positive','#20c79b'],['chart-negative','#f14d64']])node('path',{d:area,fill:color,'fill-opacity':.16,'clip-path':'url(#'+clip+')'},undefined,group);}for(const [clip,color] of [['chart-positive','#20c79b'],['chart-negative','#f14d64']])node('path',{d:path,fill:'none',stroke:color,'stroke-width':2.4,'stroke-linejoin':'round','clip-path':'url(#'+clip+')'},undefined,group);const last=line.values.at(-1);if(last!=null){node('line',{x1:left,x2:right,y1:y(last),y2:y(last),stroke:last>=0?'#20c79b':'#f14d64','stroke-dasharray':'5 5',opacity:.5},undefined,group);node('circle',{cx:x(days.length-1),cy:y(last),r:4,fill:last>=0?'#20c79b':'#f14d64'},undefined,group);}}else if(shape==='columns'){
   const stride=Math.max(1,Math.ceil(days.length/Math.max(1,Math.floor((right-left)/6))));
   const half=Math.min(15,(right-left)/Math.max(1,Math.ceil(days.length/stride))*.3),baseline=y(0);
   let columns='';for(let i=0;i<line.values.length;i++){
    const value=line.values[i];if(value==null||(i%stride&&i!==line.values.length-1))continue;
    columns+='M'+(x(i)-half)+' '+baseline+' V'+y(value)+' h'+(2*half)+' V'+baseline+' Z';
   }
   node('path',{d:columns,fill:line.color,'fill-opacity':.8},undefined,group);
  }else{
   if(shape==='area')for(const run of chartRuns(line.values)){
    const baseline=y(0),area='M'+x(run[0].i)+' '+baseline+' '+run.map(p=>'L'+x(p.i)+' '+y(p.value)).join(' ')+' L'+x(run.at(-1).i)+' '+baseline+' Z';
    node('path',{d:area,fill:line.color,'fill-opacity':.18},undefined,group);
   }
   node('path',{d:path,fill:'none',stroke:line.color,'stroke-width':2.5,'stroke-linejoin':'round','stroke-linecap':'round'},undefined,group);
  }if(line.values.filter(value=>value!=null).length===1){const i=line.values.findIndex(value=>value!=null);node('circle',{cx:x(i),cy:y(line.values[i]),r:4,fill:returnMode&&line.values[i]<0?'#f14d64':line.color},undefined,group);}
  const label=document.createElement('button');label.type='button';label.className='home-legend-button';label.setAttribute('aria-pressed','true');const mark=document.createElementNS(svg.namespaceURI,'svg');mark.setAttribute('viewBox','0 0 20 12');node('line',{x1:1,x2:18,y1:6,y2:6,stroke:line.color,'stroke-width':3},undefined,mark);label.append(mark,document.createTextNode(line.name));label.addEventListener('click',()=>{line.hidden=!line.hidden;group.setAttribute('visibility',line.hidden?'hidden':'visible');label.setAttribute('aria-pressed',String(!line.hidden));});$('chart-legend').append(label);
 }
 let cursor=days.length-1;const guide=node('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:bottom,stroke:'#91a4bf','stroke-dasharray':'4 4',visibility:'hidden'});
 function detail(index){cursor=index;guide.setAttribute('x1',x(index));guide.setAttribute('x2',x(index));guide.setAttribute('visibility','visible');$('chart-detail').textContent=dayLabel(days[index])+' · '+lines.filter(line=>!line.hidden).map(line=>line.name+': '+(line.values[index]==null?ui('onbekend'):format(line.values[index]))).join(' · ');}
 svg.onpointermove=event=>{const matrix=svg.getScreenCTM();if(!matrix)return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());detail(days.length===1?0:Math.max(0,Math.min(days.length-1,Math.round((point.x-left)/(right-left)*(days.length-1)))));};svg.onpointerleave=()=>guide.setAttribute('visibility','hidden');svg.onkeydown=event=>{if(!['ArrowLeft','ArrowRight',ui('Home'),'End'].includes(event.key))return;event.preventDefault();detail(event.key===ui('Home')?0:event.key==='End'?days.length-1:Math.max(0,Math.min(days.length-1,cursor+(event.key==='ArrowLeft'?-1:1))));};
}
