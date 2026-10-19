let currentBroker='all',importPreview=null,importProviders={trading212:'Trading 212'};
function refreshImportAccounts(){if(state)accountOptions($('import-account'),state.accounts.filter(a=>a.broker===importProviders[$('import-provider').value]),currentBroker);}
function accountOptions(select,accounts,prefer){
 const previous=select.value;select.replaceChildren();
 for(const account of accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;select.append(option);}
 if(accounts.some(a=>String(a.id)===previous))select.value=previous;
 else if(accounts.some(a=>String(a.id)===prefer))select.value=prefer;
}
function renderBrokerAccounts(){
 const filter=$('account-filter');filter.replaceChildren();const all=document.createElement('option');all.value='all';all.textContent='Alle accounts';filter.append(all);
 for(const account of state.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;filter.append(option);}filter.value=currentBroker;
 accountOptions($('purchase-account'),state.accounts,currentBroker);
 refreshImportAccounts();
 accountOptions($('t212-account'),state.accounts.filter(a=>a.broker==='Trading 212'),currentBroker);
 $('broker-list').replaceChildren();for(const account of state.accounts){const row=document.createElement('tr');cell(row,account.name);cell(row,account.broker);$('broker-list').append(row);}
 if(location.hash==='#imports'&&accessSession?.user?.role==='admin')loadImportHistory().catch(error=>{$('import-feedback').textContent=error.message;});
}
async function loadImportHistory(){
 const response=await apiFetch('api/imports');const result=await response.json();if(!response.ok)throw Error(result.error);
 const chosen=$('import-provider').value;$('import-provider').replaceChildren();for(const provider of result.providers){importProviders[provider.id]=provider.name;const option=document.createElement('option');option.value=provider.id;option.textContent=provider.name+' · '+provider.formats.join(', ').toUpperCase();$('import-provider').append(option);}if(result.providers.some(p=>p.id===chosen))$('import-provider').value=chosen;refreshImportAccounts();
 $('import-history').replaceChildren();for(const batch of result.batches){const row=document.createElement('tr');for(const value of [new Date(batch.created_at).toLocaleString('nl-NL'),batch.filename,state?.accounts.find(a=>a.id===batch.account_id)?.name??batch.account_id,batch.status==='imported'?'Geïmporteerd':'Voorbeeld'])cell(row,value);$('import-history').append(row);}
}
function showImportPreview(result){
 importPreview=result;$('import-preview').hidden=false;$('import-confirm').checked=false;$('import-rows').replaceChildren();$('import-mappings').replaceChildren();
 $('import-warnings').textContent='Bestemming: '+result.account.name+' · '+result.account.broker+'. '+result.warnings.join(' ');
 for(const entry of result.rows){const row=document.createElement('tr');for(const value of [entry.line,entry.kind??'Onbekend',entry.ticker,entry.day??'—',entry.quantity??entry.amount??'—',entry.error??(entry.duplicate?'Reeds geïmporteerd':entry.kind==='SKIP'?'Overgeslagen (geen aandelenmutatie)':'Te importeren')])cell(row,value);$('import-rows').append(row);}
 $('import-commit').disabled=result.rows.some(row=>row.error);
 result.instruments.forEach((instrument,index)=>{
  const wrapper=document.createElement('div');wrapper.className='mapping-row';
  const label=document.createElement('label');label.textContent=instrument.ticker+' · '+instrument.currency;
  const query=document.createElement('input');query.value=instrument.ticker;query.maxLength=80;query.setAttribute('aria-label','Zoek notering voor '+instrument.ticker+' '+instrument.currency);
  const search=document.createElement('button');search.type='button';search.textContent='Notering zoeken';
  const select=document.createElement('select');select.dataset.mapping=instrument.ticker+'|'+instrument.currency;select.setAttribute('aria-label','Beursnotering '+instrument.ticker+' '+instrument.currency);
  const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Kies een gecontroleerde beursnotering';select.append(placeholder);
  const feedback=document.createElement('p');feedback.setAttribute('role','status');
  search.addEventListener('click',async()=>{search.disabled=true;try{const response=await apiFetch('api/search?q='+encodeURIComponent(query.value));const result=await response.json();if(!response.ok)throw Error(result.error);select.replaceChildren(placeholder);for(const stock of result.results.filter(stock=>stock.currency===instrument.currency)){const option=document.createElement('option');option.value=JSON.stringify(stock);option.textContent=stock.name+' · '+stock.symbol+' · '+stock.exchange+' · '+stock.currency;select.append(option);}feedback.textContent=select.options.length>1?'Kies de juiste notering.':'Geen passende notering in deze valuta. De import kan zonder juiste koppeling niet doorgaan.';}catch(error){feedback.textContent=error.message;}finally{search.disabled=false;}});
  label.append(query);wrapper.append(label,search,select,feedback);$('import-mappings').append(wrapper);
 });
}
function bindImports(){
 bindTrading212();
 $('import-form').addEventListener('change',()=>{importPreview=null;$('import-preview').hidden=true;refreshImportAccounts();});
 $('account-filter').addEventListener('change',async()=>{currentBroker=$('account-filter').value;stateETag=null;await load();if(currentBroker!=='all')$('purchase-account').value=currentBroker;});
 $('broker-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{await jsonAction('api/accounts',Object.fromEntries(new FormData(event.target)));event.target.reset();stateETag=null;await load();$('broker-feedback').textContent='Brokeraccount aangemaakt.';}catch(error){$('broker-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('check-updates').addEventListener('click',async()=>{const button=$('check-updates');button.disabled=true;$('update-feedback').textContent='Versie controleren…';try{const result=await jsonAction('api/updates',{});$('update-feedback').textContent=(result.available?'Nieuwe versie beschikbaar: '+result.latest:'Je hebt de nieuwste versie: '+result.installed)+' · Laatst gecontroleerd '+new Date(result.checked_at).toLocaleString('nl-NL')+(result.available?'. Werk bij via de Home Assistant app store.':'');}catch(error){$('update-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('import-form').addEventListener('submit',async event=>{event.preventDefault();const file=$('import-file').files[0];if(!file||file.size>5*1024*1024){$('import-feedback').textContent='Kies een CSV van maximaal 5 MB.';return;}if(!$('import-account').value){$('import-feedback').textContent='Maak eerst bij Instellingen een brokeraccount met bedrijf Trading 212 aan.';return;}const button=event.target.querySelector('button');button.disabled=true;try{const result=await jsonAction('api/imports/preview',{provider:$('import-provider').value,account_id:Number($('import-account').value),filename:file.name,csv:await file.text()});showImportPreview(result);await loadImportHistory();$('import-feedback').textContent='Voorbeeld opgeslagen. Controleer de regels en koppel de beursnoteringen vóór bevestigen.';}catch(error){$('import-feedback').textContent=error.message;}finally{button.disabled=false;}});
 $('import-commit').addEventListener('click',async()=>{if(!importPreview||!$('import-confirm').checked){$('import-feedback').textContent='Controleer het voorbeeld en vink de bevestiging aan.';return;}const mappings={};for(const select of $('import-mappings').querySelectorAll('select[data-mapping]')){if(!select.value){$('import-feedback').textContent='Koppel eerst alle nieuwe tickers aan een beursnotering.';return;}mappings[select.dataset.mapping]=JSON.parse(select.value);}const button=$('import-commit');button.disabled=true;try{const result=await jsonAction('api/imports/commit',{batch_id:importPreview.batch_id,mappings});stateETag=null;await load();await loadImportHistory();$('import-preview').hidden=true;importPreview=null;$('import-feedback').textContent=result.imported+' transacties geïmporteerd. Bestaande transacties zijn niet dubbel toegevoegd.';}catch(error){$('import-feedback').textContent=error.message;button.disabled=false;}});
}
function bindTrading212(){
 const account=()=>{const value=Number($('t212-account').value);if(!value)throw Error('Maak eerst een Trading 212-brokeraccount aan bij Instellingen.');return value;};
 const action=(name,data={})=>jsonAction('api/imports/trading212/'+name,{account_id:account(),...data});
 const report=$('t212-report');report.elements.namedItem('start').value='2010-01-01';report.elements.namedItem('end').value=new Date().toLocaleDateString('en-CA');
 function bind(button,feedback,callback){button.addEventListener('click',async()=>{button.disabled=true;try{await callback();}catch(error){$(feedback).textContent=error.message;}finally{button.disabled=false;}});}
 $('t212-account').addEventListener('change',()=>{for(const name of ['key','secret'])$('t212-connection').elements.namedItem(name).value='';$('t212-connection-feedback').textContent='';$('t212-feedback').textContent='';});
 $('t212-connection').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;const data=Object.fromEntries(new FormData(event.target));try{const result=await action('save',data);$('t212-connection-feedback').textContent='Versleuteld opgeslagen · '+result.environment+'. De API wordt gecontroleerd bij het aanvragen van een rapport.';}catch(error){$('t212-connection-feedback').textContent=error.message;}finally{event.target.elements.namedItem('key').value='';event.target.elements.namedItem('secret').value='';button.disabled=false;}});
 bind($('t212-status'),'t212-connection-feedback',async()=>{const result=await action('status');$('t212-connection-feedback').textContent=result.saved?'Verbinding opgeslagen · '+result.environment+(result.pending?' · rapport in behandeling.':'.'):'Nog geen API-verbinding opgeslagen.';});
 bind($('t212-forget'),'t212-connection-feedback',async()=>{await action('forget');$('t212-connection-feedback').textContent='API-verbinding verwijderd. Reeds geïmporteerde transacties blijven bewaard.';});
 bind($('t212-cancel'),'t212-feedback',async()=>{const result=await action('cancel');$('t212-feedback').textContent=result.message;});
 report.addEventListener('submit',async event=>{event.preventDefault();const button=report.querySelector('button[type="submit"]');button.disabled=true;try{const result=await action('start',{start:report.elements.namedItem('start').value,end:report.elements.namedItem('end').value,dividends:report.elements.namedItem('dividends').checked});$('t212-feedback').textContent=result.message;}catch(error){$('t212-feedback').textContent=error.message;}finally{button.disabled=false;}});
 bind($('t212-poll'),'t212-feedback',async()=>{$('t212-feedback').textContent='Rapport controleren…';const result=await action('poll');if(result.preview){showImportPreview(result.preview);await loadImportHistory();$('t212-feedback').textContent='Rapport opgehaald. Controleer het importvoorbeeld hieronder.';}else $('t212-feedback').textContent=result.message;});
}
