/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
/* Session credentials stay in HttpOnly cookies; only the CSRF token is in memory. */
let currentProfile=typeof location!=='undefined'&&new URLSearchParams(location.search).get('profile')==='demo'?'demo':'personal';
let accessSession=null,stateETag=null,stateETagUrl='';
const nativeFetch=window.fetch.bind(window);
async function apiFetch(url,options={}){
 const finish=options.background?()=>{}:beginPageLoading(),controller=(!options.signal&&(!options.method||options.method==='GET'))?new AbortController():null;
 const timer=controller?setTimeout(()=>controller.abort(),30000):null;
 try{
  const headers=new Headers(options.headers??{});
  headers.set('X-HomeInvest-Language',currentLanguage);headers.set('X-HomeInvest-Profile',currentProfile);
  if(options.method==='POST'&&accessSession?.user?.csrf)headers.set('X-CSRF-Token',accessSession.user.csrf);
  if(url.startsWith('api/state')&&stateETag&&stateETagUrl===url)headers.set('If-None-Match',stateETag);
  const response=await nativeFetch(url,{...options,headers,signal:options.signal||controller?.signal,cache:'no-store'});
  if(response.status===401){lockApp();throw Error(ui('Je sessie is verlopen. Meld je opnieuw aan.'));}
  // Include body parsing in the loading state; each response is parsed only once.
  if(response.status!==304&&response.status!==204&&response.headers.get('Content-Type')?.includes('application/json')){const data=await response.json();response.json=async()=>data;}
  if(url.startsWith('api/state')&&response.ok){stateETag=response.headers.get('ETag');stateETagUrl=url;}
  return response;
 }finally{if(timer!==null)clearTimeout(timer);finish();}
}
// Passkeys use only standard browser WebAuthn APIs. No external JavaScript/CDN.
function passkeySupported(){
 return Boolean(window.isSecureContext&&window.PublicKeyCredential&&navigator.credentials?.create&&navigator.credentials?.get);
}
function b64urlDecode(value){
 const s=value.replace(/-/g,'+').replace(/_/g,'/');
 const binary=atob(s+'='.repeat((4-s.length%4)%4));
 return Uint8Array.from(binary,c=>c.charCodeAt(0));
}
function b64urlEncode(bytes){
 const view=new Uint8Array(bytes);
 let binary='';for(const byte of view)binary+=String.fromCharCode(byte);
 return btoa(binary).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
}
function passkeyCreateOptions(options){
 return {...options,challenge:b64urlDecode(options.challenge),
  user:{...options.user,id:b64urlDecode(options.user.id)},
  excludeCredentials:(options.excludeCredentials||[]).map(x=>({...x,id:b64urlDecode(x.id)}))};
}
function passkeyGetOptions(options){
 return {...options,challenge:b64urlDecode(options.challenge),
  allowCredentials:(options.allowCredentials||[]).map(x=>({...x,id:b64urlDecode(x.id)}))};
}
function passkeyJSON(credential){
 if(typeof credential.toJSON==='function')return credential.toJSON();
 const response=credential.response;
 const result={id:credential.id,rawId:b64urlEncode(credential.rawId),type:credential.type,
  authenticatorAttachment:credential.authenticatorAttachment,
  clientExtensionResults:credential.getClientExtensionResults(),response:{}};
 for(const key of ['clientDataJSON','attestationObject','authenticatorData','signature','userHandle']){
  if(response[key]!=null)result.response[key]=b64urlEncode(response[key]);
 }
 return result;
}
async function passkeyPost(path,data){
 const response=await apiFetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},
  body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error||ui('Passkey-aanvraag mislukt.'));
 return result;
}
async function passkeySignIn(){
 const status=$('login-feedback');
 status.textContent='';
 try{
  const begin=await passkeyPost('api/passkey/login/begin',{});
  const credential=await navigator.credentials.get({publicKey:passkeyGetOptions(begin.options)});
  if(!credential)throw Error(ui('Passkey-aanmelding geannuleerd.'));
  await passkeyPost('api/passkey/login/finish',{ceremony_id:begin.ceremony_id,credential:passkeyJSON(credential)});
  await startSession();
 }catch(error){status.textContent=error.name==='NotAllowedError'?ui('Passkey-aanmelding geannuleerd of niet toegestaan.'):error.message;}
}
async function loadPasskeys(){
 const list=$('passkey-list');
 if(!accessSession?.enabled||!accessSession.user?.id){list.replaceChildren();return;}
 const response=await apiFetch('api/passkeys');
 if(!response.ok)throw Error(ui('Passkeys ophalen mislukt.'));
 const data=await response.json();list.replaceChildren();
 if(!data.passkeys.length){const p=document.createElement('p');p.textContent=ui('Nog geen passkeys toegevoegd.');list.append(p);return;}
 for(const key of data.passkeys){
  const line=document.createElement('div');line.className='passkey-row';
  const label=document.createElement('span');label.textContent=key.label;
  const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=ui('Verwijderen');
  button.addEventListener('click',async()=>{
   const password=prompt(ui('Bevestig met je huidige wachtwoord om deze passkey te verwijderen.'));
   if(password===null)return;
   try{await passkeyPost('api/passkey/delete',{id:key.id,password});await loadPasskeys();$('passkey-feedback').textContent=ui('Passkey verwijderd.');}
   catch(error){$('passkey-feedback').textContent=error.message;}
  });
  line.append(label,button);list.append(line);
 }
}
function bindPasskeys(){
 const supported=passkeySupported();
 $('passkey-login').disabled=!supported;
 $('passkey-unavailable').hidden=supported;
 $('passkey-login').addEventListener('click',passkeySignIn);
 $('passkey-create-form').addEventListener('submit',async(event)=>{
  event.preventDefault();const form=event.currentTarget;const button=form.querySelector('button');button.disabled=true;
  try{
   const fields=Object.fromEntries(new FormData(form));
   const begin=await passkeyPost('api/passkey/register/begin',{password:fields.password});
   const credential=await navigator.credentials.create({publicKey:passkeyCreateOptions(begin.options)});
   if(!credential)throw Error(ui('Passkey registreren geannuleerd.'));
   await passkeyPost('api/passkey/register/finish',{ceremony_id:begin.ceremony_id,
     credential:passkeyJSON(credential),label:fields.label});
   form.reset();await loadPasskeys();$('passkey-feedback').textContent=ui('Passkey toegevoegd.');
  }catch(error){$('passkey-feedback').textContent=error.name==='NotAllowedError'?
    ui('Passkey niet toegestaan of geannuleerd. Open Home Invest zo nodig via HTTPS in de browser.'):error.message;}
  finally{button.disabled=false;form.elements.namedItem('password').value='';}
 });
}
function lockApp(){
 if(typeof clearHealthCenter==='function')clearHealthCenter();
 closeAllPopups();
 if(typeof clearDashboardLayout==='function')clearDashboardLayout();
 $('profile-control').hidden=true;$('demo-banner').hidden=true;
 languageUser=null;accessSession=null;stateETag=null;stateETagUrl='';state=null;stateRequest++;
 if(typeof clearCategoryOverview==='function')clearCategoryOverview();
 if(typeof clearTableControls==='function')clearTableControls();
 if(typeof clearStockDetail==='function')clearStockDetail();
 if(typeof clearStocksDashboard==='function')clearStocksDashboard();
 if(typeof clearTransactions==='function')clearTransactions();
 if(typeof clearConversions==='function')clearConversions();
 if(typeof clearHomeDashboard==='function')clearHomeDashboard();
 if(typeof clearDividendDashboard==='function')clearDividendDashboard();
 if(typeof clearETFTasks==='function')clearETFTasks();
 if(typeof clearReports==='function')clearReports();
 if(typeof clearImportIssues==='function')clearImportIssues();
 if(typeof clearImportMappings==='function')clearImportMappings();
 if(typeof clearLogs==='function')clearLogs();
 if(typeof clearFeedback==='function')clearFeedback();
 if(typeof clearBackupFiles==='function')clearBackupFiles();
 for(const id of ['ha-export-status','ha-export-values','ha-export-yaml']){const item=document.getElementById(id);if(item)item.textContent='';}
 if(typeof clearCurrencies==='function')clearCurrencies();
 if(typeof closeMenu==='function')closeMenu();
 document.getElementById('sidebar').inert=false;
 document.body.classList.add('locked');document.body.classList.remove('booting');document.getElementById('login-panel').hidden=false;
 for(const id of ['totals','positions','dividends','chart','chart-days','users-list','report-rows','report-currency','report-metrics'])document.getElementById(id).replaceChildren();
 if(typeof importPreview!=='undefined'){importPreview=null;document.getElementById('import-preview').hidden=true;for(const id of ['import-rows','import-mappings','import-history'])document.getElementById(id).replaceChildren();}
 document.querySelectorAll('input[type="password"]').forEach(input=>{input.value='';});
 const passwordDialog=document.getElementById('password-dialog');if(passwordDialog.open)passwordDialog.close();
 document.getElementById('login-form').reset();
 document.getElementById('account-name').textContent=ui('Niet ingelogd');
 document.getElementById('account-open').hidden=true;
 document.getElementById('password-open').hidden=true;document.getElementById('logout').hidden=true;
 document.getElementById('login-open').hidden=false;document.getElementById('account-hint').textContent=ui('Meld je aan om je portefeuille te openen.');
}
async function startSession(){
 const finish=beginPageLoading();try{
 const response=await nativeFetch('api/session',{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error(ui('Verbinding mislukt.'));
 accessSession=await response.json();
 if(currentProfile==='demo'&&accessSession.user)accessSession.user={...accessSession.user,role:'basic'};
 await initializeLanguage(accessSession.user);
 if(!accessSession.user){lockApp();return;}
 document.body.classList.toggle('demo-profile',currentProfile==='demo');$('demo-banner').hidden=currentProfile!=='demo';$('profile-control').hidden=false;$('profile-select').value=currentProfile;
 document.body.classList.remove('booting','locked');document.getElementById('login-panel').hidden=true;
 const admin=accessSession.user.role==='admin';
 document.querySelector('[data-route="instellingen"]').hidden=!admin;document.querySelector('[data-route="imports"]').hidden=!admin;
 document.querySelector('[data-route="logs"]').hidden=!admin||!accessSession.enabled;
 document.getElementById('password-open').hidden=!accessSession.enabled;document.getElementById('logout').hidden=!accessSession.enabled;
 document.getElementById('login-open').hidden=true;
 document.getElementById('account-hint').textContent=accessSession.enabled?'':ui('Aanmelding via Home Assistant. Accounts inschakelen bij Instellingen.');
 document.getElementById('account-name').textContent=accessSession.user.username;
 document.querySelector('.account-avatar').textContent=accessSession.user.username.slice(0,1).toLocaleUpperCase();
 document.getElementById('account-open').hidden=false;
 document.getElementById('enable-auth').hidden=accessSession.enabled;
 document.getElementById('disable-auth').hidden=!accessSession.enabled;
 document.getElementById('security-status').textContent=accessSession.enabled?ui('Ingeschakeld. Accounts en rollen worden door de server gecontroleerd.'):ui('Uitgeschakeld. Toegang loopt momenteel via Home Assistant.');
 document.getElementById('user-management').hidden=!admin||!accessSession.enabled;
 document.getElementById('passkey-settings').hidden=!accessSession.enabled||!passkeySupported();
 if(accessSession.enabled&&passkeySupported())loadPasskeys().catch(error=>{$('passkey-feedback').textContent=error.message;});
 if(currentProfile==='demo')homeCurrency='ALL';
 const layout=loadDashboardLayout();
 stateETag=null;rangeInitialized=false;showPage();await Promise.all([layout,load()]);
 if(admin&&accessSession?.enabled)await loadUsers();
 }finally{finish();}
}
function requestPassword(label){
 return new Promise(resolve=>{
  const dialog=document.createElement('dialog'),form=document.createElement('form');
  const field=document.createElement('label'),input=document.createElement('input');
  const submit=document.createElement('button'),cancel=document.createElement('button');
  form.method='dialog';input.type='password';input.required=true;input.maxLength=128;
  field.append(label,input);submit.textContent=ui('Bevestigen');submit.value='confirm';
  cancel.type='button';cancel.textContent=ui('Annuleren');cancel.onclick=()=>dialog.close();
  form.append(field,submit,cancel);dialog.append(form);document.body.append(dialog);
  dialog.addEventListener('close',()=>{const value=dialog.returnValue==='confirm'?input.value:null;input.value='';dialog.remove();resolve(value);},{once:true});
  dialog.showModal();input.focus();
 });
}
async function sensitiveHeaders(){
 if(!accessSession?.user?.csrf)return {};
 const password=await requestPassword(ui('Bevestig met je Home Invest-wachtwoord'));
 if(password===null)throw Error(ui('Actie geannuleerd.'));
 return {'X-Confirm-Password':encodeURIComponent(password)};
}
async function jsonAction(path,data,options={}){
 const response=await apiFetch(path,{...options,method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1',...options.headers},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error);return result;
}
async function loadUsers(){
 const response=await apiFetch('api/users');if(!response.ok)throw Error(ui('Gebruikers laden mislukt.'));const data=await response.json();
 $('users-list').replaceChildren();for(const user of data.users){const row=document.createElement('tr');cell(row,user.username);cell(row,user.role);cell(row,user.active?ui('Actief'):ui('Inactief'));const action=cell(row,'');const button=document.createElement('button');button.type='button';button.textContent=ui('Bewerken');button.addEventListener('click',()=>{const form=$('user-form');form.elements.namedItem('id').value=user.id;form.elements.namedItem('username').value=user.username;form.elements.namedItem('username').readOnly=true;form.elements.namedItem('password').value='';form.elements.namedItem('password').required=false;form.elements.namedItem('role').value=user.role;form.elements.namedItem('active').checked=Boolean(user.active);$('users-feedback').textContent=ui('Laat het wachtwoord leeg om het bestaande te behouden.');openPopup('user-form-editor');});action.append(button);$('users-list').append(row);}
}
function newUser(){const form=$('user-form');form.reset();form.elements.namedItem('id').value='';form.elements.namedItem('username').readOnly=false;form.elements.namedItem('password').required=true;}
function switchProfile(profile){
 const target=new URL(location.href);target.searchParams.set('profile',profile);target.hash='home';location.assign(target.href);
}
function bindAccess(){
 $('profile-open').addEventListener('click',()=>$('profile-dialog').showModal());
 $('profile-close').addEventListener('click',()=>$('profile-dialog').close());
 $('profile-select').addEventListener('change',()=>switchProfile($('profile-select').value));
 $('profile-personal').addEventListener('click',()=>switchProfile('personal'));

 bindPasskeys();
 function formAction(id,callback,feedback){$(id).addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;try{await callback(event.target);}catch(error){$(feedback).textContent=error.message;}finally{button.disabled=false;}});}
 formAction('login-form',async form=>{await jsonAction('api/auth/login',Object.fromEntries(new FormData(form)));form.reset();await startSession();},'login-feedback');
 formAction('enable-auth',async form=>{await jsonAction('api/auth/enable',Object.fromEntries(new FormData(form)));form.reset();await startSession();$('security-feedback').textContent=ui('Gebruikersbeveiliging ingeschakeld.');},'security-feedback');
 formAction('disable-auth',async form=>{await jsonAction('api/auth/disable',Object.fromEntries(new FormData(form)));form.reset();await startSession();$('security-feedback').textContent=ui('Uitgeschakeld. Toegang verloopt weer via Home Assistant.');},'security-feedback');
 formAction('user-form',async form=>{const data=Object.fromEntries(new FormData(form));data.active=form.elements.namedItem('active').checked;if(data.id)data.id=Number(data.id);else delete data.id;await jsonAction('api/users',data);newUser();await loadUsers();$('users-feedback').textContent=ui('Gebruiker opgeslagen. Gewijzigde accounts moeten opnieuw aanmelden.');},'users-feedback');
 $('user-cancel').addEventListener('click',newUser);
 $('logout').addEventListener('click',async()=>{try{await jsonAction('api/auth/logout',{});}finally{lockApp();}});
 $('login-open').addEventListener('click',()=>$('login-form').elements.namedItem('username').focus());
 $('password-open').addEventListener('click',()=>{$('password-form').reset();$('password-form').elements.namedItem('username').value=accessSession.user.username;$('password-feedback').textContent='';$('password-dialog').showModal();});
 $('password-cancel').addEventListener('click',()=>$('password-dialog').close());
 formAction('password-form',async form=>{await jsonAction('api/auth/password',Object.fromEntries(new FormData(form)));form.reset();$('password-dialog').close();lockApp();$('login-feedback').textContent=ui('Account aangepast. Meld je opnieuw aan.');},'password-feedback');
 formAction('restore-form',async form=>{
  const file=$('restore-file').files[0];if(!file||file.size>25*1024*1024+64)throw Error(ui('Kies een SQLite-back-up van maximaal 25 MB.'));
  if(!$('restore-confirm').checked)throw Error(ui('Bevestig het terugzetten.'));
  const password=file.name.toLowerCase().endsWith('.hib')?await requestPassword(ui('Wachtwoord van de back-up')):'';
  if(password===null)return;
  const headers={'Content-Type':'application/octet-stream','X-Portfolio-Request':'1','X-Backup-Password':encodeURIComponent(password)};
  const preview=await apiFetch('api/restore-preview',{method:'POST',headers,body:file});
  const summary=await preview.json();if(!preview.ok)throw Error(summary.error);
  if(!window.confirm(restoreSummary(summary)))return;
  const response=await apiFetch('api/restore',{method:'POST',headers:{...headers,...await sensitiveHeaders(),'X-Confirm-Restore':'yes'},body:file});
  const result=await response.json();if(!response.ok)throw Error(result.error);form.reset();stateETag=null;await startSession();$('restore-feedback').textContent=ui('Portefeuille hersteld. Gebruikers en rollen zijn behouden.');if(!accessSession)$('login-feedback').textContent=ui('Portefeuille hersteld. Meld je opnieuw aan.');
 },'restore-feedback');
}
