let savedImportMappings=[];
function clearImportMappings(){savedImportMappings=[];$('mapping-list').replaceChildren();$('mapping-edit-form').reset();$('mapping-filter').value='';$('mapping-edit-title').textContent='';$('mapping-edit-feedback').textContent='';$('mapping-feedback').textContent='';closePopup('mapping-edit');}
async function loadImportMappings(){
 $('mapping-feedback').textContent='Koppelingen uit de database laden…';
 try{const response=await apiFetch('api/imports/mappings');const result=await response.json();if(!response.ok)throw Error(result.error);savedImportMappings=result.mappings;renderImportMappings();$('mapping-feedback').textContent=result.mappings.length+' koppelingen en openstaande instrumenten. Deze lijst gebruikt geen koersdienst.';}
 catch(error){$('mapping-feedback').textContent=error.message;}
}
function renderImportMappings(){
 const query=$('mapping-filter').value.trim().toLowerCase();$('mapping-list').replaceChildren();
 for(const entry of savedImportMappings){
  if(query&&!Object.values(entry).join(' ').toLowerCase().includes(query))continue;
  const row=document.createElement('tr');
  for(const value of [entry.account_name,entry.ticker,entry.isin||'—',entry.source_currency,entry.symbol||'Nog niet gekoppeld',entry.exchange||'—',entry.currency||'—',entry.origin==='manual'?'Handmatig gecontroleerd':entry.symbol?'Automatisch opgeslagen':'Openstaand'])cell(row,value);
  const action=cell(row,'');const button=document.createElement('button');button.type='button';button.textContent=entry.symbol?'Corrigeren':'Koppelen';
  button.addEventListener('click',()=>{const form=$('mapping-edit-form');form.elements.namedItem('id').value=entry.id;for(const key of ['symbol','exchange','currency'])form.elements.namedItem(key).value=entry[key];$('mapping-edit-title').textContent=entry.ticker+' / '+entry.source_currency+' · '+entry.account_name;openPopup('mapping-edit');$('mapping-edit-feedback').textContent='';form.elements.namedItem('symbol').focus();});action.append(button);$('mapping-list').append(row);
 }
}
function bindImportMappings(){
 $('mapping-filter').addEventListener('input',renderImportMappings);
 $('mapping-refresh').addEventListener('click',loadImportMappings);
 $('mapping-cancel').addEventListener('click',()=>{closePopup('mapping-edit');});
 $('mapping-check').addEventListener('click',async()=>{
  const button=$('mapping-check'),form=$('mapping-edit-form');button.disabled=true;
  try{const symbol=form.elements.namedItem('symbol').value.trim().toUpperCase();const response=await apiFetch('api/listing?symbol='+encodeURIComponent(symbol));const result=await response.json();if(!response.ok)throw Error(result.error);for(const key of ['symbol','exchange','currency'])form.elements.namedItem(key).value=result[key];$('mapping-edit-feedback').textContent='Gecontroleerd: '+result.name+' · '+result.exchange+' · '+result.currency+'. Controleer of dit het juiste aandeel is en sla op.';}
  catch(error){$('mapping-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
 $('mapping-edit-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.target.querySelector('[type="submit"]');button.disabled=true;
  try{const result=await jsonAction('api/imports/mappings',Object.fromEntries(new FormData(event.target)));$('mapping-edit-feedback').textContent=result.message;await loadImportMappings();}
  catch(error){$('mapping-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
}
