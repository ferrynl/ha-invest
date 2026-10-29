/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let state,stateRequest=0;
const quantityLabel=value=>{const text=String(value??'0');if(Number(text)===0)return '0';const separator=typeof appLocale==='function'&&appLocale()==='en-GB'?'.':',';return text.replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1').replace('.',separator);};
const $ = id => document.getElementById(id);
const money = (n,c) => n === null ? ui('Nog geen koers') : new Intl.NumberFormat((typeof appLocale==='function'?appLocale():'nl-NL'),{style:'currency',currency:c}).format(Number(n));
function cell(row,value){const td=document.createElement('td');td.textContent=value;row.append(td);return td;}
async function load(){
 try{
 const request=++stateRequest;const response=await apiFetch('api/state?account_id='+encodeURIComponent(currentBroker)+'&compact=1');if(response.status===304)return;if(!response.ok)throw Error();const result=await response.json();if(request!==stateRequest||!accessSession?.user)return;state=result;
 $('status').textContent=state.status.message+ui(' Automatische controle elke ')+state.refresh_minutes+ui(' minuten.');
 if(location.hash==='#transacties')loadTransactions();
 if(location.hash==='#aandelen')renderStockPage();
 if(location.hash.startsWith('#aandeel?'))loadStockDetail();
 if(location.hash==='#dividend')renderDividendPage();
 if(!rangeInitialized){chartRange=state.settings.default_range;rangeInitialized=true;syncRangeButtons();}
 renderPages();renderBrokerAccounts();if(document.body.classList.contains('home-page')){renderHomeDashboard();draw();}
 }catch{$('status').textContent=ui('Gegevens laden mislukt. Probeer de pagina opnieuw te openen.');if(location.hash.startsWith('#rapporten'))$('report-status').textContent=ui('Gegevens laden mislukt. Probeer de pagina opnieuw te openen.');}
}
let chartRange='1M',rangeInitialized=false;
function syncRangeButtons(){for(const button of $('chart-ranges').querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.range===chartRange));}
const dayLabel=day=>new Date(day+'T00:00:00Z').toLocaleDateString((typeof appLocale==='function'?appLocale():'nl-NL'),{timeZone:'UTC'});
function draw(){
 if(!state||!document.body.classList.contains('home-page'))return;
 const view=homeViewState(),selection=$('instrument').value;
 const members=selection==='all'?homeChartMembers():selection.startsWith('portfolio:')?[]:[view.positions[Number(selection)]].filter(Boolean);
 if(members.some(p=>p.history_loaded===false)){loadHomePositionHistory(members);return;}
 drawDashboardChart(view,chartRange,selection,homeChartMembers());
}
$('chart-ranges').addEventListener('click',event=>{const button=event.target.closest('button[data-range]');if(!button)return;chartRange=button.dataset.range;for(const choice of $('chart-ranges').querySelectorAll('button'))choice.setAttribute('aria-pressed',String(choice===button));draw();});
$('instrument').addEventListener('change',()=>{homeChartChanged();draw();});
window.addEventListener('resize',()=>{clearTimeout(homeResizeTimer);homeResizeTimer=setTimeout(()=>{if(document.body.classList.contains('home-page'))draw();},120);});
let homeResizeTimer;
let selectedStock=null,searchTimer,searchController,searchVersion=0;
const stockFields=['name','symbol','exchange','currency'];
function closeSearch(){ $('search-results').replaceChildren();$('search-results').hidden=true;$('stock-search').setAttribute('aria-expanded','false'); }
function clearSelection(){selectedStock=null;for(const field of stockFields)$('purchase').elements.namedItem(field).value='';}
async function chooseStock(stock){
 const version=++searchVersion;clearSelection();closeSearch();$('search-status').textContent=ui('Notering en werkelijke koersvaluta controleren…');
 try{const response=await apiFetch('api/listing?symbol='+encodeURIComponent(stock.symbol));const result=await response.json();if(!response.ok)throw Error(result.error);if(version!==searchVersion||!accessSession?.user)return;
 selectedStock=result;for(const field of stockFields)$('purchase').elements.namedItem(field).value=result[field];
 $('stock-search').value=result.name;$('search-status').textContent=result.symbol+' · '+result.exchange+' · '+result.currency+ui(' geselecteerd.');$('purchase').elements.namedItem('quantity').focus();
 }catch(error){if(version===searchVersion)$('search-status').textContent=error.message;}
}
$('stock-search').addEventListener('input',()=>{
 clearTimeout(searchTimer);searchController?.abort();const version=++searchVersion;clearSelection();closeSearch();
 const query=$('stock-search').value.trim();
 if(query.length<2){$('search-status').textContent=ui('Typ minimaal twee letters van een bedrijfsnaam of symbool.');return;}
 $('search-status').textContent=ui('Aandelen zoeken…');
 searchTimer=setTimeout(async()=>{
  searchController=new AbortController();
  try{
   const response=await apiFetch('api/search?q='+encodeURIComponent(query),{signal:searchController.signal});const data=await response.json();
   if(version!==searchVersion)return;if(!response.ok)throw Error(data.error);
   for(const stock of data.results){const button=document.createElement('button');button.type='button';button.setAttribute('role','option');button.setAttribute('aria-selected','false');button.textContent=stock.name+' · '+stock.symbol+' · '+stock.exchange+' · '+stock.currency;button.addEventListener('click',()=>chooseStock(stock));$('search-results').append(button);}
   $('search-results').hidden=!data.results.length;$('stock-search').setAttribute('aria-expanded',String(Boolean(data.results.length)));
   $('search-status').textContent=data.results.length?data.results.length+ui(' resultaten van Yahoo. Kies de juiste notering; typ verder om te verfijnen.'):ui('Geen passende aandelen, ETF’s of fondsen gevonden. Probeer meer letters of het symbool.');
  }catch(error){if(error.name!=='AbortError'&&version===searchVersion)$('search-status').textContent=error.message||ui('Zoeken mislukt. Probeer opnieuw.');}
 },350);
});
$('stock-search').addEventListener('keydown',event=>{if(event.key==='ArrowDown'){const first=$('search-results').querySelector('button');if(first){event.preventDefault();first.focus();}}if(event.key==='Escape'){clearTimeout(searchTimer);searchController?.abort();searchVersion++;closeSearch();}if(event.key==='Enter'){event.preventDefault();$('search-results').querySelector('button')?.focus();}});
$('search-results').addEventListener('keydown',event=>{const buttons=[...$('search-results').querySelectorAll('button')],index=buttons.indexOf(document.activeElement);if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();buttons[(index+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(event.key==='Escape'){closeSearch();$('stock-search').focus();}});
$('purchase').addEventListener('submit',async event=>{event.preventDefault();if(!selectedStock){$('feedback').textContent=ui('Zoek en selecteer eerst een aandeel.');$('stock-search').focus();return;}const button=event.target.querySelector('button[type="submit"]');button.disabled=true;try{const response=await apiFetch('api/purchases',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))});const result=await response.json();if(!response.ok)throw Error(result.error);$('feedback').textContent=ui('Aankoop opgeslagen. De koers wordt opgehaald; het overzicht ververst automatisch.');event.target.reset();clearSelection();closeSearch();$('search-status').textContent=ui('Zoek op bedrijfsnaam of symbool. Aandelen, ETF’s en fondsen.');await load();}catch(error){$('feedback').textContent=error.message;}finally{button.disabled=false;}});
$('dividend-form').addEventListener('submit',async event=>{
 event.preventDefault();const selected=$('dividend-stock').value;if(!selected){$('dividend-feedback').textContent=ui('Voeg eerst een aankoop toe.');return;}
 const [symbol,exchange,currency,account_id]=JSON.parse(selected);const button=event.target.querySelector('button');button.disabled=true;
 try{const response=await apiFetch('api/dividends',{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify({...Object.fromEntries(new FormData(event.target)),symbol,exchange,currency,account_id})});const result=await response.json();if(!response.ok)throw Error(result.error);$('dividend-feedback').textContent=ui('Dividend apart opgeslagen en opgeteld bij je totale winst.');event.target.reset();await load();}catch(error){$('dividend-feedback').textContent=error.message;}finally{button.disabled=!state?.positions.length;}
});

function renderStockPage(){loadStocksDashboard();}
function renderDividendPage(){
 if(!state)return;
 const dividendSelected=$('dividend-stock').value;$('dividend-stock').replaceChildren();
 for(const p of state.positions){const o=document.createElement('option');o.value=JSON.stringify([p.symbol,p.exchange,p.currency,p.account_id]);o.textContent=p.name+' · '+p.symbol+' · '+p.account_name+' · '+p.currency;$('dividend-stock').append(o);}
 if([...$('dividend-stock').options].some(o=>o.value===dividendSelected))$('dividend-stock').value=dividendSelected;
 $('dividend-form').querySelector('button').disabled=!state.positions.length;
 renderDividendDashboard();
}
