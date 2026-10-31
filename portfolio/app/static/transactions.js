/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let transactionRows=[],editingTransaction=null,transactionPage=0,transactionLoad=0,deletePreview=null;
const transactionLabels={TRANSFER:ui('Omboeking'),BUY:ui('Aankoop'),SELL:ui('Verkoop'),DIVIDEND:ui('Dividend'),CAPITAL_RETURN:ui('Kapitaalterugbetaling'),SPLIT:ui('Aandelensplitsing')};
function clearTransactions(){transactionLoad++;transactionRows=[];editingTransaction=null;transactionPage=0;$('transaction-list').replaceChildren();closePopup('transaction-editor');$('transaction-form').reset();$('transaction-edit-title').textContent='';$('transaction-identity').textContent='';$('transaction-edit-feedback').textContent='';$('delete-backup').hidden=true;$('delete-backup').removeAttribute('href');$('transaction-feedback').textContent='';$('transaction-changes').replaceChildren();deletePreview=null;$('delete-review').hidden=true;$('delete-summary').textContent='';$('delete-confirmation').value='';$('delete-submit').disabled=true;$('delete-feedback').textContent='';}
async function loadTransactions(){
 const version=++transactionLoad,account=currentBroker;
 try{const response=await apiFetch('api/transactions?account_id='+encodeURIComponent(account));const result=await response.json();if(!response.ok)throw Error(result.error);if(version!==transactionLoad||!accessSession?.user)return;transactionRows=result.transactions;transactionPage=0;renderTransactions();}catch(error){if(version===transactionLoad)$('transaction-feedback').textContent=error.message;}
}
function transactionColumnValues(entry){return [entry.day,transactionLabels[entry.type],entry.name||entry.symbol||entry.ticker,entry.account_name,entry.currency,entry.quantity==null?'—':quantityLabel(entry.quantity),entry.amount?money(entry.amount,entry.currency):(entry.type==='SPLIT'||entry.type==='TRANSFER')?'—':money(entry.price,entry.currency),ui('Bekijken')];}
function transactionInPage(row,page){
 if(page==='transacties-dividend')return row.type==='DIVIDEND';
 if(page==='transacties-omzettingen')return row.type==='SPLIT'||row.type==='TRANSFER';
 return true;
}
function configureTransactionPage(page){
 $('transaction-page-title').textContent=page==='transacties-dividend'?ui('Dividend'):page==='transacties-omzettingen'?ui('Splitsingen en omzettingen'):ui('Transacties');
 $('transaction-page-description').textContent=page==='transacties-dividend'?ui('Bekijk de geboekte dividendontvangsten per brokeraccount.'):page==='transacties-omzettingen'?ui('Bekijk aandelensplitsingen en omzettingen per brokeraccount.'):ui('Bekijk aankopen, verkopen, splitsingen, dividend en kapitaalterugbetalingen. De rekeningkeuze bovenaan filtert dit overzicht. Alleen admins kunnen gegevens wijzigen.');
 const type=$('transaction-type');
 for(const option of type.options)option.hidden=!!option.value&&!transactionInPage({type:option.value},page);
 if(type.selectedOptions[0]?.hidden)type.value='';
 type.closest('label').hidden=page==='transacties-dividend';
 transactionPage=0;
}
function renderTransactions(){
 const query=$('transaction-search').value.trim().toLocaleLowerCase(),type=$('transaction-type').value;
 const filtered=sortTableData('transaction-list',transactionRows.filter(r=>transactionInPage(r,location.hash.slice(1).split('?')[0])&&(!type||r.type===type)&&[r.symbol,r.ticker,r.name,r.account_name,r.broker,r.day].join(' ').toLocaleLowerCase().includes(query)&&matchesTableColumns('transaction-list',transactionColumnValues(r))),transactionColumnValues);
 const pages=Math.max(1,Math.ceil(filtered.length/50));transactionPage=Math.min(transactionPage,pages-1);$('transaction-list').replaceChildren();
 for(const entry of filtered.slice(transactionPage*50,transactionPage*50+50)){
  const row=document.createElement('tr');for(const value of transactionColumnValues(entry).slice(0,7))cell(row,value);
  const button=document.createElement('button');button.type='button';button.textContent=ui('Bekijken');button.addEventListener('click',()=>openTransaction(entry));cell(row,'').append(button);$('transaction-list').append(row);
 }
 $('transaction-feedback').textContent=filtered.length+ui(' transacties · pagina ')+(transactionPage+1)+ui(' van ')+pages;
 $('transaction-prev').disabled=transactionPage===0;$('transaction-next').disabled=transactionPage>=pages-1;
}
async function openTransaction(entry){
 editingTransaction=entry;const form=$('transaction-form'),admin=accessSession?.user?.role==='admin'&&!entry.transfer_id,trade=entry.kind==='trade',split=entry.type==='SPLIT';
 openPopup('transaction-editor');$('transaction-edit-title').textContent=transactionLabels[entry.type]+' · '+(entry.name||entry.symbol||entry.ticker)+' · '+entry.account_name;
 $('transaction-identity').textContent=ui('Registratie ')+entry.id+' · '+(entry.symbol||entry.ticker)+' · '+(entry.exchange||ui('bronvaluta'))+' · '+entry.currency+(split?ui(' · Aantal vóór splitsing: ')+(entry.split_before==='0'?ui('niet in bronbestand'):entry.split_before):'');
 $('transaction-day').value=entry.day;$('transaction-time').value=entry.trade_time?.slice(11,19)||'';$('transaction-side').value=entry.side||'BUY';$('transaction-quantity').value=entry.quantity||'';$('transaction-price').value=entry.price||'';$('transaction-amount').value=entry.amount||'';$('transaction-note').value=entry.note||'';
 $('transaction-time-label').hidden=!trade;$('transaction-side-label').hidden=!trade||split||Boolean(entry.transfer_id);$('transaction-quantity-label').hidden=!trade;$('transaction-price-label').hidden=!trade||split||Boolean(entry.transfer_id);$('transaction-amount-label').hidden=trade;$('transaction-note-label').hidden=entry.kind!=='dividend';
 for(const field of form.querySelectorAll('input,select,textarea'))field.disabled=!admin||field.closest('label').hidden;
 $('transaction-save').hidden=!admin;$('transaction-edit-feedback').textContent=entry.transfer_id?ui('Omboeking bekijken; wijzigen kan alleen door de herstelback-up terug te zetten.'):admin?ui('Pas de gegevens aan en kies Wijzigingen opslaan.'):ui('Je kunt deze transactie bekijken. Alleen een admin kan wijzigingen opslaan.');
 $('transaction-changes').replaceChildren();
 try{const response=await apiFetch('api/transactions/changes?kind='+entry.kind+'&id='+entry.id);const result=await response.json();if(!response.ok)throw Error(result.error);if(editingTransaction!==entry)return;
  for(const change of result.changes){const before=JSON.parse(change.before_payload),after=JSON.parse(change.after_payload),item=document.createElement('li');const diffs=Object.keys(after).filter(key=>before[key]!==after[key]).map(key=>( {quantity:ui('Aantal'),price:ui('Prijs'),amount:ui('Bedrag'),paid_on:ui('Datum'),purchased_on:ui('Datum'),trade_time:ui('Tijd'),side:ui('Type'),note:ui('Notitie')}[key]||key)+': '+before[key]+' → '+after[key]);item.textContent=new Date(change.created_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL'))+' · '+change.changed_by+' · '+diffs.join('; ');$('transaction-changes').append(item);}
  if(!result.changes.length){const item=document.createElement('li');item.textContent=ui('Nog geen handmatige wijzigingen.');$('transaction-changes').append(item);}
 }catch(error){if(editingTransaction===entry)$('transaction-edit-feedback').textContent=error.message;}
}
function renderDeleteAccounts(){
 const select=$('delete-account'),previous=select.value;select.replaceChildren();
 const all=document.createElement('option');all.value='all';all.textContent=ui('Alles · alle brokeraccounts');select.append(all);
 for(const account of state.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;select.append(option);}
 if([...select.options].some(o=>o.value===previous))select.value=previous;
}
function clearDeleteReview(){deletePreview=null;$('delete-review').hidden=true;$('delete-confirmation').value='';$('delete-submit').disabled=true;$('delete-feedback').textContent='';}
function bindTransactions(){
 for(const id of ['transaction-search','transaction-type'])$(id).addEventListener('input',()=>{transactionPage=0;renderTransactions();});
 $('transaction-refresh').addEventListener('click',loadTransactions);$('transaction-prev').addEventListener('click',()=>{transactionPage--;renderTransactions();});$('transaction-next').addEventListener('click',()=>{transactionPage++;renderTransactions();});
 $('transaction-close').addEventListener('click',()=>{editingTransaction=null;closePopup('transaction-editor');});
 $('transaction-form').addEventListener('submit',async event=>{event.preventDefault();const entry=editingTransaction;if(!entry)return;const button=$('transaction-save');button.disabled=true;
  try{const data={...Object.fromEntries(new FormData(event.target)),id:entry.id,kind:entry.kind,revision:entry.revision};await jsonAction('api/transactions/edit',data);editingTransaction=null;closePopup('transaction-editor');stateETag=null;await load();await loadTransactions();$('transaction-edit-feedback').textContent='';$('transaction-feedback').textContent+=ui(' · Wijzigingen opgeslagen; portefeuille opnieuw berekend.');$('transaction-feedback').scrollIntoView({behavior:'smooth',block:'center'});}catch(error){$('transaction-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
 $('delete-account').addEventListener('change',clearDeleteReview);
 $('delete-confirmation').addEventListener('input',()=>{$('delete-submit').disabled=!deletePreview||$('delete-confirmation').value!=='VERWIJDEREN';});
 $('delete-preview').addEventListener('click',async()=>{clearDeleteReview();const account=$('delete-account').value;const button=$('delete-preview');button.disabled=true;
  try{const response=await apiFetch('api/portfolio/delete-preview?account_id='+encodeURIComponent(account));const result=await response.json();if(!response.ok)throw Error(result.error);if(account!==$('delete-account').value)return;deletePreview=result;
   const c=result.counts;$('delete-summary').textContent=(account==='all'?ui('Alle brokeraccounts'):result.label)+': '+(c.purchases||0)+ui(' aankopen/verkopen/splitsingen, ')+(c.dividends||0)+ui(' dividendontvangsten, ')+(c.capital_returns||0)+ui(' kapitaalterugbetalingen, ')+(c.import_batches||0)+ui(' imports en ')+(c.import_issues||0)+ui(' beoordelingen. Ook de bijbehorende bron-ID’s, omrekeningen, aandelenkoppelingen en wijzigingshistorie worden verwijderd.')+(account==='all'?ui(' Gedeelde aandelenkoersen, categorieën en hun cache worden ook gewist.'):ui(' Gedeelde aandelenkoersen blijven beschikbaar voor de overige rekeningen.'));
   $('delete-review').hidden=false;$('delete-confirmation').focus();
  }catch(error){$('delete-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
 $('delete-form').addEventListener('submit',async event=>{event.preventDefault();if(!deletePreview)return;const snapshot=deletePreview,button=$('delete-submit');button.disabled=true;
  try{const result=await jsonAction('api/portfolio/delete',{account_id:snapshot.account_id,revision:snapshot.revision,confirmation:$('delete-confirmation').value});clearDeleteReview();clearTransactions();importPreview=null;$('import-preview').hidden=true;clearImportIssues();clearImportMappings();stateETag=null;await load();$('delete-feedback').textContent=ui('Gegevens verwijderd voor ')+result.label+ui('. Een herstelback-up is bewaard.');const link=$('delete-backup');link.href='api/portfolio/deletion-backup?name='+encodeURIComponent(result.backup_name);link.hidden=false;$('delete-feedback').scrollIntoView({behavior:'smooth',block:'center'});}
  catch(error){$('delete-feedback').textContent=error.message;clearDeleteReview();$('delete-feedback').textContent=error.message;}
 });
}
