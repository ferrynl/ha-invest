
/* Broker choices, export instructions and on-demand read-only API imports. */
let importDirectoryProviders=[];
let directorySelection='';
let flexRequest=null;

function renderImportDirectory(){
 const grid=$('import-directory');
 if(!grid)return;
 const search=$('import-search').value.trim().toLowerCase(), format=$('import-format').value;
 const choices=importDirectoryProviders.filter(provider=>provider.name.toLowerCase().includes(search)&&(!format||provider.formats.includes(format)));
 grid.replaceChildren();
 for(const provider of choices){
  const button=document.createElement('button');
  button.type='button';button.className='import-broker-choice';
  button.setAttribute('aria-pressed',String(directorySelection===provider.id));
  const title=document.createElement('strong');title.textContent=provider.name;
  const formats=document.createElement('span');formats.className='import-formats';formats.textContent=provider.formats.join(' · ').toUpperCase();
  const accountCount=state?.accounts.filter(account=>account.broker===provider.name).length||0;
  if(accountCount){
   const count=document.createElement('small');count.textContent=accountCount===1?ui('1 brokeraccount'):ui('{count} brokeraccounts',{count:accountCount});
   button.append(title,formats,count);
  }else button.append(title,formats);
  button.addEventListener('click',()=>selectDirectoryBroker(provider));
  grid.append(button);
 }
 $('import-directory-status').textContent=choices.length?'':ui('Geen brokers gevonden.');
}

function selectDirectoryBroker(provider){
 directorySelection=provider.id;
 $('import-provider').value=provider.id;
 $('import-file').value='';
 refreshImportAccounts();
 renderImportDirectory();
 $('import-broker-title').textContent=provider.name;
 $('import-broker-guide').textContent=ui(provider.guide||'');
 const docs=$('import-broker-docs');docs.hidden=!provider.source;
 if(provider.source)docs.href=provider.source;
 const legacy=$('import-broker-more');
 legacy.hidden=!['trading212','traderepublic','revolut'].includes(provider.id);
 legacy.href='#import-'+provider.id;
 const upload=$('import-broker-upload');
 upload.textContent=ui('{formats} importeren',{formats:provider.formats.filter(format=>format!=='api').map(format=>format.toUpperCase()).join(' / ')});
 $('import-broker-t212').hidden=provider.id!=='trading212';
 $('import-broker-api').hidden=!['interactivebrokers','saxo'].includes(provider.id);
 $('import-broker-detail').hidden=false;
 $('import-broker-title').focus();
}

function bindImportDirectory(){
 $('import-search').addEventListener('input',renderImportDirectory);
 $('import-format').addEventListener('change',renderImportDirectory);
 $('import-broker-upload').addEventListener('click',()=>{
  $('import-provider').value=directorySelection;refreshImportAccounts();openPopup('import-form-editor');
 });
 $('import-broker-t212').addEventListener('click',()=>openPopup('import-api-report'));
 $('import-broker-api').addEventListener('click',()=>{
  const form=$('import-broker-api-form');
  flexRequest=null;form.reset();
  const isFlex=directorySelection==='interactivebrokers';
  for(const group of form.querySelectorAll('fieldset')){
   group.hidden=group.dataset.api!==(isFlex?'flex':'saxo');
   group.disabled=group.hidden;
  }
  accountOptions($('import-api-account'),state?.accounts.filter(account=>account.broker===importProviders[directorySelection])||[],currentBroker);
  $('import-broker-api-status').textContent=$('import-api-account').value?'':ui('Maak eerst een brokeraccount aan via de importknop.');
  $('import-broker-api-submit').disabled=!$('import-api-account').value;
  $('import-broker-api-poll').hidden=true;
  openPopup('broker-api-editor');
 });
 $('broker-api-editor-popup').addEventListener('close',()=>{
  flexRequest=null;$('import-broker-api-form').reset();
 });
 const form=$('import-broker-api-form');
 const send=async (poll=false)=>{
  if(!form.reportValidity())return;
  const provider=directorySelection;
  const status=$('import-broker-api-status'), start=$('import-broker-api-submit'), check=$('import-broker-api-poll');
  const data=Object.fromEntries(new FormData(form));
  const account=data.account_id;
  if(poll){
   if(!flexRequest||flexRequest.account!==account)return;
   data.reference=flexRequest.reference;
  }
  start.disabled=check.disabled=true;
  status.textContent=ui('Rapport ophalen…');
  try{
   const operation=provider==='saxo'?'fetch':poll?'poll':'start';
   const result=await jsonAction('api/imports/'+provider+'/'+operation,data,{signal:AbortSignal.timeout(60000)});
   if(!$('broker-api-editor-popup').open||directorySelection!==provider)return;
   if(result.preview){
    closePopup('broker-api-editor');showImportPreview(result.preview);await loadImportHistory();
   }else if(result.reference){
    flexRequest={reference:result.reference,account};check.hidden=false;
    status.textContent=ui('Rapport aangevraagd. Controleer de status na enkele seconden.');
   }else if(result.pending)status.textContent=ui('Het Flex-rapport wordt voorbereid. Controleer de status opnieuw.');
  }catch(error){status.textContent=error.message;}
  finally{
   if(provider==='saxo')form.elements.namedItem('token').value='';
   start.disabled=check.disabled=false;
  }
 };
 form.addEventListener('submit',event=>{event.preventDefault();send();});
 $('import-broker-api-poll').addEventListener('click',()=>send(true));
 $('import-api-account').addEventListener('change',()=>{flexRequest=null;$('import-broker-api-poll').hidden=true;});
}
