/* Costs use their own source currency; zero is shown only for known entries. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
const chargeLabels={COMMISSION:ui('Transactiekosten'),CUSTODY:ui('Bewaarloon'),FX_FEE:ui('Valutakosten'),OTHER_FEE:ui('Overige kosten'),VAT:ui('Btw'),WITHHOLDING_TAX:ui('Dividendbelasting'),TRANSACTION_TAX:ui('Transactiebelasting'),OTHER_TAX:ui('Overige belastingen')};
let chargeData=null,chargeDataKey='',chargePending=false,chargeError='',chargeGeneration=0;
function clearChargeReport(){chargeGeneration++;chargeData=null;chargeDataKey='';chargePending=false;chargeError='';}
function chargeScope(){return JSON.stringify([String(currentBroker),state?.data_revision,$('report-year').value,$('report-currency').value,reportType]);}
function chargeQuery(){return new URLSearchParams({account_id:currentBroker,year:$('report-year').value,currency:$('report-currency').value,view:reportType==='taxes'?'taxes':'all'}).toString();}
async function loadChargeReport(){
 const key=chargeScope(),generation=++chargeGeneration;chargeDataKey=key;chargeData=null;chargePending=true;chargeError='';
 try{const response=await apiFetch('api/reports/charges?'+chargeQuery());const result=await response.json();if(!response.ok)throw Error(result.error);if(generation===chargeGeneration&&key===chargeScope()&&accessSession?.user)chargeData=result;}
 catch(error){if(generation===chargeGeneration&&key===chargeScope())chargeError=error.message;}
 finally{if(generation===chargeGeneration){chargePending=false;if(['costs','taxes'].includes(reportType)&&location.hash.startsWith('#rapporten'))renderChargeReport();}}
}
function chargeButton(label,handler){const button=homeNode('button',label,'secondary');button.type='button';button.onclick=handler;return button;}
function renderChargeReport(){
 $('report-description').textContent=ui('Alleen expliciet vastgelegde bedragen. Ontbrekende kosten zijn onbekend, niet nul. Btw wordt niet uit een tarief geschat.');
 for(const id of ['report-metrics','report-charts','report-insights','report-rows','report-head'])$(id).replaceChildren();
 const key=chargeScope();if(key!==chargeDataKey){loadChargeReport();}
 const controls=homeNode('section',undefined,'panel report-wide');
 if(accessSession?.user?.role==='admin'&&currentProfile!=='demo'){
  controls.append(chargeButton(ui('Kosten of belasting toevoegen'),openChargeEditor));
  const download=homeNode('a',ui('Kostenrapport downloaden'),'button secondary');download.href='api/charges/export?'+chargeQuery();if(accessSession.enabled)controls.append(download);
  controls.append(chargeButton(ui('Ontbrekende wisselkoersen ophalen'),async()=>{try{await jsonAction('api/charges/fx',Object.fromEntries(new URLSearchParams(chargeQuery())));clearChargeReport();stateETag=null;await load();}catch(error){$('report-status').textContent=error.message;}}));
 }
 controls.append(homeNode('p',ui('Positief is betaald; negatief is terugontvangen. Reeds netto verwerkt betekent dat het bedrag al in het bestaande resultaat zit.')));$('report-charts').append(controls);
 if(chargePending||key!==chargeDataKey){$('report-status').textContent=ui('Laden…');$('report-count').textContent='';return;}
 if(chargeError){$('report-status').textContent=chargeError;controls.append(chargeButton(ui('Opnieuw proberen'),()=>{clearChargeReport();renderChargeReport();}));return;}
 if(!chargeData){$('report-status').textContent=ui('Geen kosten vastgelegd.');return;}
 $('report-status').textContent=chargeData.missing_fx.length?ui('Onvolledig totaal: ontbrekende historische wisselkoersen.')+' '+chargeData.missing_fx.length:ui('Rapport bevat uitsluitend de vastgelegde kosten en belastingen.');
 $('report-count').textContent=String(chargeData.entries.length);
 const group=chargeData.total,known=chargeData.entries.length>0,converted=group.count>0;
 reportMetric(ui('Totaal alle valuta’s in EUR'),converted?money(group.total,'EUR'):'—',chargeData.complete?ui('Geboekte kosten en belastingen'):ui('Onvolledig'));
 reportMetric(ui('Reeds netto verwerkt'),converted?money(group.included,'EUR'):'—',ui('Niet nogmaals aftrekken van het resultaat.'));
 reportMetric(ui('Aanvullende resultaatimpact'),converted?money(Number(group.additional)?-Number(group.additional):0,'EUR'):'—',ui('Alleen bedragen die nog niet in het bestaande nettoresultaat zitten.'));
 if(!known)$('report-charts').append(homeNode('p',ui('Geen kosten vastgelegd.'),'report-wide'));
 for(const g of [{...group,label:ui('Totaal alle valuta’s in EUR')},...chargeData.currencies.map(g=>({...g,label:ui('Uitsplitsing per valuta')+' · '+g.currency}))]){
  if(!g.count)continue;
  $('report-charts').append(homeNode('h3',g.label,'report-group-heading report-wide'));
  const categories=reportChartCard(g,ui('Kosten en belastingen per soort'),ui('Nettobedragen na terugbetalingen.'));
  reportBars(categories,Object.entries(g.categories).map(([name,value])=>({name:chargeLabels[name],value:Number(value)})),g.currency,true,true);
  const months=reportChartCard(g,ui('Kosten en belastingen per maand'),ui('Nettobedragen na terugbetalingen.'));
  reportBars(months,Object.entries(g.months).sort().map(([name,value])=>({name:reportMonth(name),value:Number(value)})),g.currency,true,true);
 }
 const head=document.createElement('tr');for(const title of [ui('Datum'),ui('Brokeraccount'),ui('Soort'),ui('Aandeel'),ui('Bedrag'),ui('Reeds netto verwerkt'),ui('Bedrag in EUR'),ui('Factor'),ui('Koersdatum'),ui('Bronreferentie')]){head.append(homeNode('th',title));}$('report-head').append(head);
 for(const entry of chargeData.entries){const row=document.createElement('tr');for(const value of [dayLabel(entry.paid_on),entry.account_name,chargeLabels[entry.category],entry.ticker||'—',money(entry.amount,entry.currency),entry.included_in_net?ui('Ja'):ui('Nee'),entry.eur_amount===null?ui('Ontbrekende koers'):money(entry.eur_amount,'EUR'),entry.rate===null?'—':new Intl.NumberFormat(appLocale(),{maximumFractionDigits:8}).format(Number(entry.rate)),entry.rate_on?dayLabel(entry.rate_on):'—',entry.external_id])cell(row,value);$('report-rows').append(row);}
}
function chargeField(form,label,name,type='text'){
 const control=document.createElement(type==='select'?'select':'input');if(type!=='select')control.type=type;control.name=name;const wrapper=homeNode('label',label);wrapper.append(control);form.append(wrapper);return control;
}
function chargeAccounts(select){select.replaceChildren();const empty=homeNode('option',ui('Kies een brokeraccount'));empty.value='';select.append(empty);for(const account of state.accounts){const option=homeNode('option',account.name+' · '+account.broker);option.value=account.id;select.append(option);}if(state.accounts.some(a=>String(a.id)===String(currentBroker)))select.value=currentBroker;select.required=true;}
let chargeEditorBuilt=false;
function openChargeEditor(){
 if(!chargeEditorBuilt)buildChargeEditor();
 const form=$('charge-entry-form');form.reset();chargeAccounts(form.elements.namedItem('account_id'));chargeAccounts($('charge-csv-form').elements.namedItem('account_id'));form.elements.namedItem('date').value=[new Date().getFullYear(),String(new Date().getMonth()+1).padStart(2,'0'),String(new Date().getDate()).padStart(2,'0')].join('-');form.elements.namedItem('currency').value='EUR';form.elements.namedItem('category').value=reportType==='taxes'?'OTHER_TAX':'COMMISSION';$('charge-entry-feedback').textContent='';openPopup('charge-editor');
}
function buildChargeEditor(){
 const panel=homeNode('section',undefined,'popup-content');panel.id='charge-editor';document.body.append(panel);
 panel.append(homeNode('p',ui('Gebruik bedragen uit je bronoverzicht. Boek een jaartotaal niet opnieuw als dezelfde kosten al per transactie zijn vastgelegd. Btw voer je apart in; gebruik voor de kosten het bedrag exclusief die btw.')));
 const form=document.createElement('form');form.id='charge-entry-form';panel.append(form);
 chargeField(form,ui('Brokeraccount'),'account_id','select');chargeField(form,ui('Datum'),'date','date').required=true;
 const category=chargeField(form,ui('Soort'),'category','select');for(const [value,label] of Object.entries(chargeLabels)){const option=homeNode('option',label);option.value=value;category.append(option);}
 const amount=chargeField(form,ui('Bedrag: positief betaald, negatief terugontvangen'),'amount','number');amount.required=true;amount.step='any';
 const currency=chargeField(form,ui('Valuta'),'currency');currency.required=true;currency.maxLength=3;
 const ticker=chargeField(form,ui('Aandeel (optioneel)'),'ticker');ticker.maxLength=30;
 const reference=chargeField(form,ui('Unieke bronreferentie'),'reference');reference.required=true;reference.maxLength=120;
 chargeField(form,ui('Omschrijving'),'description').maxLength=500;
 const net=chargeField(form,ui('Al verwerkt in bestaand nettoresultaat'),'included_in_net','checkbox');
 const save=homeNode('button',ui('Kostenboeking opslaan'));save.type='submit';form.append(save);
 const feedback=homeNode('p');feedback.id='charge-entry-feedback';feedback.setAttribute('role','status');panel.append(feedback);
 form.onsubmit=async event=>{event.preventDefault();save.disabled=true;try{const data=Object.fromEntries(new FormData(form));data.included_in_net=net.checked?'1':'0';const result=await jsonAction('api/charges/save',data);if(result.pending){feedback.textContent=ui('Boeking vraagt beoordeling. Controleer Te beoordelen.');return;}closePopup('charge-editor');clearChargeReport();stateETag=null;await load();}catch(error){feedback.textContent=error.message;}finally{save.disabled=false;}};
 panel.append(homeNode('h3',ui('Aanvullende kosten importeren')));
 panel.append(homeNode('p',ui('Gebruik het CSV-sjabloon. Elke regel bevat een expliciet bedrag, valuta, datum en unieke referentie. included_in_net is 1 als het bedrag al in het bestaande nettoresultaat zit, anders 0.')));
 const template=homeNode('a',ui('CSV-sjabloon downloaden'),'button secondary');template.href='data:text/csv;charset=utf-8,'+encodeURIComponent('date,reference,category,amount,currency,ticker,included_in_net,description\n');template.download='home-invest-charges-template.csv';panel.append(template,homeNode('p',Object.entries(chargeLabels).map(([code,label])=>code+' = '+label).join(' · ')));
 const csvForm=document.createElement('form');csvForm.id='charge-csv-form';panel.append(csvForm);chargeField(csvForm,ui('Brokeraccount'),'account_id','select');const file=chargeField(csvForm,ui('CSV-bestand'),'file','file');file.accept='.csv,text/csv';file.required=true;
 const upload=homeNode('button',ui('Importvoorbeeld openen'));upload.type='submit';csvForm.append(upload);
 csvForm.onsubmit=async event=>{event.preventDefault();const source=file.files[0];if(!source||source.size>5*1024*1024){feedback.textContent=ui('Kies een CSV van maximaal 5 MB.');return;}upload.disabled=true;try{const result=await jsonAction('api/imports/preview',{provider:'charges',account_id:Number(csvForm.elements.namedItem('account_id').value),filename:source.name,csv:await source.text()});closePopup('charge-editor');showImportPreview(result);}catch(error){feedback.textContent=error.message;}finally{upload.disabled=false;}};
 panel.append(chargeButton(ui('Annuleren'),()=>closePopup('charge-editor')));registerPopup('charge-editor',ui('Kosten of belasting toevoegen'));chargeEditorBuilt=true;
}
