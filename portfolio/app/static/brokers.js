/* Broker changes use account IDs; renaming never moves ledger entries. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let brokerEdit=null,brokerDelete=null,brokerEditorRequest=0;
async function openBrokerEditor(id){
 const request=++brokerEditorRequest;brokerEdit=null;$('broker-edit-feedback').textContent='';
 try{
  const response=await apiFetch('api/accounts/edit?account_id='+id),account=await response.json();if(!response.ok)throw Error(account.error);
  if(request!==brokerEditorRequest||accessSession?.user?.role!=='admin')return;
  brokerEdit=account;const form=$('broker-edit-form');form.elements.namedItem('name').value=account.name;form.elements.namedItem('broker').value=account.broker;openPopup('broker-editor');
 }catch(error){$('broker-manage-feedback').textContent=error.message;}
}
async function openBrokerDeletion(id){
 const request=++brokerEditorRequest;brokerDelete=null;$('broker-delete-feedback').textContent='';$('broker-delete-confirm').value='';$('broker-delete-submit').disabled=true;
 try{
  const response=await apiFetch('api/accounts/delete-preview?account_id='+id),result=await response.json();if(!response.ok)throw Error(result.error);
  if(request!==brokerEditorRequest||accessSession?.user?.role!=='admin')return;
  brokerDelete=result;const c=result.counts;$('broker-delete-summary').textContent=result.label+': '+ui('{trades} boekingen, {dividends} dividendontvangsten, {capital} kapitaalterugbetalingen, {imports} imports en {issues} beoordelingen.',{trades:c.purchases||0,dividends:c.dividends||0,capital:c.capital_returns||0,imports:c.import_batches||0,issues:c.import_issues||0});openPopup('broker-delete');
 }catch(error){$('broker-manage-feedback').textContent=error.message;}
}
function bindBrokerManagement(){
 $('broker-edit-cancel').addEventListener('click',()=>closePopup('broker-editor'));
 $('broker-delete-cancel').addEventListener('click',()=>closePopup('broker-delete'));
 $('broker-delete-confirm').addEventListener('input',()=>{$('broker-delete-submit').disabled=!brokerDelete||$('broker-delete-confirm').value!=='VERWIJDEREN';});
 $('broker-edit-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!brokerEdit)return;const account=brokerEdit,button=event.target.querySelector('button[type=submit]');button.disabled=true;
  try{
   await jsonAction('api/accounts/edit',{...Object.fromEntries(new FormData(event.target)),id:account.id,revision:account.revision});brokerEdit=null;closePopup('broker-editor');stateETag=null;await load();$('broker-manage-feedback').textContent=ui('Brokeraccount bijgewerkt.');
  }catch(error){$('broker-edit-feedback').textContent=error.message;}finally{button.disabled=false;}
 });
 $('broker-delete-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!brokerDelete||$('broker-delete-confirm').value!=='VERWIJDEREN')return;const account=brokerDelete,button=$('broker-delete-submit');button.disabled=true;
  try{
   const result=await jsonAction('api/accounts/delete',{account_id:account.account_id,revision:account.revision,confirmation:$('broker-delete-confirm').value});brokerDelete=null;closePopup('broker-delete');if(String(currentBroker)===String(account.account_id))currentBroker='all';
   clearTransactions();clearStockDetail();clearImportIssues();clearImportMappings();importPreview=null;$('import-preview').hidden=true;stateETag=null;await load();
   $('broker-manage-feedback').textContent=ui('Brokeraccount verwijderd. Een herstelback-up is bewaard.');const link=$('broker-manage-backup');link.href='api/portfolio/deletion-backup?name='+encodeURIComponent(result.backup_name);link.hidden=false;
  }catch(error){$('broker-delete-feedback').textContent=error.message;button.disabled=false;}
 });
}
