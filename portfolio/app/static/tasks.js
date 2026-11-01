/* The task is server-owned. Reading progress never starts provider requests. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let etfTaskTimer=null,etfTaskGeneration=0,etfTaskWasRunning=false;
function clearETFTasks(){etfTaskGeneration++;clearTimeout(etfTaskTimer);etfTaskTimer=null;etfTaskWasRunning=false;$('etf-task-rows').replaceChildren();$('etf-task-feedback').textContent='';$('etf-task-summary').textContent='';$('etf-task-form').reset();closePopup('etf-task-editor');}
function etfTaskSummary(rows){return {total:rows.length,done:rows.filter(r=>!['ready','queued','running'].includes(r.status)).length,success:rows.filter(r=>['success','partial'].includes(r.status)).length,failed:rows.filter(r=>['error','unsupported','interrupted'].includes(r.status)).length};}
function renderETFTasks(data){
 const labels={ready:ui('Nog niet gestart'),queued:ui('In wachtrij'),running:ui('Bezig met ophalen'),success:ui('Opgehaald'),partial:ui('Opgehaald met ontbrekende indeling'),waiting:ui('Bronwachttijd'),skipped:ui('Overgeslagen'),unsupported:ui('Bron niet herkend'),error:ui('Mislukt'),interrupted:ui('Onderbroken'),cancelled:ui('Gestopt'),closed:ui('Fonds samengevoegd')};
 const summary=etfTaskSummary(data.rows),number=n=>new Intl.NumberFormat(appLocale()).format(n);$('etf-task-progress').max=Math.max(1,summary.total);$('etf-task-progress').value=data.phase==='ready'?0:summary.done;
 $('etf-task-summary').textContent=number(summary.done)+' / '+number(summary.total)+' · '+ui('Opgehaald')+': '+number(summary.success)+' · '+ui('Mislukt')+': '+number(summary.failed);
 $('etf-task-feedback').textContent=data.phase==='stopping'?ui('Stop aangevraagd. De lopende aanvraag wordt eerst afgerond.'):data.running?ui('ETF-taak wordt op de achtergrond uitgevoerd.'):data.phase==='interrupted'?ui('De vorige taak is onderbroken. Je kunt de taak opnieuw starten.'):data.phase==='complete'?ui('ETF-taak afgerond.'):data.phase==='cancelled'?ui('ETF-taak gestopt.'):ui('Start een taak om ETF-gegevens automatisch op te halen.');
 $('etf-task-open').disabled=!!data.running;$('etf-task-stop').disabled=!data.running||data.phase==='stopping';$('etf-task-rows').replaceChildren();
 for(const item of data.rows){const row=homeNode('tr');row.dataset.status=item.status;const identity=cell(row,''),link=homeNode('a',item.name);link.href=stockDetailLink(item);identity.append(link,homeNode('small',item.symbol+' · '+item.exchange+' · '+item.currency));
  cell(row,({invesco:'Invesco',vaneck:ui('VanEck'),vanguard:'Vanguard',ishares:'iShares'})[item.issuer]||'—');cell(row,labels[item.status]||labels.ready);cell(row,item.as_of?dayLabel(item.as_of):'—');cell(row,number(item.count||0));const detail=cell(row,ui(item.message||'')+(item.log_id?' · Log-ID '+item.log_id:''));if(item.stale)detail.append(homeNode('small',ui('Samenstelling ouder dan 14 dagen')));$('etf-task-rows').append(row);}
 $('etf-task-empty').textContent=data.rows.length?'':ui('Geen ETF-noteringen gevonden. Controleer bij het aandeel of Type belegging op ETF staat.');
}
async function loadETFTasks(){
 clearTimeout(etfTaskTimer);if(accessSession?.user?.role!=='admin'||location.hash!=='#instellingen-taken')return;const generation=++etfTaskGeneration;
 try{const response=await apiFetch('api/tasks/etf');const data=await response.json();if(generation!==etfTaskGeneration||!accessSession?.user||location.hash!=='#instellingen-taken')return;if(!response.ok)throw Error(data.error);renderETFTasks(data);
  const finished=etfTaskWasRunning&&!data.running;etfTaskWasRunning=!!data.running;if(finished){stateETag=null;await load();}if(data.running)etfTaskTimer=setTimeout(loadETFTasks,2000);
 }catch(error){if(generation===etfTaskGeneration&&accessSession?.user)$('etf-task-feedback').textContent=error.message||ui('Taakstatus laden mislukt.');}
}
if(typeof document!=='undefined'){
 $('etf-task-open').addEventListener('click',()=>{$('etf-task-start-feedback').textContent='';openPopup('etf-task-editor');});
 $('etf-task-cancel').addEventListener('click',()=>closePopup('etf-task-editor'));
 $('etf-task-refresh').addEventListener('click',loadETFTasks);
 $('etf-task-stop').addEventListener('click',async()=>{try{await jsonAction('api/tasks/etf',{action:'cancel'});await loadETFTasks();}catch(error){$('etf-task-feedback').textContent=error.message;}});
 $('etf-task-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button[type=submit]');button.disabled=true;try{await jsonAction('api/tasks/etf',{mode:event.target.elements.mode.value});etfTaskWasRunning=true;closePopup('etf-task-editor');await loadETFTasks();}catch(error){$('etf-task-start-feedback').textContent=error.message;}finally{button.disabled=false;}});
}
if(typeof module!=='undefined')module.exports={etfTaskSummary};
