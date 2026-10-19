/* Diagnostics are fetched on demand and never saved in browser storage. */
let logsBefore=0,logsNext=null,logsBusy=false,logsGeneration=0,logsQueued=false;
function clearLogs(){logsGeneration++;logsBefore=0;logsNext=null;$('logs-entries').replaceChildren();$('logs-feedback').textContent='';$('logs-export').removeAttribute('href');}
function logsQuery(download=false){const params=new URLSearchParams();for(const key of ['level','source','q']){const value=$('logs-'+key).value;if(value)params.set(key,value);}if(logsBefore)params.set('before',logsBefore);if(download)params.set('download','1');return params.toString();}
async function loadLogs(){
 if(!accessSession?.enabled||accessSession.user?.role!=='admin')return;
 if(logsBusy){logsQueued=true;return;}
 logsBusy=true;const generation=logsGeneration;$('logs-refresh').disabled=true;
 try{
  const response=await apiFetch('api/logs?'+logsQuery());const result=await response.json();if(!response.ok)throw Error(result.error);
  if(generation!==logsGeneration||!accessSession?.enabled||accessSession.user?.role!=='admin')return;
  const source=$('logs-source').value;$('logs-source').replaceChildren();const any=document.createElement('option');any.value='';any.textContent='Alle bronnen';$('logs-source').append(any);
  for(const name of result.sources){const option=document.createElement('option');option.value=name;option.textContent=name;$('logs-source').append(option);}if(result.sources.includes(source))$('logs-source').value=source;
  $('logs-entries').replaceChildren();for(const entry of result.entries){const row=document.createElement('tr');row.className='log-'+entry.level.toLowerCase();for(const value of [new Date(entry.created_at).toLocaleString('nl-NL'),entry.level,entry.source,entry.message,entry.reference])cell(row,value);const last=cell(row,'');const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent=entry.event+' · details';const pre=document.createElement('pre');pre.textContent=JSON.stringify(entry.details,null,2);details.append(summary,pre);last.append(details);$('logs-entries').append(row);}
  logsNext=result.next_before;$('logs-older').disabled=!logsNext;$('logs-newest').disabled=!logsBefore;$('logs-export').href='api/logs?'+logsQuery(true);
  $('logs-feedback').textContent=result.entries.length?result.entries.length+(result.entries.length===1?' regel':' regels')+' · nieuw naar oud · bijgewerkt '+new Date().toLocaleTimeString('nl-NL'):'Geen logs voor deze filters. Voer de mislukte actie opnieuw uit.';
 }finally{logsBusy=false;$('logs-refresh').disabled=false;if(logsQueued){logsQueued=false;await loadLogs();}}
}
function bindLogs(){
 const refresh=()=>loadLogs().catch(error=>{$('logs-feedback').textContent=error.message;});
 $('logs-refresh').addEventListener('click',refresh);
 for(const id of ['logs-level','logs-source','logs-q'])$(id).addEventListener('change',()=>{logsBefore=0;refresh();});
 $('logs-older').addEventListener('click',()=>{if(logsNext){logsBefore=logsNext;refresh();}});
 $('logs-newest').addEventListener('click',()=>{logsBefore=0;refresh();});
}
