/* Fund composition is current exposure, never a fabricated transaction or return. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
function fundKey(p){return JSON.stringify([p.symbol,p.exchange,p.native_currency||p.currency]);}
function fundComposition(p,compositions){return (compositions||[]).find(f=>fundKey(f)===fundKey(p));}
function fundIsETF(p,compositions){return p.categories?.asset_type==='ETF'||!!fundComposition(p,compositions);}
function fundExposure(positions,compositions){
 const rows=[];
 for(const p of positions){
  if(p.value==null||!Number.isFinite(Number(p.value))||Number(p.value)<=0)continue;
  const fund=fundComposition(p,compositions);
  if(!fundIsETF(p,compositions)){rows.push({...p,value:Number(p.value),exposure_id:fundKey(p)});continue;}
  const unknown=(value)=>({...p,name:p.name+' · '+ui('Niet uitgesplitst'),value,categories:{sector:ui('ETF niet uitgesplitst'),country:ui('ETF niet uitgesplitst')},fund_parent:fundKey(p),exposure_id:'unknown:'+fundKey(p)});
  if(!fund){rows.push(unknown(Number(p.value)));continue;}
  const total=fund.holdings.reduce((sum,h)=>sum+Number(h.weight),0),divisor=Math.max(100,total);
  for(const [index,h] of fund.holdings.entries()){if(Number(h.weight)===0)continue;rows.push({name:h.name,symbol:h.symbol,isin:h.isin,value:Number(p.value)*Number(h.weight)/divisor,currency:p.currency,categories:{sector:h.sector||ui('Niet ingedeeld'),country:h.country||ui('Niet ingedeeld'),asset_type:h.asset_type,category:h.category},fund_parent:fundKey(p),exposure_id:h.isin?'isin:'+h.isin:(h.symbol&&h.exchange&&h.exchange!=='-'&&h.currency?JSON.stringify([h.symbol,h.exchange,h.currency]):JSON.stringify([fundKey(p),index]))});}
  if(total<100)rows.push(unknown(Number(p.value)*(100-total)/100));
 }
 return rows;
}
function fundAllocation(rows){
 const groups=new Map();for(const [index,row] of rows.entries()){const key=row.exposure_id||String(index),prior=groups.get(key);if(prior)prior.value+=row.value;else groups.set(key,{...row});}return [...groups.values()];
}
function fundCoverageText(fund){return ui('Samenstelling van')+' '+dayLabel(fund.as_of)+' · '+ui('Dekking')+' '+reportPercent(Number(fund.coverage))+(fund.stale?' · '+ui('Samenstelling ouder dan 14 dagen'):'')+(fund.signed?' · '+ui('Inclusief negatieve bronwegingen'):'')+(Number(fund.rounding_excess)>0?' · '+ui('Afgeronde bronwegingen evenredig gecorrigeerd'):'');}
function fundHoldingLink(h){return '#aandeel?'+new URLSearchParams({symbol:h.fund_parent.symbol,exchange:h.fund_parent.exchange,currency:h.fund_parent.native_currency||h.fund_parent.currency,holding:h.fund_index,as_of:h.fund_as_of,holding_name:h.name,holding_isin:h.isin||'',holding_symbol:h.symbol||''});}
function renderFundHoldings(target,items,includeFund=false){
 target.replaceChildren();if(!items.length){target.append(homeNode('p',ui('Geen ETF-samenstelling beschikbaar.'),'home-muted'));return;}
 const search=homeNode('input'),controls=homeNode('div',undefined,'fund-holdings-controls'),note=homeNode('span'),previous=homeNode('button',ui('Vorige'),'secondary'),next=homeNode('button',ui('Volgende'),'secondary');
 search.type='search';search.placeholder=ui('Zoek aandeel, sector of land');search.setAttribute('aria-label',ui('Zoek aandeel, sector of land'));previous.type=next.type='button';controls.append(search,note,previous,next);target.append(controls);
 const scroll=homeNode('div',undefined,'scroll'),table=homeNode('table'),head=homeNode('thead'),tr=homeNode('tr'),body=homeNode('tbody');
 for(const label of [...(includeFund?[ui('ETF')]:[]),ui('Aandeel'),ui('Weging in ETF'),ui('Sector'),ui('Categorie'),ui('Land')]){const th=homeNode('th',label);th.scope='col';tr.append(th);}head.append(tr);table.append(head,body);scroll.append(table);target.append(scroll);let page=0;
 function draw(){const query=search.value.toLocaleLowerCase(appLocale()),matches=items.filter(h=>[h.fund_name,h.name,h.symbol,h.isin,h.sector,h.category,h.asset_type,h.country].filter(Boolean).join(' ').toLocaleLowerCase(appLocale()).includes(query));const pages=Math.max(1,Math.ceil(matches.length/50));page=Math.min(page,pages-1);body.replaceChildren();
  for(const h of matches.slice(page*50,(page+1)*50)){const row=homeNode('tr');if(includeFund)cell(row,h.fund_name);const identity=cell(row,'');if(h.fund_parent){const link=homeNode('a',h.name);link.href=fundHoldingLink(h);identity.append(link);}else identity.textContent=h.name;if(h.symbol)identity.append(homeNode('small',' · '+h.symbol));for(const value of [new Intl.NumberFormat(appLocale(),{maximumFractionDigits:6}).format(Number(h.weight))+'%',h.sector||ui('Niet ingedeeld'),h.category||h.asset_type||ui('Niet ingedeeld'),h.country||ui('Niet ingedeeld')])cell(row,value);body.append(row);}
  note.textContent=new Intl.NumberFormat(appLocale()).format(matches.length)+' '+ui('regels')+' · '+(page+1)+' / '+pages;previous.disabled=page===0;next.disabled=page>=pages-1;
  if(!matches.length){const row=homeNode('tr'),td=homeNode('td',ui('Geen gegevens voor deze selectie.'));td.colSpan=includeFund?7:6;row.append(td);body.append(row);}
 }
 search.oninput=()=>{page=0;draw();};previous.onclick=()=>{page--;draw();};next.onclick=()=>{page++;draw();};draw();
}
function renderStockFund(data){
 const panel=$('stock-fund-panel');panel.hidden=!data.is_etf&&!data.fund_composition;if(panel.hidden)return;
 const fund=data.fund_composition;$('stock-fund-open').hidden=accessSession?.user?.role!=='admin';$('stock-fund-status').textContent=fund?fundCoverageText(fund):ui('Koppel een volledige bron om alle onderliggende beleggingen te tonen.');
 const source=$('stock-fund-source');source.replaceChildren();if(fund?.source_url){const link=homeNode('a',ui('Officiële fondsbron'));link.href=fund.source_url;link.target='_blank';link.rel='noopener noreferrer';source.append(link);}else if(fund)source.textContent=ui('Geïmporteerde samenstelling');
 renderFundHoldings($('stock-fund-holdings'),(fund?.holdings||[]).map((h,index)=>({...h,fund_parent:data,fund_index:index,fund_as_of:fund.as_of})));
 const charts=$('stock-fund-charts');charts.replaceChildren();if(!fund)return;
 const exposure=fundExposure([{...data,value:100}], [fund]);
 for(const [field,title] of [['sector',ui('Sectoren')],['country',ui('Landen')]]){const card=homeNode('section',undefined,'panel report-chart-card'),heading=homeNode('h3',title),plot=homeNode('div',undefined,'report-plot'),detail=homeNode('p',undefined,'report-chart-detail');card.append(heading,plot,detail);charts.append(card);const map=new Map();for(const row of exposure){const name=row.categories[field];map.set(name,(map.get(name)||0)+row.value);}const values=[...map].map(([name,value])=>({name,value}));if(field==='country')renderCountryMap({plot,detail},values,'','fund-'+fundKey(data),{percent:true});else reportDonut({plot,detail},values,'',{percent:true});}
}
function renderFundReport(){
 const target=$('report-funds');target.replaceChildren();if(!state)return;
 const currency=$('report-currency').value,compositions=state.fund_compositions||[];let positions=state.positions.filter(p=>(!currency||p.currency===currency)&&Number(p.quantity)>0);
 if(reportType==='portfolio'){const keys=reportPortfolioKeys(state.positions,$('report-holding').value,$('report-sector').value,$('report-position-status').value);positions=positions.filter(p=>keys.has(fundKey(p)));}
 const funds=positions.filter(p=>fundIsETF(p,compositions));if(!funds.length)return;
 const details=homeNode('details',undefined,'panel fund-report'),summary=homeNode('summary',ui('ETF-samenstelling in dit rapport'));details.append(summary,homeNode('p',ui('Actuele onderliggende beleggingen. Historische winst, kosten en dividend blijven bij de geboekte ETF.'),'home-muted'));const holder=homeNode('div');details.append(holder);target.append(details);
 details.ontoggle=()=>{if(!details.open)return;holder.replaceChildren();const seen=new Set(),items=[];for(const p of funds){if(seen.has(fundKey(p)))continue;seen.add(fundKey(p));const fund=fundComposition(p,compositions);holder.append(homeNode('h3',p.name),homeNode('p',fund?fundCoverageText(fund):ui('Geen ETF-samenstelling beschikbaar.'),'home-muted'));if(fund)items.push(...fund.holdings.map((h,index)=>({...h,fund_name:p.name,fund_parent:p,fund_index:index,fund_as_of:fund.as_of})));}const table=homeNode('div');holder.append(table);renderFundHoldings(table,items,true);};
}
if(typeof document!=='undefined'){
 $('stock-fund-open').addEventListener('click',()=>{if(!stockDetail||accessSession?.user?.role!=='admin')return;const form=$('stock-fund-form');form.reset();form.elements.source_url.value=stockDetail.fund_composition?.source_url||stockDetail.fund_source||'';$('stock-fund-feedback').textContent='';openPopup('stock-fund-editor');});
 $('stock-fund-cancel').addEventListener('click',()=>closePopup('stock-fund-editor'));
 $('stock-fund-form').addEventListener('submit',async event=>{event.preventDefault();if(!stockDetail)return;const target={symbol:stockDetail.symbol,exchange:stockDetail.exchange,currency:stockDetail.currency,account_id:currentBroker},form=event.target,button=form.querySelector('button[type=submit]');button.disabled=true;
  try{const file=form.elements.csv.files[0];if(file&&file.size>8*1024*1024)throw Error(ui('Kies een CSV-bestand van maximaal 8 MB.'));if(!file&&!form.elements.source_url.value)throw Error(ui('Kies een officiële bron of een CSV-bestand.'));const payload={...target,source_url:form.elements.source_url.value,as_of:form.elements.as_of.value};if(file)payload.csv=await file.text();await jsonAction('api/instrument/holdings',payload);closePopup('stock-fund-editor');stateETag=null;await load();}catch(error){$('stock-fund-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
}
if(typeof module!=='undefined')module.exports={fundHoldingLink,fundKey,fundComposition,fundExposure,fundIsETF,fundAllocation};
