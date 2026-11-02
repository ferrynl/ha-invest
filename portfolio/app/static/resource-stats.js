/* Monitoring runs only while this admin page is visible. */
let resourceTimer=null,resourceBusy=false,resourceSnapshot=null;
function resourceBytes(value){
 if(value===null||value===undefined)return ui('Niet beschikbaar');
 const units=['B','KiB','MiB','GiB','TiB'];let i=0;while(value>=1024&&i<units.length-1){value/=1024;i++;}
 return new Intl.NumberFormat(appLocale(),{maximumFractionDigits:1}).format(value)+' '+units[i];
}
function resourceCard(target,title,value,note=''){
 const card=homeNode('article');card.className='resource-card';card.append(homeNode('span',title),homeNode('strong',value));if(note)card.append(homeNode('small',note));target.append(card);
}
async function loadResourceStats(){
 clearTimeout(resourceTimer);
 if(resourceBusy||document.hidden||location.hash!=='#instellingen-statistieken'||accessSession?.user?.role!=='admin')return;
 resourceBusy=true;
 try{
  const response=await apiFetch('api/resource-stats',{background:true});if(!response.ok)throw Error(ui('Statistieken laden mislukt.'));
  const data=await response.json();if(location.hash!=='#instellingen-statistieken'||accessSession?.user?.role!=='admin')return;
  resourceSnapshot={app_version:data.diagnostics?.app_version??state?.app_version,...data};$('resource-download').disabled=false;
  const cards=$('resource-cards'),disk=$('resource-storage');cards.replaceChildren();disk.replaceChildren();
  const number=value=>new Intl.NumberFormat(appLocale(),{maximumFractionDigits:1}).format(value);
  resourceCard(cards,ui('Werkgeheugen app'),resourceBytes(data.process.memory_bytes));
  resourceCard(cards,ui('CPU app'),data.process.cpu_percent===null?ui('Volgende meting afwachten'):number(data.process.cpu_percent)+'%',ui('Actieve threads')+': '+number(data.process.threads));
  resourceCard(cards,ui('Werkgeheugen container'),resourceBytes(data.container.bytes),ui('Geheugenlimiet')+': '+resourceBytes(data.container.limit_bytes));
  resourceCard(cards,ui('Overzichtcache in geheugen'),resourceBytes(data.cache.bytes),ui('Cachelimiet')+': '+resourceBytes(data.cache.budget_bytes));
  for(const [key,label] of [['database_bytes',ui('Databasebestand')],['journal_bytes',ui('Databaselog')],['backup_bytes',ui('Back-ups')],['other_bytes',ui('Overige bestanden')],['cache_payload_bytes',ui('Tijdelijke gegevens in database')],['reusable_bytes',ui('Herbruikbare databaseruimte')],['volume_free_bytes',ui('Vrij op opslagvolume')],['total_bytes',ui('Totale gegevensopslag')]])resourceCard(disk,label,resourceBytes(data.storage[key]));
  const details=$('resource-diagnostics');details.replaceChildren();
  for(const issue of data.storage.date_issues||[]){const card=homeNode('article',ui('Verdachte transactiedatum')+': '+issue.day+' · '+ui('Aantal')+': '+number(issue.count));card.className='resource-card';const link=homeNode('a',ui('Betrokken transacties controleren'));link.href='#transacties?datum='+encodeURIComponent(issue.day);card.append(document.createElement('br'),link);details.append(card);}
  const day=value=>value?new Date(value.slice(0,10)+'T00:00:00Z').toLocaleDateString(appLocale(),{timeZone:'UTC'}):ui('Niet beschikbaar');
  for(const [label,value] of [[ui('Piekgeheugen app'),resourceBytes(data.process.peak_bytes)],[ui('Anoniem werkgeheugen'),resourceBytes(data.process.anonymous_bytes)],[ui('Bestandsgeheugen'),resourceBytes(data.process.file_bytes)],[ui('Wisselgeheugen'),resourceBytes(data.process.swap_bytes)],[ui('Posities per broker'),number(data.storage.listing_count)],[ui('Dagwaarden bij volledige historie'),number(data.storage.estimated_daily_points)],[ui('Oudste aankoop'),day(data.storage.history_start)],[ui('Oudste koerswaarneming'),day(data.storage.quote_start)]])resourceCard(details,label,value);
  const names={'state-compact':ui('Compact overzicht'),'state':ui('Volledig overzicht'),'home-euro-chart':ui('EUR-grafiek'),'home-euro-compact':ui('EUR-totalen'),'performance':ui('Rendementsrapport'),'dividend':ui('Dividend'),'dividend-euro':ui('Dividend'),'reports-combined':ui('EUR-rapport'),'reports-history':ui('Rapporthistorie')};
  const tasks={daily:ui('Dagwaarden berekenen'),state:ui('Overzicht opbouwen'),history:ui('Positiehistorie lezen'),report:ui('Rapport berekenen'),quotes:ui('Koersen ophalen'),prices:ui('Koershistorie ophalen'),profile:ui('Bedrijfsprofiel ophalen'),funds:ui('ETF-gegevens ophalen'),backup:ui('Back-up maken')};
  $('resource-work').textContent=ui('Lopende berekeningen')+': '+([...(data.cache.active||[]).map(row=>(names[row.view]||ui('Overige berekening'))+' ('+number(row.seconds)+' s)'),...Object.entries(data.diagnostics?.workers||{}).map(([task,count])=>(tasks[task]||ui('Overige berekening'))+' × '+number(count))].join(' · ')||ui('Geen zware berekening actief'));
  const builds=$('resource-builds');builds.replaceChildren();
  for(const row of data.cache.measurements||[])builds.append(homeNode('p',(names[row.view]||ui('Overige berekening'))+' · '+ui('Opgebouwd')+': '+number(row.builds)+' · '+ui('Laatste duur')+': '+number(row.last_seconds)+' s · '+ui('Langste duur')+': '+number(row.max_seconds)+' s · '+ui('Boven cachelimiet')+': '+number(row.oversized)));
  $('resource-rows').textContent=ui('Aantallen')+': '+[[ui('Transacties'),data.storage.rows.purchases],[ui('Dagkoersen'),data.storage.rows.daily_prices],[ui('Koerswaarnemingen'),data.storage.rows.quotes],[ui('Dividend'),data.storage.rows.dividends]].map(([label,value])=>label+' '+number(value)).join(' · ');
  $('resource-status').textContent=ui('Bijgewerkt')+': '+new Date(data.sampled_at*1000).toLocaleTimeString(appLocale())+' · '+ui('Actief sinds')+' '+number(data.process.uptime_seconds/3600)+' '+ui('uur');
 }catch(error){if(location.hash==='#instellingen-statistieken')$('resource-status').textContent=error.message;}
 finally{resourceBusy=false;if(location.hash==='#instellingen-statistieken'&&!document.hidden)resourceTimer=setTimeout(loadResourceStats,15000);}
}
$('resource-refresh').addEventListener('click',loadResourceStats);
window.addEventListener('hashchange',()=>{clearTimeout(resourceTimer);});
document.addEventListener('visibilitychange',()=>{clearTimeout(resourceTimer);if(!document.hidden)loadResourceStats();});

$('resource-download').addEventListener('click',()=>{
 if(!resourceSnapshot||accessSession?.user?.role!=='admin')return;
 const url=URL.createObjectURL(new Blob([JSON.stringify(resourceSnapshot,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='home-invest-diagnose.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
