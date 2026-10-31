/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
function updateImportSource(){
 $('import-upload-feedback').textContent='';
 const tradeRepublic=$('import-provider').value==='traderepublic';
 $('import-source-help').textContent=$('import-provider').value==='revolut'?ui('Revolut: upload de Engelstalige CSV van je beleggingsrekening. Onbekende acties blijven ter beoordeling.'):tradeRepublic?ui('Trade Republic: profiel → afschriften → transactie-export. Upload de oorspronkelijke CSV. Alleen aandelen en fondsen; onbekende acties en dividendcorrecties blijven ter beoordeling.'):ui('Trading 212: upload de Engelstalige History CSV uit Invest of Stocks ISA. Een API-rapport kun je via de knop hierboven ophalen.');
 const available=!!$('import-account').value;
 $('import-account-help').hidden=available;
 $('import-account').disabled=!available;
 $('import-form').querySelector('button[type=submit]').disabled=!available;
}
let currentBroker='all',importPreview=null,importProviders={trading212:'Trading 212',traderepublic:'Trade Republic',revolut:ui('Revolut')};
function refreshImportAccounts(){if(state)accountOptions($('import-account'),state.accounts.filter(a=>a.broker===importProviders[$('import-provider').value]),currentBroker);updateImportSource();}
function accountOptions(select,accounts,prefer){
 const previous=select.value;select.replaceChildren();
 if(!accounts.length){const option=document.createElement('option');option.value='';option.textContent=ui('Nog geen passende brokerrekening');select.append(option);}
 for(const account of accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;select.append(option);}
 if(accounts.some(a=>String(a.id)===previous))select.value=previous;
 else if(accounts.some(a=>String(a.id)===prefer))select.value=prefer;
}
function renderBrokerAccounts(){
 if(currentBroker!=='all'&&!state.accounts.some(account=>String(account.id)===currentBroker))currentBroker='all';
 renderDeleteAccounts();
 const filter=$('account-filter');filter.replaceChildren();const all=document.createElement('option');all.value='all';all.textContent=ui('Alle accounts');filter.append(all);
 for(const account of state.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;filter.append(option);}filter.value=currentBroker;
 accountOptions($('purchase-account'),state.accounts,currentBroker);
 refreshImportAccounts();
 accountOptions($('t212-account'),state.accounts.filter(a=>a.broker==='Trading 212'),currentBroker);
 accountOptions($('t212-report-account'),state.accounts.filter(a=>a.broker==='Trading 212'),currentBroker);
 $('broker-list').replaceChildren();for(const account of state.accounts){const row=document.createElement('tr');cell(row,account.name);cell(row,account.broker);const actions=cell(row,'');for(const [label,handler] of [[ui('Aanpassen'),()=>openBrokerEditor(account.id)],[ui('Verwijderen'),()=>openBrokerDeletion(account.id)]]){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=label;button.addEventListener('click',handler);actions.append(button);}$('broker-list').append(row);}
 if((location.hash==='#import-geschiedenis'||/^#import-(trading212|traderepublic|revolut)$/.test(location.hash))&&accessSession?.user?.role==='admin')loadImportHistory().catch(error=>{$('import-feedback').textContent=error.message;});
}
async function loadImportHistory(){
 const response=await apiFetch('api/imports');const result=await response.json();if(!response.ok)throw Error(result.error);
 const chosen=location.hash.match(/^#import-(trading212|traderepublic|revolut)$/)?.[1]||$('import-provider').value;$('import-provider').replaceChildren();for(const provider of result.providers){importProviders[provider.id]=provider.name;const option=document.createElement('option');option.value=provider.id;option.textContent=provider.name+' · '+provider.formats.join(', ').toUpperCase();$('import-provider').append(option);}if(result.providers.some(p=>p.id===chosen))$('import-provider').value=chosen;refreshImportAccounts();
 $('import-history').replaceChildren();if(!result.batches.length){const row=document.createElement('tr');const empty=cell(row,ui('Nog geen imports. Begin bij het brokeroverzicht.'));empty.colSpan=5;$('import-history').append(row);}for(const batch of result.batches){if(location.hash.match(/^#import-(trading212|traderepublic|revolut)$/)&&batch.provider!==chosen)continue;const row=document.createElement('tr');for(const value of [new Date(batch.created_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL')),batch.filename,state?.accounts.find(a=>a.id===batch.account_id)?.name??batch.account_id,batch.status==='imported'?ui('Geïmporteerd'):batch.status==='partial'?ui('Deels verwerkt - beoordeling nodig'):ui('Voorbeeld')])cell(row,value);const action=cell(row,'');if(batch.status==='preview'||batch.status==='partial'){const button=document.createElement('button');button.type='button';button.textContent=ui('Voorbeeld openen');button.addEventListener('click',async()=>{button.disabled=true;try{showImportPreview(await jsonAction('api/imports/open',{batch_id:batch.id}));$('import-feedback').textContent=ui('Opgeslagen voorbeeld geopend; noteringen worden automatisch gekoppeld.');}catch(error){$('import-feedback').textContent=error.message;}finally{button.disabled=false;}});action.append(button);}$('import-history').append(row);}
}
function importProblems(result){
 const problems=result.rows.filter(row=>row.error).map(row=>ui('Regel ')+row.line+' - '+(row.ticker||row.kind||ui('Transactie'))+': '+row.error);
 for(const instrument of result.instruments){const key=instrument.ticker+'|'+instrument.currency;if(!result.rows.some(row=>row.ticker+'|'+row.currency===key&&row.mapping))problems.push(instrument.ticker+' - '+instrument.currency+': '+(instrument.error||ui('Beurskoppeling ontbreekt. Gebruik Automatisch opnieuw koppelen.')));}
 return problems;
}
function showImportProblems(problems){
 const feedback=$('import-commit-feedback');feedback.replaceChildren();
 if(!problems.length){feedback.textContent=ui('Alle beurskoppelingen zijn gereed. Vink de bevestiging aan en sla de import op.');return;}
 const title=document.createElement('strong');title.textContent=ui('Deze regels worden apart gehouden voor beoordeling; de overige regels kun je importeren:');feedback.append(title);
 const list=document.createElement('ul');for(const problem of problems){const item=document.createElement('li');item.textContent=problem;list.append(item);}feedback.append(list);
}
function showImportPreview(result){
 location.hash='import-voorbeeld';
 importPreview=result;$('import-commit').textContent=ui('Import definitief opslaan');$('import-preview').hidden=false;$('import-confirm').checked=false;$('import-rows').replaceChildren();$('import-mappings').replaceChildren();
 $('import-warnings').textContent=ui('Bestemming: ')+result.account.name+' · '+result.account.broker+'. '+result.warnings.join(' ');
 for(const entry of result.rows){const row=document.createElement('tr');for(const value of [entry.line,entry.kind??ui('Onbekend'),entry.ticker,entry.day??'—',entry.quantity??entry.amount??'—',entry.error??(entry.duplicate?ui('Reeds geïmporteerd'):entry.kind==='SPLIT_INFO'?ui('Splitsing: oude aantal (controle bij open)'):entry.kind==='SKIP'?entry.notice||ui('Overgeslagen (geen aandelenmutatie)'):entry.notice||ui('Te importeren'))])cell(row,value);$('import-rows').append(row);}
 $('import-commit').disabled=false;showImportProblems(importProblems(result));
 const statuses=new Map();
 for(const instrument of result.instruments){const row=document.createElement('div');row.className='auto-mapping-row';const title=document.createElement('strong');title.textContent=instrument.ticker+' · '+instrument.currency;const status=document.createElement('p');status.textContent=ui('Automatisch koppelen…');row.append(title,status);$('import-mappings').append(row);statuses.set(instrument.ticker+'|'+instrument.currency,status);}
 async function matchAll(){
  const retry=$('import-rematch');retry.disabled=true;$('import-commit').disabled=false;
  try{for(const instrument of result.instruments){
   if(importPreview!==result||accessSession?.user?.role!=='admin')return;
   const key=instrument.ticker+'|'+instrument.currency;const rows=result.rows.filter(r=>r.ticker+'|'+r.currency===key);let mapping=rows.find(r=>r.mapping)?.mapping;
   if(!mapping){try{const found=await jsonAction('api/imports/resolve',{batch_id:result.batch_id,key});if(importPreview!==result)return;mapping=found.mapping;if(!mapping){instrument.error=found.error;statuses.get(key).textContent=found.error;if(found.retry_later){$('import-feedback').textContent=found.error;for(const remaining of result.instruments){const remainingKey=remaining.ticker+'|'+remaining.currency;if(!result.rows.some(r=>r.ticker+'|'+r.currency===remainingKey&&r.mapping)){remaining.error=found.error;statuses.get(remainingKey).textContent=found.error;}}break;}continue;}for(const row of rows)row.mapping=mapping;}catch(error){if(importPreview!==result)return;instrument.error=error.message;statuses.get(key).textContent=error.message;continue;}}
   delete instrument.error;statuses.get(key).textContent=ui('Automatisch gekoppeld: ')+mapping.name+' · '+mapping.symbol+' · '+mapping.exchange+' · '+mapping.currency+(instrument.currency!==mapping.currency?ui(' · Bij import historisch omrekenen: ')+instrument.currency+' → '+mapping.currency:'');
  }}finally{if(importPreview===result){retry.disabled=false;$('import-commit').disabled=false;showImportProblems(importProblems(result));}}
 }
 $('import-rematch').onclick=matchAll;matchAll();
}
function bindImports(){
 bindTrading212();
 let returnToImport=null;
 $('import-account-add').addEventListener('click',()=>{
  const form=$('broker-form'),provider=$('import-provider').value;
  returnToImport={hash:location.hash,ids:new Set(state.accounts.map(account=>account.id))};
  form.reset();form.elements.namedItem('broker').value=importProviders[provider];form.elements.namedItem('broker').readOnly=true;
  form.elements.namedItem('name').value=importProviders[provider];$('broker-feedback').textContent='';
  openPopup('broker-form-editor');
 });
 $('broker-form-editor-popup').addEventListener('close',()=>{
  const resume=returnToImport;returnToImport=null;$('broker-form').elements.namedItem('broker').readOnly=false;
  if(resume&&location.hash===resume.hash)openPopup('import-form-editor');
 });
 for(const button of document.querySelectorAll('[data-import-provider]'))button.addEventListener('click',()=>{$('import-provider').value=button.dataset.importProvider;refreshImportAccounts();openPopup('import-form-editor');});
 $('import-api-report-open').addEventListener('click',()=>openPopup('import-api-report'));
 $('import-form').addEventListener('change',()=>{importPreview=null;$('import-preview').hidden=true;refreshImportAccounts();});
 $('account-filter').addEventListener('change',async()=>{
  currentBroker=$('account-filter').value;stateETag=null;stateRequest++;state=null;
  clearHomeDashboard();clearStocksDashboard();clearCategoryOverview();clearDividendDashboard();clearStockDetail();clearTransactions();clearReports();
  for(const id of ['totals','chart','chart-days'])$(id).replaceChildren();
  await load();if(currentBroker!=='all')$('purchase-account').value=currentBroker;
 });
 $('broker-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{await jsonAction('api/accounts',Object.fromEntries(new FormData(event.target)));event.target.reset();stateETag=null;await load();$('broker-feedback').textContent=ui('Brokeraccount aangemaakt.');if(returnToImport){const created=state.accounts.find(account=>!returnToImport.ids.has(account.id)&&account.broker===importProviders[$('import-provider').value]);if(created){$('import-account').value=created.id;updateImportSource();closePopup('broker-form-editor');}}}catch(error){$('broker-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('check-updates').addEventListener('click',async()=>{const button=$('check-updates');button.disabled=true;$('update-feedback').textContent=ui('Versie controleren…');try{const result=await jsonAction('api/updates',{});$('update-feedback').textContent=(result.available?ui('Nieuwe versie beschikbaar: ')+result.latest:ui('Je hebt de nieuwste versie: ')+result.installed)+ui(' · Laatst gecontroleerd ')+new Date(result.checked_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL'))+(result.available?ui('. Werk bij via de Home Assistant app store.'):'');}catch(error){$('update-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('import-form').addEventListener('submit',async event=>{event.preventDefault();const file=$('import-file').files[0];if(!file||file.size>5*1024*1024){$('import-upload-feedback').textContent=ui('Kies een CSV van maximaal 5 MB.');return;}if(!$('import-account').value){$('import-upload-feedback').textContent=ui('Maak eerst bij Instellingen een brokeraccount met bedrijf ')+importProviders[$('import-provider').value]+ui(' aan.');return;}const button=event.target.querySelector('button');button.disabled=true;try{const result=await jsonAction('api/imports/preview',{provider:$('import-provider').value,account_id:Number($('import-account').value),filename:file.name,csv:await file.text()});closePopup('import-form-editor');showImportPreview(result);await loadImportHistory();$('import-feedback').textContent=ui('Voorbeeld opgeslagen. Controleer de regels en koppel de beursnoteringen vóór bevestigen.');}catch(error){$('import-upload-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('import-commit').addEventListener('click',async()=>{if(!importPreview)return;const problems=importProblems(importPreview);if(problems.length)showImportProblems(problems);if(!$('import-confirm').checked){$('import-commit-feedback').textContent=ui('Vink eerst aan dat je het voorbeeld en de beursnoteringen hebt gecontroleerd.');return;}const mappings={};const button=$('import-commit');button.disabled=true;button.textContent=ui('Dagkoersen controleren en importeren…');try{const result=await jsonAction('api/imports/commit',{batch_id:importPreview.batch_id,mappings});stateETag=null;await load();await loadImportHistory();$('import-preview').hidden=true;importPreview=null;$('import-feedback').textContent=result.imported+ui(' transacties geïmporteerd. ')+(result.pending??0)+ui(' regels apart gehouden: open Imports > Te beoordelen. Bestaande transacties zijn niet dubbel toegevoegd.')+(result.standalone_dividends?' '+result.standalone_dividends+ui(' dividendontvangsten apart opgeslagen zonder voorafgaande aankoop. Zie Dividend voor de melding over ontbrekende aankoophistorie.'):'');if(result.pending)location.hash='import-beoordeling';}catch(error){$('import-feedback').textContent=error.message;$('import-commit-feedback').textContent=error.message;button.disabled=false;button.textContent=ui('Import definitief opslaan');}});
}
function bindTrading212(){
 const account=(report=false)=>{const value=Number($(report?'t212-report-account':'t212-account').value);if(!value)throw Error(ui('Maak eerst een Trading 212-brokeraccount aan bij Instellingen.'));return value;};
 const action=(name,data={})=>jsonAction('api/imports/trading212/'+name,{account_id:account(['start','poll','cancel'].includes(name)),...data});
 const report=$('t212-report');report.elements.namedItem('start').value=new Date().getFullYear()+'-01-01';report.elements.namedItem('end').value=new Date().toLocaleDateString('en-CA');
 function bind(button,feedback,callback){button.addEventListener('click',async()=>{button.disabled=true;try{await callback();}catch(error){$(feedback).textContent=error.message;}finally{button.disabled=false;}});}
 $('t212-account').addEventListener('change',()=>{for(const name of ['key','secret'])$('t212-connection').elements.namedItem(name).value='';$('t212-connection-feedback').textContent='';$('t212-feedback').textContent='';});
 $('t212-connection').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;const data=Object.fromEntries(new FormData(event.target));try{const result=await action('save',data);$('t212-connection-feedback').textContent=ui('Versleuteld opgeslagen · ')+result.environment+ui('. De API wordt gecontroleerd bij het aanvragen van een rapport.');}catch(error){$('t212-connection-feedback').textContent=error.message;}finally{event.target.elements.namedItem('key').value='';event.target.elements.namedItem('secret').value='';button.disabled=false;}});
 bind($('t212-status'),'t212-connection-feedback',async()=>{const result=await action('status');$('t212-connection-feedback').textContent=result.saved?ui('Verbinding opgeslagen · ')+result.environment+(result.pending?' · '+(result.total!==undefined?result.completed+ui(' van ')+result.total+ui(' rapporten opgehaald.'):ui('rapport in behandeling.')):'.'):ui('Nog geen API-verbinding opgeslagen.');});
 bind($('t212-forget'),'t212-connection-feedback',async()=>{await action('forget');$('t212-connection-feedback').textContent=ui('API-verbinding verwijderd. Reeds geïmporteerde transacties blijven bewaard.');});
 bind($('t212-cancel'),'t212-feedback',async()=>{const result=await action('cancel');$('t212-feedback').textContent=result.message;});
 report.addEventListener('submit',async event=>{event.preventDefault();const button=report.querySelector('button[type="submit"]');button.disabled=true;try{const result=await action('start',{start:report.elements.namedItem('start').value,end:report.elements.namedItem('end').value,dividends:report.elements.namedItem('dividends').checked});$('t212-feedback').textContent=result.message;}catch(error){$('t212-feedback').textContent=error.message;}finally{button.disabled=false;}});
 bind($('t212-poll'),'t212-feedback',async()=>{$('t212-feedback').textContent=ui('Rapport controleren…');const result=await action('poll');if(result.preview){closePopup('import-api-report');showImportPreview(result.preview);await loadImportHistory();$('t212-feedback').textContent=ui('Rapport opgehaald. Controleer het importvoorbeeld hieronder.');}else $('t212-feedback').textContent=result.message;});
}
