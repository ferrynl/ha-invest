/* Poll only small local metadata; never refetch providers or rebuild financial histories. */
let categoryScope='',categoryItems=new Map(),categoryETag=null,categoryCounts=null,categoryNextCheck=0,categoryRequest=null,categoryGeneration=0;
const categoryKey=p=>JSON.stringify([p.symbol,p.exchange,p.currency]);
function categoryFieldLabel(categories={},sync={},field){
 if(categories[field])return categories[field];
 if(field==='category')return 'Zelf te kiezen';
 if(categories['manual_'+field])return 'Handmatig leeg';
 if(sync.status==='complete'||sync.status==='partial')return 'Niet beschikbaar bij bron';
 if(sync.status==='retry')return 'Ophalen mislukt';
 if(sync.status==='fetching')return 'Wordt opgehaald…';
 return 'Nog ophalen…';
}
function categoryProgressLabel(counts){
 if(!counts.total)return 'Nog geen aandelen om in te delen.';
 return counts.processed+' van '+counts.total+' profielen gecontroleerd · '+counts.complete+' volledig ingedeeld · '+counts.partial+' met ontbrekende velden · '+(counts.pending+counts.fetching)+' nog ophalen'+(counts.retry?' · '+counts.retry+' wachten op opnieuw proberen':'')+'. Je eigen categorie kies je zelf.';
}
function categoryForPosition(p){return categoryScope==='all'&&categoryItems.get(categoryKey(p))||{categories:p.categories||{},sync:{status:'pending'}};}
function clearCategoryOverview(){categoryGeneration++;categoryScope='';categoryItems.clear();categoryETag=null;categoryCounts=null;categoryNextCheck=0;categoryRequest=null;$('stock-categories-summary').textContent='';$('stock-categories-progress').value=0;$('stock-categories-refresh').disabled=false;}
function applyCategoryOverview(result){
 categoryCounts=result.counts;categoryItems=new Map(result.entries.map(entry=>[categoryKey(entry),entry]));
 for(const p of state.positions){const entry=categoryItems.get(categoryKey(p));if(entry)p.categories=entry.categories;}
 const saved=new Map((state.instrument_categories||[]).map(entry=>[categoryKey(entry),entry]));for(const entry of result.entries)saved.set(categoryKey(entry),{symbol:entry.symbol,exchange:entry.exchange,currency:entry.currency,...entry.categories});state.instrument_categories=[...saved.values()];
 for(const row of $('positions').querySelectorAll('tr[data-category-key]')){
  const entry=categoryItems.get(row.dataset.categoryKey);if(!entry)continue;
  for(const fieldCell of row.querySelectorAll('[data-category-field]')){const label=categoryFieldLabel(entry.categories,entry.sync,fieldCell.dataset.categoryField);if(fieldCell.textContent!==label)fieldCell.textContent=label;}
 }
 if(typeof updateStocksCategories==='function')updateStocksCategories(result.entries);
 $('stock-categories-summary').textContent=categoryProgressLabel(result.counts);$('stock-categories-progress').max=Math.max(1,result.counts.total);$('stock-categories-progress').value=result.counts.processed;
}
async function refreshCategoryOverview(force=false){
 if(!state||!accessSession?.user||location.hash!=='#aandelen'||document.hidden)return;
 const account='all';
 if(categoryScope!==account){categoryGeneration++;categoryScope=account;categoryETag=null;categoryItems.clear();categoryCounts=null;categoryRequest=null;categoryNextCheck=0;}
 if(categoryRequest||!force&&Date.now()<categoryNextCheck)return;
 const request={generation:categoryGeneration,account};categoryRequest=request;$('stock-categories-refresh').disabled=true;
 try{
  const headers={};if(categoryETag)headers['If-None-Match']=categoryETag;
  const response=await apiFetch('api/instruments/categories?account_id='+encodeURIComponent(account),{headers});
  if(request.generation!==categoryGeneration||!state||!accessSession?.user)return;
  if(response.status===304)return;
  const result=await response.json();if(request.generation!==categoryGeneration||!state||!accessSession?.user)return;if(!response.ok)throw Error(result.error||'Categorieën laden mislukt.');
  if(result.account_id!==account)return;
  categoryETag=response.headers.get('ETag');applyCategoryOverview(result);
 }catch(error){if(request.generation===categoryGeneration&&accessSession?.user)$('stock-categories-summary').textContent='Actuele categorieën laden mislukt. De getoonde gegevens blijven bewaard. Kies Weergave vernieuwen.';}
 finally{if(categoryRequest===request){categoryRequest=null;$('stock-categories-refresh').disabled=false;const active=!categoryCounts||categoryCounts.pending+categoryCounts.fetching+categoryCounts.retry>0;categoryNextCheck=Date.now()+(active?5000:30000);}}
}
if(typeof document!=='undefined'){
 $('stock-categories-refresh').addEventListener('click',()=>refreshCategoryOverview(true));
 setInterval(()=>refreshCategoryOverview(),5000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshCategoryOverview(true);});
}
if(typeof module!=='undefined')module.exports={categoryFieldLabel,categoryProgressLabel,categoryKey};
