/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
const pageNames={account:ui('Mijn account'),'import-api':ui('API-instellingen'),aandeel:ui('Aandeel'),transacties:ui('Transacties'),'import-beoordeling':ui('Te beoordelen'),'import-koppelingen':ui('Aandelenkoppelingen'),home:ui('Home'),aandelen:ui('Aandelen'),dividend:ui('Dividend'),rapporten:ui('Rapporten'),instellingen:ui('Instellingen'),imports:ui('Imports'),logs:ui('Logs'),valuta:ui('Valuta')};
function closeMenu(){document.body.removeAttribute('data-menu-open');$('sidebar').inert=window.matchMedia('(max-width:850px)').matches&&!document.body.classList.contains('locked');$('nav-overlay').hidden=true;$('menu-toggle').setAttribute('aria-expanded','false');$('menu-toggle').setAttribute('aria-label',ui('Menu openen'));}
function showPage(){
 closeAllPopups();
 const requested=location.hash.slice(1).split('?')[0];let page=Object.hasOwn(pageNames,requested)?requested:'home';
 if((page==='instellingen'||page==='imports'||page==='import-koppelingen'||page==='import-beoordeling'||page==='import-api')&&accessSession?.user?.role!=='admin')page='home';
 if(page==='logs'&&(accessSession?.user?.role!=='admin'||!accessSession?.enabled))page='home';
 for(const view of document.querySelectorAll('[data-page]'))view.hidden=view.dataset.page!==page;
 for(const link of document.querySelectorAll('[data-route]')){if(link.dataset.route===page||(page==='aandeel'&&link.dataset.route==='aandelen')||((page==='import-koppelingen'||page==='import-beoordeling'||page==='import-api')&&link.dataset.route==='imports'))link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 for(const link of document.querySelectorAll('.import-nav a')){if(link.hash==='#'+page)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 document.body.classList.toggle('home-page',page==='home');
 document.body.classList.toggle('dividend-page',page==='dividend');
 document.body.classList.toggle('stocks-page',page==='aandelen'||page==='aandeel');
 document.body.classList.toggle('stocks-list-page',page==='aandelen');
 const brokerSlot={home:'home-broker-slot',aandelen:'stocks-broker-slot',dividend:'dividend-broker-slot'}[page];
 $(brokerSlot||'page-header').append($('broker-filter-control'));
 $('broker-filter-control').hidden=page==='account';
 $('page-title').textContent=pageNames[page];document.title=pageNames[page]+' · Home Invest';closeMenu();
 if(page==='transacties'&&state)loadTransactions();
 if(page==='aandelen'&&state)renderStockPage();
 if(page==='aandeel'&&state)loadStockDetail();
 if(page==='dividend'&&state)renderDividendPage();
 if(page==='home'&&state){renderHomeDashboard();requestAnimationFrame(draw);}
 if(page==='rapporten'&&state)renderReports();
 if(page==='imports'&&state&&accessSession?.user?.role==='admin')loadImportHistory().catch(error=>{$('import-feedback').textContent=error.message;});
 if(page==='logs')loadLogs().catch(error=>{$('logs-feedback').textContent=error.message;});
 if(page==='import-koppelingen')loadImportMappings();
 if(page==='import-beoordeling')loadImportIssues();
 if(page==='valuta')loadCurrencies();
 if(page==='instellingen'&&state)loadHomeAssistant();
 window.scrollTo(0,0);
}
window.addEventListener('hashchange',showPage);
$('menu-toggle').addEventListener('click',()=>{if(document.body.hasAttribute('data-menu-open'))closeMenu();else{document.body.setAttribute('data-menu-open','');$('sidebar').inert=false;$('nav-overlay').hidden=false;$('menu-toggle').setAttribute('aria-expanded','true');$('menu-toggle').setAttribute('aria-label',ui('Menu sluiten'));}});
window.matchMedia('(max-width:850px)').addEventListener('change',closeMenu);
document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();$('main-content').focus();});
$('nav-overlay').addEventListener('click',closeMenu);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.body.hasAttribute('data-menu-open')){closeMenu();$('menu-toggle').focus();}});
document.querySelectorAll('[data-route]').forEach(link=>link.addEventListener('click',closeMenu));
function renderPages(){
 $('sidebar-version').textContent=ui('Versie ')+state.app_version;
 $('settings-version').textContent=state.app_version;$('settings-database').textContent=state.database_version;$('settings-interval').textContent=state.refresh_minutes+ui(' minuten');
 if(!settingsDirty)$('settings-form').elements.namedItem('default_range').value=state.settings.default_range;
 const selected=$('report-year').value,years=[...new Set([String(new Date().getFullYear()),...state.dividends.filter(d=>reportDate(d.paid_on)).map(d=>d.paid_on.slice(0,4))])].sort().reverse();
 $('report-year').replaceChildren();for(const year of years){const option=document.createElement('option');option.value=year;option.textContent=year;$('report-year').append(option);}if(years.includes(selected))$('report-year').value=selected;
 if(location.hash==='#rapporten')renderReports();
 if(location.hash==='#instellingen')loadHomeAssistant();
}
async function loadHomeAssistant(){
 const request=stateRequest;
 try{
  const response=await apiFetch('api/home-assistant');if(!response.ok)throw Error(ui('Home Assistant-koppeling laden mislukt.'));
  const data=await response.json();if(request!==stateRequest||accessSession?.user?.role!=='admin')return;
  $('ha-export-status').textContent=data.enabled?ui('Toegangssleutel ingesteld. Controleer ook de netwerkpoort in de app-configuratie.'):ui('Nog niet ingeschakeld. Stel de toegangssleutel en netwerkpoort hieronder in.');
  const summary=data.summary,values=Object.entries(summary.currencies).map(([currency,item])=>currency+': '+(item.complete?money(item.value,currency):ui('onvolledig')));
  values.push(ui('Totaal in euro: ')+(summary.total_eur.complete?money(summary.total_eur.value,'EUR'):ui('onvolledig; ontbrekende koersen of wisselkoersen')));
  $('ha-export-values').textContent=values.join(' · ');$('ha-export-yaml').textContent=data.configuration;
 }catch(error){if(request===stateRequest)$('ha-export-status').textContent=error.message;}
}
let settingsDirty=false;
$('settings-form').addEventListener('input',()=>{settingsDirty=true;});
$('report-year').addEventListener('change',renderReports);
$('settings-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const response=await apiFetch('api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))});if(!response.ok)throw Error(ui('Instellingen opslaan mislukt.'));settingsDirty=false;chartRange=event.target.elements.namedItem('default_range').value;syncRangeButtons();await load();$('settings-feedback').textContent=ui('Instellingen opgeslagen.');}catch(error){$('settings-feedback').textContent=error.message;}finally{button.disabled=false;}});
bindPopups();showPage();
bindTransactions();bindHomeDashboard();bindImportIssues();bindImportMappings();bindImports();bindAccess();bindLogs();bindCurrencies();startSession().catch(()=>{$('status').textContent=ui('Verbinding mislukt. Herlaad de pagina.');document.body.classList.remove('booting');});
setInterval(()=>{if(!document.hidden&&accessSession?.user)load();},120000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&accessSession?.user)load();});
