const pageNames={transacties:'Transacties','import-beoordeling':'Te beoordelen','import-koppelingen':'Aandelenkoppelingen',home:'Home',aandelen:'Aandelen',dividend:'Dividend',rapporten:'Rapporten',instellingen:'Instellingen',imports:'Imports',logs:'Logs',valuta:'Valuta'};
function closeMenu(){document.body.removeAttribute('data-menu-open');$('sidebar').inert=window.matchMedia('(max-width:850px)').matches&&!document.body.classList.contains('locked');$('nav-overlay').hidden=true;$('menu-toggle').setAttribute('aria-expanded','false');$('menu-toggle').setAttribute('aria-label','Menu openen');}
function showPage(){
 closeAllPopups();
 const requested=location.hash.slice(1);let page=Object.hasOwn(pageNames,requested)?requested:'home';
 if((page==='instellingen'||page==='imports'||page==='import-koppelingen'||page==='import-beoordeling')&&accessSession?.user?.role!=='admin')page='home';
 if(page==='logs'&&(accessSession?.user?.role!=='admin'||!accessSession?.enabled))page='home';
 for(const view of document.querySelectorAll('[data-page]'))view.hidden=view.dataset.page!==page;
 for(const link of document.querySelectorAll('[data-route]')){if(link.dataset.route===page||((page==='import-koppelingen'||page==='import-beoordeling')&&link.dataset.route==='imports'))link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 document.body.classList.toggle('home-page',page==='home');
 $('page-title').textContent=pageNames[page];document.title=pageNames[page]+' · Home Invest';closeMenu();
 if(page==='transacties'&&state)loadTransactions();
 if(page==='aandelen'&&state)renderStockPage();
 if(page==='dividend'&&state)renderDividendPage();
 if(page==='home'&&state)requestAnimationFrame(draw);
 if(page==='imports'&&state&&accessSession?.user?.role==='admin')loadImportHistory().catch(error=>{$('import-feedback').textContent=error.message;});
 if(page==='logs')loadLogs().catch(error=>{$('logs-feedback').textContent=error.message;});
 if(page==='import-koppelingen')loadImportMappings();
 if(page==='import-beoordeling')loadImportIssues();
 if(page==='valuta')loadCurrencies();
 window.scrollTo(0,0);
}
window.addEventListener('hashchange',showPage);
$('menu-toggle').addEventListener('click',()=>{if(document.body.hasAttribute('data-menu-open'))closeMenu();else{document.body.setAttribute('data-menu-open','');$('sidebar').inert=false;$('nav-overlay').hidden=false;$('menu-toggle').setAttribute('aria-expanded','true');$('menu-toggle').setAttribute('aria-label','Menu sluiten');}});
window.matchMedia('(max-width:850px)').addEventListener('change',closeMenu);
document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();$('main-content').focus();});
$('nav-overlay').addEventListener('click',closeMenu);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.body.hasAttribute('data-menu-open')){closeMenu();$('menu-toggle').focus();}});
document.querySelectorAll('[data-route]').forEach(link=>link.addEventListener('click',closeMenu));
function renderPages(){
 $('sidebar-version').textContent='Versie '+state.app_version;
 $('settings-version').textContent=state.app_version;$('settings-database').textContent=state.database_version;$('settings-interval').textContent=state.refresh_minutes+' minuten';
 if(!settingsDirty)$('settings-form').elements.namedItem('default_range').value=state.settings.default_range;
 const selected=$('report-year').value,years=[...new Set([String(new Date().getFullYear()),...state.dividends.map(d=>d.paid_on.slice(0,4))])].sort().reverse();
 $('report-year').replaceChildren();for(const year of years){const option=document.createElement('option');option.value=year;option.textContent=year;$('report-year').append(option);}if(years.includes(selected))$('report-year').value=selected;
 renderReports();
}
function renderReports(){
 if(!state)return;const groups={};const year=$('report-year').value;
 for(const d of state.dividends){if(d.paid_on.slice(0,4)!==year)continue;const key=d.paid_on.slice(0,7)+'|'+d.currency;const item=groups[key]??={month:d.paid_on.slice(0,7),currency:d.currency,count:0,amount:0};item.count++;item.amount+=Number(d.amount);}
 $('report-dividends').replaceChildren();for(const key of Object.keys(groups).sort()){const item=groups[key],row=document.createElement('tr');for(const value of [new Date(item.month+'-01T00:00:00Z').toLocaleDateString('nl-NL',{month:'long',year:'numeric',timeZone:'UTC'}),item.currency,item.count,money(item.amount,item.currency)])cell(row,value);$('report-dividends').append(row);}
 $('report-empty').textContent=Object.keys(groups).length?'':'Geen dividend geboekt in '+year+'.';
 const totals={};for(const p of state.positions){const t=totals[p.currency]??={cost:0,value:0,dividend:0,realised:0,count:0,complete:true};t.cost+=Number(p.cost);t.dividend+=Number(p.dividend);t.realised+=Number(p.realised??0);t.count++;if(p.value===null)t.complete=false;else t.value+=Number(p.value);}
 $('report-portfolio').replaceChildren();for(const [currency,t] of Object.entries(totals)){const row=document.createElement('tr');for(const value of [currency,t.count,money(t.cost,currency),t.complete?money(t.value,currency):'Onvolledig',t.complete?money(t.value-t.cost+t.realised,currency):'Onbekend',money(t.dividend,currency),t.complete?money(t.value-t.cost+t.realised+t.dividend,currency):'Onbekend'])cell(row,value);$('report-portfolio').append(row);}
}
let settingsDirty=false;
$('settings-form').addEventListener('input',()=>{settingsDirty=true;});
$('report-year').addEventListener('change',renderReports);
$('settings-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const response=await apiFetch('api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))});if(!response.ok)throw Error('Instellingen opslaan mislukt.');settingsDirty=false;chartRange=event.target.elements.namedItem('default_range').value;syncRangeButtons();await load();$('settings-feedback').textContent='Instellingen opgeslagen.';}catch(error){$('settings-feedback').textContent=error.message;}finally{button.disabled=false;}});
bindPopups();showPage();
bindTransactions();bindHomeDashboard();bindImportIssues();bindImportMappings();bindImports();bindAccess();bindLogs();bindCurrencies();startSession().catch(()=>{$('status').textContent='Verbinding mislukt. Herlaad de pagina.';document.body.classList.remove('booting');});
setInterval(()=>{if(!document.hidden&&accessSession?.user)load();},120000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&accessSession?.user)load();});
