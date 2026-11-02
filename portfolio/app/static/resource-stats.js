/* Monitoring runs only while this admin page is visible. */
let resourceTimer=null,resourceBusy=false;
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
  const cards=$('resource-cards'),disk=$('resource-storage');cards.replaceChildren();disk.replaceChildren();
  const number=value=>new Intl.NumberFormat(appLocale(),{maximumFractionDigits:1}).format(value);
  resourceCard(cards,ui('Werkgeheugen app'),resourceBytes(data.process.memory_bytes));
  resourceCard(cards,ui('CPU app'),data.process.cpu_percent===null?ui('Volgende meting afwachten'):number(data.process.cpu_percent)+'%',ui('Actieve threads')+': '+number(data.process.threads));
  resourceCard(cards,ui('Werkgeheugen container'),resourceBytes(data.container.bytes),ui('Geheugenlimiet')+': '+resourceBytes(data.container.limit_bytes));
  resourceCard(cards,ui('Overzichtcache in geheugen'),resourceBytes(data.cache.bytes),ui('Cachelimiet')+': '+resourceBytes(data.cache.budget_bytes));
  for(const [key,label] of [['database_bytes',ui('Databasebestand')],['journal_bytes',ui('Databaselog')],['backup_bytes',ui('Back-ups')],['other_bytes',ui('Overige bestanden')],['cache_payload_bytes',ui('Tijdelijke gegevens in database')],['reusable_bytes',ui('Herbruikbare databaseruimte')],['volume_free_bytes',ui('Vrij op opslagvolume')],['total_bytes',ui('Totale gegevensopslag')]])resourceCard(disk,label,resourceBytes(data.storage[key]));
  $('resource-rows').textContent=ui('Aantallen')+': '+[[ui('Transacties'),data.storage.rows.purchases],[ui('Dagkoersen'),data.storage.rows.daily_prices],[ui('Koerswaarnemingen'),data.storage.rows.quotes],[ui('Dividend'),data.storage.rows.dividends]].map(([label,value])=>label+' '+number(value)).join(' · ');
  $('resource-status').textContent=ui('Bijgewerkt')+': '+new Date(data.sampled_at*1000).toLocaleTimeString(appLocale())+' · '+ui('Actief sinds')+' '+number(data.process.uptime_seconds/3600)+' '+ui('uur');
 }catch(error){if(location.hash==='#instellingen-statistieken')$('resource-status').textContent=error.message;}
 finally{resourceBusy=false;if(location.hash==='#instellingen-statistieken'&&!document.hidden)resourceTimer=setTimeout(loadResourceStats,15000);}
}
$('resource-refresh').addEventListener('click',loadResourceStats);
window.addEventListener('hashchange',()=>{clearTimeout(resourceTimer);});
document.addEventListener('visibilitychange',()=>{clearTimeout(resourceTimer);if(!document.hidden)loadResourceStats();});
