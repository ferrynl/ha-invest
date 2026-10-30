/* Performance is fetched only when its report is opened. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let performanceData=null,performanceKey='',performanceRequest=null,performanceGeneration=0,performanceError=false,performanceErrorDetails='',performancePages=new Map();
function performancePercent(value){return new Intl.NumberFormat(appLocale(),{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value))+'%';}
function clearPerformance(){performanceGeneration++;performanceRequest?.cancel();performanceRequest=null;performanceData=null;performanceKey='';performanceError=false;performanceErrorDetails='';performancePages.clear();}
async function loadPerformance(key){
 const generation=++performanceGeneration;
 performanceRequest=reportRequest('api/reports/performance?account_id='+encodeURIComponent(currentBroker)+'&currency='+encodeURIComponent($('report-currency').value),60000);
 // All figures come from this one server snapshot. A quote update since the
 // selector list loaded does not invalidate a complete report response.
 try{const data=await performanceRequest.promise;if(generation!==performanceGeneration||key!==reportHistoryScope()||!accessSession?.user)return;performanceData=data;}
 catch(error){if(generation===performanceGeneration){performanceError=true;performanceErrorDetails=['report_timeout','report_server'].includes(error.code)?error.message:ui('Controleer de verbinding en probeer opnieuw.');}}
 finally{if(generation===performanceGeneration){performanceRequest=null;if(state&&reportType==='performance')renderReports();}}
}
function performanceRow(list,label,value,percent=null,note='',emphasis=false){
 const row=homeNode('div',undefined,'performance-row'+(emphasis?' performance-total':'')),term=homeNode('div'),amount=homeNode('div',undefined,'performance-amount');
 term.append(homeNode('span',label));if(note){const help=homeNode('details',undefined,'performance-help'),toggle=homeNode('summary','ⓘ');toggle.setAttribute('aria-label',label+' · '+ui('Toelichting'));help.append(toggle,homeNode('small',note));term.append(help);}
 if(percent!==null)amount.append(homeNode('span',performancePercent(percent),Number(percent)>=0?'positive':'negative'));
 const number=homeNode('strong',value);if(emphasis&&percent!==null)number.className=Number(percent)>=0?'positive':'negative';amount.append(number);row.append(term,amount);list.append(row);
}
function performanceBars(card,years,currency,key){
 const mobile=window.matchMedia('(max-width:600px)').matches,pageSize=mobile?5:9,pages=Math.max(1,Math.ceil(years.length/pageSize)),page=Math.min(performancePages.get(key)||0,pages-1);
 const last=years.length-page*pageSize,rows=years.slice(Math.max(0,last-pageSize),last),toolbar=homeNode('div',undefined,'performance-toolbar'),previous=homeNode('button','‹','secondary'),next=homeNode('button','›','secondary');
 previous.type=next.type='button';previous.setAttribute('aria-label',ui('Eerdere jaren'));next.setAttribute('aria-label',ui('Latere jaren'));previous.disabled=page>=pages-1;next.disabled=page===0;
 previous.onclick=()=>{performancePages.set(key,page+1);renderReports();};next.onclick=()=>{performancePages.set(key,page-1);renderReports();};toolbar.append(previous,homeNode('span',rows.length?rows[0].year+' – '+rows.at(-1).year:ui('Geen gegevens voor deze selectie.')),next);card.plot.append(toolbar);
 if(!rows.length){reportEmpty(card);return;}
 const width=mobile?360:640,svg=reportSvg(card,280),max=Math.max(1,...rows.flatMap(r=>[Math.abs(Number(r.gain)||0),Number(r.invested)||0])),zero=140,scale=105/max,step=(width-60)/rows.length;svg.setAttribute('viewBox','0 0 '+width+' 280');
 reportSvgNode('line',{x1:20,x2:width-20,y1:zero,y2:zero,stroke:'#53647c'},undefined,svg);
 rows.forEach((row,i)=>{const x=30+i*step,width=Math.min(42,step*.65),capital=Number(row.invested)*scale;
  const base=reportSvgNode('rect',{x,y:zero-capital,width,height:capital,fill:'#384357'},undefined,svg);reportHover(base,row.year+' · '+ui('Aankoopbedrag')+': '+money(row.invested,currency),card);
  if(row.gain!==null){const gain=Number(row.gain),size=Math.max(1,Math.abs(gain)*scale),bar=reportSvgNode('rect',{x,y:gain>=0?zero-size:zero,width,height:size,fill:gain>=0?'#47dcb0':'#f05b54'},undefined,svg);reportHover(bar,row.year+' · '+ui('Jaarresultaat')+': '+money(gain,currency),card);}
  reportSvgNode('text',{x:x+width/2,y:270,'text-anchor':'middle',fill:'#a7bad1','font-size':12},row.year,svg);
 });
 const legend=homeNode('p',ui('Groen/rood: jaarresultaat. Grijs: aankopen in dat jaar. Het lopende jaar is tot vandaag.'),'report-chart-note');card.plot.append(legend);
 if(rows.some(r=>r.gain===null))card.detail.textContent=ui('Jaren zonder betrouwbare begin- of eindwaarde tonen geen resultaatbalk.');
}
function renderPerformanceReport(){
 $('report-metrics').replaceChildren();$('report-charts').replaceChildren();$('report-insights').replaceChildren();$('report-head').replaceChildren();$('report-rows').replaceChildren();$('report-count').textContent='';
 $('report-description').textContent=ui('Sinds de eerste aankoop. Eerst het totaal in EUR, daarna per bronvaluta. Percentages bij de onderdelen gebruiken de totale aankoopinleg als basis.');
 const key=reportHistoryScope();if(performanceKey!==key){clearPerformance();performanceKey=key;}
 if(!performanceData){const panel=homeNode('section',undefined,'panel report-wide');panel.append(homeNode('p',performanceError?ui('Rendementsrapport laden mislukt.'):ui('Rendement berekenen…')));$('report-charts').append(panel);if(performanceError){if(performanceErrorDetails)panel.append(homeNode('p',performanceErrorDetails));const retry=homeNode('button',ui('Opnieuw proberen'),'secondary');retry.type='button';retry.onclick=()=>{clearPerformance();renderReports();};panel.append(retry);}else if(!performanceRequest)loadPerformance(key);return;}
 $('report-status').textContent=ui('Kosten en belasting zijn niet afzonderlijk geregistreerd. Het resultaat is vóór eventuele aanvullende kosten; dividend is het geboekte nettobedrag.');
 const header=homeNode('tr');for(const label of [ui('Valuta'),ui('Jaar'),ui('Aankoopbedrag'),ui('Jaarresultaat')])header.append(homeNode('th',label));$('report-head').append(header);
 let count=0;
 for(const group of performanceData.groups){
  const label=group.combined?ui('Totaal alle valuta’s in EUR'):ui('Uitsplitsing per valuta')+' · '+group.currency;
  const card=reportChartCard({label},ui('Rendementsoverzicht'),ui('Winst en verlies per kalenderjaar, naast de aankoopbedragen.'),true);performanceBars(card,group.years,group.currency,label);
  const list=homeNode('div',undefined,'performance-breakdown');card.plot.append(list);
  const amount=value=>value===null?ui('Niet beschikbaar'):money(value,group.currency);
  list.append(homeNode('h4',ui('Kapitaal')));performanceRow(list,ui('Totale aankoopinleg'),amount(group.invested),null,ui('Alle aankoopbedragen; verkopen worden hier niet afgetrokken. Omboekingen tellen niet dubbel.'));
  list.append(homeNode('h4',ui('Resultaatopbouw')));
  performanceRow(list,ui('Koersresultaat'),amount(group.price_gain),group.price_percent,ui('Marktwaarde min openstaande kostprijs.'));
  performanceRow(list,ui('Dividend'),amount(group.dividend),group.dividend_percent,ui('Geboekt netto ontvangen dividend.'));
  performanceRow(list,ui('Gerealiseerd resultaat'),amount(group.realised),group.realised_percent,ui('Verkoopopbrengst min de afgeboekte kostprijs.'));
  list.append(homeNode('h4',ui('Kosten en belasting')));performanceRow(list,ui('Transactiekosten'),ui('Niet geregistreerd'));performanceRow(list,ui('Belasting'),ui('Niet afzonderlijk geregistreerd'));
  performanceRow(list,ui('Totaal resultaat'),amount(group.total),group.total_percent,ui('Koersresultaat plus gerealiseerd resultaat en netto dividend, vóór aanvullende kosten.'),true);
  performanceRow(list,ui('Intern rendement (XIRR)'),group.irr===null?ui('Niet berekenbaar'):performancePercent(group.irr),null,ui('Op jaarbasis uit gedateerde aankopen, verkopen, dividend en de actuele eindwaarde. Geen rendement op brokersaldo. Een niet-eenduidige uitkomst blijft leeg.'));
  performanceRow(list,ui('Exact tijdgewogen rendement'),ui('Niet berekenbaar'),null,ui('Hiervoor ontbreken portefeuillewaarderingen op ieder moment van een externe geldstroom.'));
  if(!group.complete)list.prepend(homeNode('p',ui('Onvolledig: ontbrekende koersen of omrekeningen. Totaalrendement en XIRR zijn niet berekend.'),'report-coverage'));
  for(const year of group.years){const row=homeNode('tr');for(const text of [label,year.year,amount(year.invested),amount(year.gain)])cell(row,text);$('report-rows').append(row);count++;}
 }
 $('report-count').textContent=new Intl.NumberFormat(appLocale()).format(count);
}
window.addEventListener('resize',()=>{if(state&&reportType==='performance'&&location.hash.startsWith('#rapporten'))renderReports();});
