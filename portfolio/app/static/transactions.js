/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let transactionRows=[],editingTransaction=null,transactionPage=0,transactionLoad=0,deletePreview=null;
const transactionLabels={COST:ui('Kosten'),TAX:ui('Belastingen'),TRANSFER:ui('Omboeking'),BUY:ui('Aankoop'),SELL:ui('Verkoop'),DIVIDEND:ui('Dividend'),CAPITAL_RETURN:ui('Kapitaalterugbetaling'),SPLIT:ui('Aandelensplitsing')};
function clearTransactions(){transactionLoad++;transactionRows=[];editingTransaction=null;transactionPage=0;$('transaction-list').replaceChildren();closePopup('transaction-editor');$('transaction-form').reset();$('transaction-cost-rows').replaceChildren();$('transaction-cost-existing').replaceChildren();$('transaction-account').replaceChildren();$('transaction-edit-title').textContent='';$('transaction-identity').textContent='';$('transaction-edit-feedback').textContent='';$('delete-backup').hidden=true;$('delete-backup').removeAttribute('href');$('transaction-feedback').textContent='';$('transaction-changes').replaceChildren();deletePreview=null;$('delete-review').hidden=true;$('delete-summary').textContent='';$('delete-confirmation').value='';$('delete-submit').disabled=true;$('delete-feedback').textContent='';}
async function loadTransactions({background=false}={}){
 const version=++transactionLoad,account=currentBroker;
 try{const response=await apiFetch('api/transactions?account_id='+encodeURIComponent(account),{background});const result=await response.json();if(!response.ok)throw Error(result.error);if(version!==transactionLoad||!accessSession?.user)return;transactionRows=result.transactions;const dateFilter=new URLSearchParams(location.hash.split('?')[1]||'').get('datum');if(dateFilter&&/^\d{4}-\d{2}-\d{2}$/.test(dateFilter))$('transaction-search').value=dateFilter;transactionPage=0;renderTransactions();}catch(error){if(version===transactionLoad)$('transaction-feedback').textContent=error.message;}
}
function transactionColumnValues(entry){return [entry.day,transactionLabels[entry.type],entry.name||entry.symbol||entry.ticker,entry.account_name,entry.currency,entry.quantity==null?'—':quantityLabel(entry.quantity),entry.type==='TRANSFER'&&entry.transfer_cost?money(entry.transfer_cost,entry.currency):entry.amount?money(entry.amount,entry.currency):(entry.type==='SPLIT'||entry.type==='TRANSFER')?'—':money(entry.price,entry.currency),ui('Bekijken')];}
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
 editingTransaction=entry;const form=$('transaction-form'),transfer=Boolean(entry.transfer_id),repair=transfer&&entry.side==='BUY',admin=accessSession?.user?.role==='admin'&&(!transfer||repair),trade=entry.kind==='trade',split=entry.type==='SPLIT';
 openPopup('transaction-editor');$('transaction-edit-title').textContent=transactionLabels[entry.type]+' · '+(entry.name||entry.symbol||entry.ticker)+' · '+entry.account_name;
 $('transaction-identity').textContent=ui('Registratie ')+entry.id+' · '+(entry.symbol||entry.ticker)+' · '+(entry.exchange||ui('bronvaluta'))+' · '+entry.currency+(split?ui(' · Aantal vóór splitsing: ')+(entry.split_before==='0'?ui('niet in bronbestand'):entry.split_before):'');
 $('transaction-day').value=entry.day;$('transaction-time').value=entry.trade_time?.slice(11,19)||'';$('transaction-side').value=entry.side||'BUY';$('transaction-quantity').value=entry.quantity||'';$('transaction-price').value=entry.price||'';$('transaction-amount').value=(entry.transfer_id?entry.transfer_cost:entry.amount)||'';$('transaction-note').value=entry.note||'';
 const accounts=$('transaction-account');accounts.replaceChildren();for(const account of state.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;accounts.append(option);}accounts.value=entry.account_id;
 $('transaction-cost-rows').replaceChildren();for(const charge of entry.kind==='charge'?[entry]:entry.charges||[])addTransactionCost(charge,admin,entry.kind==='charge');
 const existing=$('transaction-cost-existing');existing.replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent=ui('Bestaande kosten koppelen');existing.append(empty);for(const charge of transactionRows.filter(r=>r.kind==='charge'&&r.account_id===entry.account_id&&!r.linked_transaction?.kind)){const option=document.createElement('option');option.value=charge.id;option.textContent=charge.day+' · '+chargeLabels[charge.category]+' · '+charge.amount+' '+charge.currency+' · '+(charge.ticker||'');existing.append(option);}existing.closest('label').hidden=!admin||entry.kind==='charge'||existing.options.length===1;
 $('transaction-costs').hidden=Boolean(entry.transfer_id)||split;$('transaction-cost-add').hidden=!admin||entry.kind==='charge';
 $('transaction-time-label').hidden=!trade;$('transaction-side-label').hidden=!trade||split||Boolean(entry.transfer_id);$('transaction-quantity-label').hidden=!trade;$('transaction-price-label').hidden=!trade||split||Boolean(entry.transfer_id);$('transaction-amount-label').hidden=trade&&!entry.transfer_id||entry.kind==='charge';$('transaction-note-label').hidden=entry.kind!=='dividend';
 for(const field of form.querySelectorAll('input,select,textarea'))field.disabled=!admin||Boolean(field.closest('[hidden]'))||(transfer&&field.id!=='transaction-quantity');
 accounts.disabled=!admin||transfer||Boolean(entry.linked_transaction?.kind);
 $('transaction-save').hidden=!admin;$('transaction-edit-feedback').textContent=admin?ui('Pas de gegevens aan en kies Wijzigingen opslaan.'):ui('Je kunt deze transactie bekijken. Alleen een admin kan wijzigingen opslaan.');
 if(admin&&entry.linked_transaction?.kind)$('transaction-edit-feedback').textContent+=' '+ui('Wijzig het brokeraccount via de bijbehorende transactie.');
 $('transaction-changes').replaceChildren();
 try{const response=await apiFetch('api/transactions/changes?kind='+entry.kind+'&id='+entry.id);const result=await response.json();if(!response.ok)throw Error(result.error);if(editingTransaction!==entry)return;
  for(const change of result.changes){const before=JSON.parse(change.before_payload),after=JSON.parse(change.after_payload),item=document.createElement('li');const diffs=Object.keys(after).filter(key=>key!=='batch_id'&&JSON.stringify(before[key])!==JSON.stringify(after[key])).map(key=>( {account_id:ui('Brokeraccount'),charges:ui('Kosten en belastingen'),category:ui('Soort'),currency:ui('Valuta'),included_in_net:ui('Reeds netto verwerkt'),description:ui('Notitie'),quantity:ui('Aantal'),price:ui('Prijs'),amount:ui('Bedrag'),paid_on:ui('Datum'),purchased_on:ui('Datum'),trade_time:ui('Tijd'),side:ui('Type'),note:ui('Notitie')}[key]||key)+': '+transactionChangeValue(key,before[key])+' → '+transactionChangeValue(key,after[key]));item.textContent=new Date(change.created_at).toLocaleString((typeof appLocale==='function'?appLocale():'nl-NL'))+' · '+change.changed_by+' · '+diffs.join('; ');$('transaction-changes').append(item);}
  if(!result.changes.length){const item=document.createElement('li');item.textContent=ui('Nog geen handmatige wijzigingen.');$('transaction-changes').append(item);}
 }catch(error){if(editingTransaction===entry)$('transaction-edit-feedback').textContent=error.message;}
}
function transactionChangeValue(key,value){
 if(key==='charges')return (value||[]).map(c=>chargeLabels[c.category]+': '+c.amount+' '+c.currency).join(', ')||'—';
 if(key==='account_id'){const account=state.accounts.find(a=>String(a.id)===String(value));return account?account.name+' · '+account.broker:value;}
 if(key==='category')return chargeLabels[value]||value;
 if(key==='included_in_net')return value?ui('Ja'):ui('Nee');
 return value??'—';
}
function addTransactionCost(charge={},admin=true,standalone=false){
 const row=document.createElement('div');row.className='transaction-cost-row';if(charge.id)row.dataset.id=charge.id;if(charge.revision)row.dataset.revision=charge.revision;
 function field(title,element,key){const label=document.createElement('label');label.append(document.createTextNode(title),element);element.dataset.field=key;element.disabled=!admin;row.append(label);return element;}
 const category=document.createElement('select');for(const [value,title] of Object.entries(chargeLabels)){const option=document.createElement('option');option.value=value;option.textContent=title;category.append(option);}category.value=charge.category||'COMMISSION';field(ui('Soort'),category,'category');
 const amount=document.createElement('input');amount.type='number';amount.step='any';amount.required=true;amount.value=charge.amount??'';field(ui('Bedrag'),amount,'amount');
 const currency=document.createElement('input');currency.required=true;currency.maxLength=3;currency.pattern='[A-Za-z]{3}';currency.value=charge.currency||editingTransaction.currency;field(ui('Valuta'),currency,'currency');
 const note=document.createElement('input');note.maxLength=500;note.value=charge.description||'';field(ui('Notitie'),note,'description');
 const included=document.createElement('input');included.type='checkbox';included.checked=Boolean(charge.included_in_net);field(ui('Reeds netto verwerkt'),included,'included_in_net');
 if(!standalone&&admin){const remove=document.createElement('button');remove.type='button';remove.textContent=ui('Verwijderen');remove.addEventListener('click',()=>row.remove());row.append(remove);}
 $('transaction-cost-rows').append(row);
}
function transactionCostInputs(){return [...$('transaction-cost-rows').children].map(row=>{const result=row.dataset.id?{id:Number(row.dataset.id)}:{};if(row.dataset.revision)result.revision=row.dataset.revision;for(const input of row.querySelectorAll('[data-field]'))result[input.dataset.field]=input.type==='checkbox'?Number(input.checked):input.dataset.field==='currency'?input.value.trim().toUpperCase():input.value;return result;});}
function renderDeleteAccounts(){
 const select=$('delete-account'),previous=select.value;select.replaceChildren();
 const all=document.createElement('option');all.value='all';all.textContent=ui('Alles · alle brokeraccounts');select.append(all);
 for(const account of state.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;select.append(option);}
 if([...select.options].some(o=>o.value===previous))select.value=previous;
}
function clearDeleteReview(){deletePreview=null;$('delete-review').hidden=true;$('delete-confirmation').value='';$('delete-submit').disabled=true;$('delete-feedback').textContent='';}
// On a timed-out POST, the server might still commit. Never suggest a blind retry.
function transactionSaveFailure(error){
 if(error?.name==='TimeoutError'||error?.name==='AbortError'){
  return ui('Opslaan duurde te lang. Controleer eerst het transactieoverzicht voordat je opnieuw opslaat.');
 }
 return error?.message||ui('Opslaan mislukt. Probeer opnieuw.');
}
function bindTransactions(){
 $('transaction-cost-add').addEventListener('click',()=>addTransactionCost());
 $('transaction-cost-existing').addEventListener('change',event=>{const charge=transactionRows.find(r=>r.kind==='charge'&&String(r.id)===event.target.value);if(charge&&![...$('transaction-cost-rows').children].some(row=>row.dataset.id===String(charge.id)))addTransactionCost(charge);event.target.value='';});
 for(const id of ['transaction-search','transaction-type'])$(id).addEventListener('input',()=>{transactionPage=0;renderTransactions();});
 $('transaction-refresh').addEventListener('click',loadTransactions);$('transaction-prev').addEventListener('click',()=>{transactionPage--;renderTransactions();});$('transaction-next').addEventListener('click',()=>{transactionPage++;renderTransactions();});
 $('transaction-close').addEventListener('click',()=>{editingTransaction=null;closePopup('transaction-editor');});
 $('transaction-form').addEventListener('submit',async event=>{event.preventDefault();const entry=editingTransaction;if(!entry)return;const button=$('transaction-save');button.disabled=true;
  try{const data={...Object.fromEntries(new FormData(event.target)),id:entry.id,kind:entry.kind,revision:entry.revision};if(entry.kind==='charge')Object.assign(data,transactionCostInputs()[0]);else if(!entry.transfer_id&&entry.type!=='SPLIT')data.charges=transactionCostInputs();await jsonAction('api/transactions/edit',data,{signal:AbortSignal.timeout(30000)});editingTransaction=null;closePopup('transaction-editor');stateETag=null;if(typeof clearChargeReport==='function')clearChargeReport();void load({background:true,refreshTransactions:false});await loadTransactions({background:true});$('transaction-edit-feedback').textContent='';$('transaction-feedback').textContent+=ui(' · Wijzigingen opgeslagen; portefeuille opnieuw berekend.');$('transaction-feedback').scrollIntoView({behavior:'smooth',block:'center'});}catch(error){$('transaction-edit-feedback').textContent=transactionSaveFailure(error);}finally{button.disabled=false;}
 });
 $('delete-account').addEventListener('change',clearDeleteReview);
 $('delete-confirmation').addEventListener('input',()=>{$('delete-submit').disabled=!deletePreview||$('delete-confirmation').value!=='VERWIJDEREN';});
 $('delete-preview').addEventListener('click',async()=>{clearDeleteReview();const account=$('delete-account').value;const button=$('delete-preview');button.disabled=true;
  try{const response=await apiFetch('api/portfolio/delete-preview?account_id='+encodeURIComponent(account));const result=await response.json();if(!response.ok)throw Error(result.error);if(account!==$('delete-account').value)return;deletePreview=result;
   const c=result.counts;$('delete-summary').textContent=(account==='all'?ui('Alle brokeraccounts'):result.label)+': '+(c.purchases||0)+ui(' aankopen/verkopen/splitsingen, ')+(c.dividends||0)+ui(' dividendontvangsten, ')+(c.capital_returns||0)+ui(' kapitaalterugbetalingen, ')+(c.charges||0)+ui(' kosten- en belastingboekingen, ')+(c.import_batches||0)+ui(' imports en ')+(c.import_issues||0)+ui(' beoordelingen. Ook de bijbehorende bron-ID’s, omrekeningen, aandelenkoppelingen en wijzigingshistorie worden verwijderd.')+(account==='all'?ui(' Gedeelde aandelenkoersen, categorieën en hun cache worden ook gewist.'):ui(' Gedeelde aandelenkoersen blijven beschikbaar voor de overige rekeningen.'));
   $('delete-review').hidden=false;$('delete-confirmation').focus();
  }catch(error){$('delete-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
 $('delete-form').addEventListener('submit',async event=>{event.preventDefault();if(!deletePreview)return;const snapshot=deletePreview,button=$('delete-submit');button.disabled=true;
  try{const result=await jsonAction('api/portfolio/delete',{account_id:snapshot.account_id,revision:snapshot.revision,confirmation:$('delete-confirmation').value});clearDeleteReview();clearTransactions();importPreview=null;$('import-preview').hidden=true;clearImportIssues();clearImportMappings();stateETag=null;await load();$('delete-feedback').textContent=ui('Gegevens verwijderd voor ')+result.label+ui('. Een herstelback-up is bewaard.');const link=$('delete-backup');link.href='api/portfolio/deletion-backup?name='+encodeURIComponent(result.backup_name);link.hidden=false;$('delete-feedback').scrollIntoView({behavior:'smooth',block:'center'});}
  catch(error){$('delete-feedback').textContent=error.message;clearDeleteReview();$('delete-feedback').textContent=error.message;}
 });
}
