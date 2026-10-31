/* Relay credentials never enter the browser. Untrusted text uses textContent. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let feedbackItems=[],feedbackMine=[],feedbackGeneration=0,feedbackBusy=false;
function clearFeedback(){feedbackGeneration++;feedbackItems=[];feedbackMine=[];for(const id of ['feedback-list','feedback-mine'])$(id).replaceChildren();for(const id of ['feedback-status','feedback-connection','feedback-form-status','feedback-connect-status'])$(id).textContent='';$('feedback-form').reset();$('feedback-form').dataset.requestId='';$('feedback-connect-form').reset();$('feedback-new').disabled=true;$('feedback-connect-open').hidden=true;}
function feedbackState(value){return {local:ui('Wacht op verzending'),queued:ui('Ontvangen door de meldservice'),sending:ui('Wordt verwerkt'),uncertain:ui('Controle door beheerder nodig'),blocked:ui('Geblokkeerd; neem contact op met de beheerder'),open:ui('Open'),closed:ui('Gesloten')}[value]||ui('Wordt verwerkt');}
function renderFeedback(){
 const query=$('feedback-search').value.trim().toLocaleLowerCase(appLocale()),kind=$('feedback-kind').value,status=$('feedback-state').value;
 const rows=feedbackItems.filter(item=>(kind==='all'||item.kind===kind)&&(status==='all'||item.state===status)&&('#'+item.number+' '+item.title).toLocaleLowerCase(appLocale()).includes(query));
 $('feedback-list').replaceChildren();
 for(const item of rows){const row=document.createElement('li'),title=document.createElement('span'),meta=document.createElement('span');title.textContent='#'+item.number+' '+item.title;meta.textContent=(item.kind==='bug'?ui('Bug'):item.kind==='wish'?ui('Wens'):ui('Overig'))+' · '+feedbackState(item.state);row.append(title,meta);$('feedback-list').append(row);}
 if(!rows.length){const row=document.createElement('li');row.textContent=ui('Geen meldingen voor deze filters.');$('feedback-list').append(row);}
 $('feedback-mine').replaceChildren();
 for(const item of feedbackMine){const row=document.createElement('li'),title=document.createElement('span'),meta=document.createElement('span');title.textContent=(item.number?'#'+item.number+' ':'')+item.title;meta.textContent=feedbackState(item.state);row.append(title,meta);$('feedback-mine').append(row);}
 if(!feedbackMine.length){const row=document.createElement('li');row.textContent=ui('Je hebt hier nog geen meldingen ingediend.');$('feedback-mine').append(row);}
}
async function loadFeedback(){
 if(!accessSession?.user||feedbackBusy)return;
 feedbackBusy=true;const generation=feedbackGeneration;$('feedback-refresh').disabled=true;
 try{const response=await apiFetch('api/feedback');const data=await response.json();if(generation!==feedbackGeneration||!accessSession?.user)return;if(!response.ok)throw Error(data.error);feedbackItems=data.issues;feedbackMine=data.mine||[];renderFeedback();$('feedback-new').disabled=!data.connected;$('feedback-connect-open').hidden=!(data.configured&&!data.connected&&data.can_connect&&accessSession.user.role==='admin'&&currentProfile!=='demo');$('feedback-connection').textContent=data.connected?ui('Verbonden met de meldservice. Meldingen zijn openbaar; deel geen persoonlijke gegevens.'):data.configured?ui('De beheerder moet de meldservice eerst activeren.'):ui('De centrale meldservice is nog niet ingesteld.');$('feedback-status').textContent=data.checked_at?ui('Bijgewerkt:')+' '+new Date(data.checked_at).toLocaleString(appLocale())+(data.limited?' · '+ui('De 100 recent bijgewerkte meldingen worden getoond.'):''):ui('De lijst wordt op de achtergrond bijgewerkt.');}
 catch(error){if(generation===feedbackGeneration)$('feedback-status').textContent=error.message;}
 finally{feedbackBusy=false;$('feedback-refresh').disabled=false;}
}
function feedbackRequestId(){
 if(crypto.randomUUID)return crypto.randomUUID();
 const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
 const hex=[...bytes].map(value=>value.toString(16).padStart(2,'0')).join('');return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
function bindFeedback(){
 registerPopup('feedback-editor',ui('Nieuwe melding'));registerPopup('feedback-connect-editor',ui('Meldservice activeren'));
 $('feedback-new').addEventListener('click',()=>openPopup('feedback-editor'));
 $('feedback-cancel').addEventListener('click',()=>closePopup('feedback-editor'));
 $('feedback-connect-open').addEventListener('click',()=>openPopup('feedback-connect-editor'));
 $('feedback-connect-cancel').addEventListener('click',()=>closePopup('feedback-connect-editor'));
 $('feedback-refresh').addEventListener('click',loadFeedback);
 for(const id of ['feedback-search','feedback-kind','feedback-state'])$(id).addEventListener('input',renderFeedback);
 $('feedback-form').addEventListener('input',()=>{$('feedback-form').dataset.requestId='';});
 $('feedback-form').addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target;if(!form.reportValidity())return;const button=form.querySelector('button[type=submit]');button.disabled=true;const generation=feedbackGeneration;
  try{const data=Object.fromEntries(new FormData(form));data.public_consent=form.elements.public_consent.checked;data.request_id=form.dataset.requestId||(form.dataset.requestId=feedbackRequestId());await jsonAction('api/feedback/submit',data);if(generation!==feedbackGeneration)return;form.reset();form.dataset.requestId='';closePopup('feedback-editor');await loadFeedback();$('feedback-status').textContent=ui('Melding lokaal opgeslagen. Verzending gaat automatisch verder, ook na een herstart.');}
  catch(error){if(generation===feedbackGeneration)$('feedback-form-status').textContent=error.message;}
  finally{button.disabled=false;}
 });
 $('feedback-connect-form').addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target,button=form.querySelector('button[type=submit]');button.disabled=true;const generation=feedbackGeneration;
  try{await jsonAction('api/feedback/connect',{code:form.elements.code.value});if(generation!==feedbackGeneration)return;form.reset();closePopup('feedback-connect-editor');await loadFeedback();}
  catch(error){if(generation===feedbackGeneration)$('feedback-connect-status').textContent=error.message;}
  finally{button.disabled=false;}
 });
 setInterval(()=>{if(!document.hidden&&location.hash.split('?')[0]==='#feedback'&&accessSession?.user)loadFeedback();},30000);
}
