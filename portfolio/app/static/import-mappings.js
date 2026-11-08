/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let savedImportMappings=[];
function clearImportMappings(){savedImportMappings=[];$('mapping-list').replaceChildren();$('mapping-edit-form').reset();$('mapping-filter').value='';$('mapping-edit-title').textContent='';$('mapping-edit-feedback').textContent='';$('mapping-feedback').textContent='';closePopup('mapping-edit');}
async function loadImportMappings(){
 $('mapping-feedback').textContent=ui('Koppelingen uit de database laden…');
 try{const response=await apiFetch('api/imports/mappings');const result=await response.json();if(!response.ok)throw Error(result.error);savedImportMappings=result.mappings;renderImportMappings();$('mapping-feedback').textContent=result.mappings.length+ui(' koppelingen en openstaande instrumenten. Deze lijst gebruikt geen koersdienst.');}
 catch(error){$('mapping-feedback').textContent=error.message;}
}
function renderImportMappings(){
 const query=$('mapping-filter').value.trim().toLowerCase();$('mapping-list').replaceChildren();
 for(const entry of savedImportMappings){
  if(query&&!Object.values(entry).join(' ').toLowerCase().includes(query))continue;
  const row=document.createElement('tr');
  for(const value of [entry.account_name,entry.ticker,entry.isin||'—',entry.source_currency,entry.symbol||ui('Nog niet gekoppeld'),entry.exchange||'—',entry.currency||'—',entry.origin==='manual'?ui('Handmatig gecontroleerd'):entry.symbol?ui('Automatisch opgeslagen'):ui('Openstaand')])cell(row,value);
  const action=cell(row,'');const button=document.createElement('button');button.type='button';button.textContent=entry.symbol?ui('Corrigeren'):ui('Koppelen');
  button.addEventListener('click',()=>{const form=$('mapping-edit-form');form.elements.namedItem('id').value=entry.id;for(const key of ['symbol','exchange','currency'])form.elements.namedItem(key).value=entry[key]||(key==='symbol'?entry.ticker:'');$('mapping-edit-title').textContent=entry.ticker+' / '+entry.source_currency+' · '+entry.account_name;openPopup('mapping-edit');$('mapping-edit-feedback').textContent='';form.elements.namedItem('symbol').focus();});action.append(button);$('mapping-list').append(row);
 }
}
async function suggestImportListings(form,symbol,entry,error){
 const feedback=$('mapping-edit-feedback');
 const queries=[...new Set([entry?.isin,entry?.name,symbol,symbol.replace(/\d+$/,'')])].filter(q=>q?.length>=2&&q.length<=80);
 const results=await Promise.allSettled(queries.map(async q=>{
  const response=await apiFetch('api/search?q='+encodeURIComponent(q));
  if(!response.ok)return [];
  return (await response.json()).results||[];
 }));
 if(form.elements.namedItem('id').value!==String(entry?.id)||form.elements.namedItem('symbol').value.trim().toUpperCase()!==symbol)return;
 const matches=new Map();
 for(const result of results)if(result.status==='fulfilled')for(const stock of result.value){
  matches.set(JSON.stringify([stock.symbol,stock.exchange,stock.currency]),stock);
 }
 feedback.textContent=matches.size?ui('Kies een mogelijke notering en controleer of die bij je brokertransactie hoort.'):error.message;
 for(const stock of [...matches.values()].slice(0,10)){
  const option=document.createElement('button');
  option.type='button';option.className='secondary';
  option.textContent=[stock.name,stock.symbol,stock.exchange,stock.currency].join(' · ');
  option.addEventListener('click',()=>{
   form.elements.namedItem('symbol').value=stock.symbol;
   for(const field of ['exchange','currency'])form.elements.namedItem(field).value='';
   $('mapping-check').click();
  });
  feedback.append(option);
 }
}
function bindImportMappings(){
 $('mapping-filter').addEventListener('input',renderImportMappings);
 $('mapping-refresh').addEventListener('click',loadImportMappings);
 $('mapping-cancel').addEventListener('click',()=>{closePopup('mapping-edit');});
 $('mapping-check').addEventListener('click',async()=>{
  const button=$('mapping-check'),form=$('mapping-edit-form');button.disabled=true;
  const symbol=form.elements.namedItem('symbol').value.trim().toUpperCase();
  const entry=savedImportMappings.find(row=>String(row.id)===form.elements.namedItem('id').value);
  try{const response=await apiFetch('api/listing?symbol='+encodeURIComponent(symbol));if(!response.headers.get('Content-Type')?.includes('application/json'))throw Error(ui('De notering of koersvaluta kon niet worden gecontroleerd. Probeer later opnieuw.'));const result=await response.json();if(!response.ok)throw Error(result.error);for(const key of ['symbol','exchange','currency'])form.elements.namedItem(key).value=result[key];$('mapping-edit-feedback').textContent=ui('Gecontroleerd: ')+result.name+' · '+result.exchange+' · '+result.currency+ui('. Controleer of dit het juiste aandeel is en sla op.');}
  catch(error){await suggestImportListings(form,symbol,entry,error);}finally{button.disabled=false;}
 });
 $('mapping-edit-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.target.querySelector('[type="submit"]');button.disabled=true;
  try{const result=await jsonAction('api/imports/mappings',Object.fromEntries(new FormData(event.target)));$('mapping-edit-feedback').textContent=result.message;await loadImportMappings();}
  catch(error){$('mapping-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
}
