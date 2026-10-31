/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
// Subpages share existing editors and account controls.
const settingsSections=['tmx-omboeken','verwijderen','brokers','versie','beveiliging','gebruikers','dashboard','sensoren','opslag','backups'];
const settingsRoot=document.querySelector('[data-page="instellingen"]');
const settingsNav=document.createElement('div');settingsNav.id='settings-types';settingsNav.className='report-sidebar';
document.querySelector('[data-route="instellingen"]').after(settingsNav);
for(const [index,panel] of [...settingsRoot.children].entries()){
 const route=index===0?'tmx-omboeken':'instellingen-'+settingsSections[index];
 const title=panel.querySelector('h2').textContent;
 const link=document.createElement('a');link.href='#'+route;link.dataset.route=route;link.textContent=title;settingsNav.append(link);
 if(index===0){panel.remove();continue;}
 const view=document.createElement('div');view.dataset.page=route;view.hidden=true;panel.before(view);view.append(panel);settingsRoot.after(view);
}
settingsNav.prepend(settingsNav.querySelector('[data-route="instellingen-dashboard"]'));
for(const route of ['valuta','logs']){const link=document.querySelector('[data-route="'+route+'"]');link.querySelector('span')?.remove();settingsNav.append(link);}
const exportView=document.createElement('div');exportView.dataset.page='import-export';exportView.hidden=true;
const exportPanel=document.createElement('section');exportPanel.className='panel';exportView.append(exportPanel);
const exportNote=document.createElement('p');exportNote.textContent=ui('Exporteer transacties, dividend en kapitaalterugbetalingen van je eigen portefeuille. Kies bovenaan een brokeraccount of alle accounts. Alleen voor ingelogde admins.');exportPanel.append(exportNote);
const exportTitle=document.createElement('h2');exportTitle.textContent=ui('Exporteren');exportPanel.append(exportTitle);
for(const format of ['csv','pdf']){const a=document.createElement('a');a.className='button';a.href='api/export?format='+format;a.textContent=format.toUpperCase();exportPanel.append(a);}
settingsRoot.after(exportView);
const exportLink=document.createElement('a');exportLink.href='#import-export';exportLink.dataset.route='import-export';exportLink.textContent=ui('Exporteren');

const importNav=document.createElement('div');importNav.id='import-types';importNav.className='report-sidebar';
document.querySelector('[data-route="imports"]').after(importNav);
for(const [route,title] of [['import-trading212','Trading 212'],['import-traderepublic','Trade Republic'],['import-revolut',ui('Revolut')],['import-api',ui('API-instellingen')],['import-koppelingen',ui('Aandelenkoppelingen')],['import-beoordeling',ui('Te beoordelen')]]){
 const a=document.createElement('a');a.href='#'+route;a.dataset.route=route;a.textContent=title;importNav.append(a);
}
importNav.append(exportLink);
const transactionNav=document.createElement('div');transactionNav.id='transaction-types';transactionNav.className='report-sidebar';
document.querySelector('[data-route="transacties"]').after(transactionNav);
for(const [route,title] of [['transacties-dividend',ui('Dividend')],['transacties-omzettingen',ui('Splitsingen en omzettingen')]]){
 const link=document.createElement('a');link.href='#'+route;link.dataset.route=route;link.textContent=title;transactionNav.append(link);
}
const pageNames={'tmx-omboeken':ui('TMX omboeken naar TDT'),account:ui('Mijn account'),'import-api':ui('API-instellingen'),aandeel:ui('Aandeel'),transacties:ui('Transacties'),'import-beoordeling':ui('Te beoordelen'),'import-koppelingen':ui('Aandelenkoppelingen'),home:ui('Home'),aandelen:ui('Aandelen'),dividend:ui('Dividend'),rapporten:ui('Rapporten'),instellingen:ui('Instellingen'),imports:ui('Imports'),logs:ui('Logs'),valuta:ui('Valuta')};
for(const a of [...settingsNav.querySelectorAll('a'),...importNav.querySelectorAll('a'),...transactionNav.querySelectorAll('a')])pageNames[a.dataset.route]=a.textContent;
for(const [key,title] of reportDefinitions)pageNames['rapporten-'+key]=title;
function closeMenu(){document.body.removeAttribute('data-menu-open');$('sidebar').inert=window.matchMedia('(max-width:850px)').matches&&!document.body.classList.contains('locked');$('nav-overlay').hidden=true;$('menu-toggle').setAttribute('aria-expanded','false');$('menu-toggle').setAttribute('aria-label',ui('Menu openen'));}
function showPage(){
 closeAllPopups();
 let requested=location.hash.slice(1).split('?')[0];if(requested==='instellingen-export')requested='import-export';if(requested==='instellingen')requested='instellingen-dashboard';let page=Object.hasOwn(pageNames,requested)?requested:'home';
 if((page.startsWith('instellingen-')||page.startsWith('import-')||page==='tmx-omboeken'||page==='instellingen'||page==='imports'||page==='import-koppelingen'||page==='import-beoordeling'||page==='import-api')&&accessSession?.user?.role!=='admin')page='home';
 if(page==='logs'&&(accessSession?.user?.role!=='admin'||!accessSession?.enabled))page='home';
 const isSettings=page.startsWith('instellingen-')||page==='logs'||page==='valuta'||page==='tmx-omboeken';settingsNav.hidden=!isSettings;document.querySelector('[data-route=instellingen]').setAttribute('aria-expanded',String(isSettings));
 const isTransactions=page==='transacties'||page.startsWith('transacties-');transactionNav.hidden=!isTransactions;document.querySelector('[data-route=transacties]').setAttribute('aria-expanded',String(isTransactions));
 const brokerPage=page.match(/^import-(trading212|traderepublic|revolut)$/);importNav.hidden=!(page==='imports'||page.startsWith('import-'));document.querySelector('[data-route=imports]').setAttribute('aria-expanded',String(!importNav.hidden));
 document.body.classList.toggle('broker-import-page',!!brokerPage);$('import-provider').disabled=!!brokerPage;
 if(brokerPage){$('import-provider').value=brokerPage[1];refreshImportAccounts();}
 for(const card of document.querySelectorAll('.import-providers > section'))card.hidden=!!brokerPage&&!card.querySelector('[data-import-provider="'+brokerPage[1]+'"]');
 const isReport=page==='rapporten'||page.startsWith('rapporten-');
 if(isReport){reportType=page==='rapporten'?'portfolio':page.slice(10);renderReportNavigation();}
 $('report-types').hidden=!isReport;document.querySelector('[data-route=rapporten]').setAttribute('aria-expanded',String(isReport));
 for(const view of document.querySelectorAll('[data-page]'))view.hidden=view.dataset.page!==(isReport?'rapporten':brokerPage?'imports':isTransactions?'transacties':page);
 for(const link of document.querySelectorAll('[data-route]')){if(link.dataset.route===page||(isReport&&link.dataset.route==='rapporten')||(isTransactions&&link.dataset.route==='transacties')||(isSettings&&link.dataset.route==='instellingen')||(brokerPage&&link.dataset.route==='imports')||(page==='aandeel'&&link.dataset.route==='aandelen')||(page.startsWith('import-')&&link.dataset.route==='imports'))link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 for(const link of document.querySelectorAll('.import-nav a')){if(link.hash==='#'+page)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 document.body.classList.toggle('home-page',page==='home');
 document.body.classList.toggle('reports-page',isReport);
 document.body.classList.toggle('countries-page',page==='rapporten-countries');
 document.body.classList.toggle('dividend-page',page==='dividend');
 document.body.classList.toggle('stocks-page',page==='aandelen'||page==='aandeel');
 document.body.classList.toggle('stocks-list-page',page==='aandelen');
 const brokerSlot={home:'home-broker-slot',aandelen:'stocks-broker-slot',dividend:'dividend-broker-slot',rapporten:'reports-broker-slot'}[isReport?'rapporten':page];
 $(brokerSlot||'page-header').append($('broker-filter-control'));
 $('broker-filter-control').hidden=page==='account';
 updateExportLinks();
 $('page-title').textContent=pageNames[page];document.title=pageNames[page]+' · Home Invest';closeMenu();
 if(isTransactions){configureTransactionPage(page);if(state)loadTransactions();}
 if(page==='aandelen'&&state)renderStockPage();
 if(page==='aandeel'&&state)loadStockDetail();
 if(page==='dividend'&&state)renderDividendPage();
 if(page==='home'&&state){renderHomeDashboard();requestAnimationFrame(draw);}
 if(isReport&&state)renderReports();
 if((page==='imports'||brokerPage)&&state&&accessSession?.user?.role==='admin')loadImportHistory().catch(error=>{$('import-feedback').textContent=error.message;});
 if(page==='logs')loadLogs().catch(error=>{$('logs-feedback').textContent=error.message;});
 if(page==='import-koppelingen')loadImportMappings();
 if(page==='import-beoordeling')loadImportIssues();
 if(page==='valuta')loadCurrencies();
 if(page==='instellingen-sensoren'&&state)loadHomeAssistant();
 if(page==='tmx-omboeken')loadConversions();
 window.scrollTo(0,0);
}
window.addEventListener('hashchange',showPage);
$('menu-toggle').addEventListener('click',()=>{if(document.body.hasAttribute('data-menu-open'))closeMenu();else{document.body.setAttribute('data-menu-open','');$('sidebar').inert=false;$('nav-overlay').hidden=false;$('menu-toggle').setAttribute('aria-expanded','true');$('menu-toggle').setAttribute('aria-label',ui('Menu sluiten'));}});
window.matchMedia('(max-width:850px)').addEventListener('change',closeMenu);
document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();$('main-content').focus();});
$('nav-overlay').addEventListener('click',closeMenu);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.body.hasAttribute('data-menu-open')){closeMenu();$('menu-toggle').focus();}});
document.querySelectorAll('[data-route]').forEach(link=>link.addEventListener('click',closeMenu));
function updateExportLinks(){for(const a of exportPanel.querySelectorAll('a')){const url=new URL(a.href);url.searchParams.set('account_id',currentBroker);a.href=url.href;}}
function renderPages(){
 updateExportLinks();
 $('sidebar-version').textContent=ui('Versie ')+state.app_version;
 $('settings-version').textContent=state.app_version;$('settings-database').textContent=state.database_version;$('settings-interval').textContent=state.refresh_minutes+ui(' minuten');
 if(!settingsDirty)$('settings-form').elements.namedItem('default_range').value=state.settings.default_range;
 const selected=$('report-year').value,years=[...new Set([...Array.from({length:6},(_,i)=>String(new Date().getFullYear()+i)),...state.dividends.filter(d=>reportDate(d.paid_on)).map(d=>d.paid_on.slice(0,4))])].sort().reverse();
 $('report-year').replaceChildren();for(const year of years){const option=document.createElement('option');option.value=year;option.textContent=year;$('report-year').append(option);}$('report-year').value=years.includes(selected)?selected:String(new Date().getFullYear());
 if(location.hash.startsWith('#rapporten'))renderReports();
 if(location.hash==='#instellingen')loadHomeAssistant();
 if(location.hash==='#tmx-omboeken')loadConversions();
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
bindTransactions();bindHomeDashboard();bindImportIssues();bindImportMappings();bindImports();bindAccess();bindLogs();bindCurrencies();startSession().catch(()=>{$('status').textContent=ui('Verbinding mislukt. Herlaad de pagina.');document.body.classList.remove('booting');refreshPageLoading();});
setInterval(()=>{if(!document.hidden&&accessSession?.user)load();},120000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&accessSession?.user)load();});
