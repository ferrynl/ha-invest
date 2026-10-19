/* Session credentials stay in HttpOnly cookies; only the CSRF token is in memory. */
let accessSession=null,stateETag=null;
const nativeFetch=window.fetch.bind(window);
async function apiFetch(url,options={}){
 const headers=new Headers(options.headers??{});
 if(options.method==='POST'&&accessSession?.user?.csrf)headers.set('X-CSRF-Token',accessSession.user.csrf);
 if(url==='api/state'&&stateETag)headers.set('If-None-Match',stateETag);
 const response=await nativeFetch(url,{...options,headers,cache:'no-store'});
 if(url==='api/state'&&response.ok)stateETag=response.headers.get('ETag');
 if(response.status===401){lockApp();throw Error('Je sessie is verlopen. Meld je opnieuw aan.');}
 return response;
}
function lockApp(){
 accessSession=null;stateETag=null;state=null;
 if(typeof closeMenu==='function')closeMenu();
 document.getElementById('sidebar').inert=false;
 document.body.classList.add('locked');document.body.classList.remove('booting');document.getElementById('login-panel').hidden=false;
 for(const id of ['totals','positions','purchases','dividends','chart','chart-days','users-list','report-dividends','report-portfolio'])document.getElementById(id).replaceChildren();
 document.querySelectorAll('input[type="password"]').forEach(input=>{input.value='';});
 const passwordDialog=document.getElementById('password-dialog');if(passwordDialog.open)passwordDialog.close();
 document.getElementById('login-form').reset();
 document.getElementById('account-name').textContent='Niet ingelogd';
 document.getElementById('password-open').hidden=true;document.getElementById('logout').hidden=true;
 document.getElementById('login-open').hidden=false;document.getElementById('account-hint').textContent='Meld je aan om je portefeuille te openen.';
}
async function startSession(){
 const response=await nativeFetch('api/session',{cache:'no-store'});if(!response.ok)throw Error('Verbinding mislukt.');
 accessSession=await response.json();
 if(!accessSession.user){lockApp();return;}
 document.body.classList.remove('booting','locked');document.getElementById('login-panel').hidden=true;
 const admin=accessSession.user.role==='admin';
 document.querySelector('[data-route="instellingen"]').hidden=!admin;
 document.getElementById('password-open').hidden=!accessSession.enabled;document.getElementById('logout').hidden=!accessSession.enabled;
 document.getElementById('login-open').hidden=true;
 document.getElementById('account-hint').textContent=accessSession.enabled?'':'Aanmelding via Home Assistant. Accounts inschakelen bij Instellingen.';
 document.getElementById('account-name').textContent=accessSession.user.username+' · '+accessSession.user.role;
 document.getElementById('enable-auth').hidden=accessSession.enabled;
 document.getElementById('disable-auth').hidden=!accessSession.enabled;
 document.getElementById('security-status').textContent=accessSession.enabled?'Ingeschakeld. Accounts en rollen worden door de server gecontroleerd.':'Uitgeschakeld. Toegang loopt momenteel via Home Assistant.';
 document.getElementById('user-management').hidden=!admin||!accessSession.enabled;
 stateETag=null;rangeInitialized=false;showPage();await load();
 if(admin&&accessSession?.enabled)await loadUsers();
}
async function jsonAction(path,data){
 const response=await apiFetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Request':'1'},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error);return result;
}
async function loadUsers(){
 const response=await apiFetch('api/users');if(!response.ok)throw Error('Gebruikers laden mislukt.');const data=await response.json();
 $('users-list').replaceChildren();for(const user of data.users){const row=document.createElement('tr');cell(row,user.username);cell(row,user.role);cell(row,user.active?'Actief':'Inactief');const action=cell(row,'');const button=document.createElement('button');button.type='button';button.textContent='Bewerken';button.addEventListener('click',()=>{const form=$('user-form');form.elements.namedItem('id').value=user.id;form.elements.namedItem('username').value=user.username;form.elements.namedItem('username').readOnly=true;form.elements.namedItem('password').value='';form.elements.namedItem('password').required=false;form.elements.namedItem('role').value=user.role;form.elements.namedItem('active').checked=Boolean(user.active);$('users-feedback').textContent='Laat het wachtwoord leeg om het bestaande te behouden.';});action.append(button);$('users-list').append(row);}
}
function newUser(){const form=$('user-form');form.reset();form.elements.namedItem('id').value='';form.elements.namedItem('username').readOnly=false;form.elements.namedItem('password').required=true;}
function bindAccess(){
 function formAction(id,callback,feedback){$(id).addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;try{await callback(event.target);}catch(error){$(feedback).textContent=error.message;}finally{button.disabled=false;}});}
 formAction('login-form',async form=>{await jsonAction('api/auth/login',Object.fromEntries(new FormData(form)));form.reset();await startSession();},'login-feedback');
 formAction('enable-auth',async form=>{await jsonAction('api/auth/enable',Object.fromEntries(new FormData(form)));form.reset();await startSession();$('security-feedback').textContent='Gebruikersbeveiliging ingeschakeld.';},'security-feedback');
 formAction('disable-auth',async form=>{await jsonAction('api/auth/disable',Object.fromEntries(new FormData(form)));form.reset();await startSession();$('security-feedback').textContent='Uitgeschakeld. Toegang verloopt weer via Home Assistant.';},'security-feedback');
 formAction('user-form',async form=>{const data=Object.fromEntries(new FormData(form));data.active=form.elements.namedItem('active').checked;if(data.id)data.id=Number(data.id);else delete data.id;await jsonAction('api/users',data);newUser();await loadUsers();$('users-feedback').textContent='Gebruiker opgeslagen. Gewijzigde accounts moeten opnieuw aanmelden.';},'users-feedback');
 $('user-cancel').addEventListener('click',newUser);
 $('logout').addEventListener('click',async()=>{try{await jsonAction('api/auth/logout',{});}finally{lockApp();}});
 $('login-open').addEventListener('click',()=>$('login-form').elements.namedItem('username').focus());
 $('password-open').addEventListener('click',()=>{$('password-form').reset();$('password-form').elements.namedItem('username').value=accessSession.user.username;$('password-feedback').textContent='';$('password-dialog').showModal();});
 $('password-cancel').addEventListener('click',()=>$('password-dialog').close());
 formAction('password-form',async form=>{await jsonAction('api/auth/password',Object.fromEntries(new FormData(form)));form.reset();$('password-dialog').close();lockApp();$('login-feedback').textContent='Account aangepast. Meld je opnieuw aan.';},'password-feedback');
 formAction('restore-form',async form=>{
  const file=$('restore-file').files[0];if(!file||file.size>25*1024*1024)throw Error('Kies een SQLite-back-up van maximaal 25 MB.');
  if(!$('restore-confirm').checked)throw Error('Bevestig het terugzetten.');
  const response=await apiFetch('api/restore',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Portfolio-Request':'1','X-Confirm-Restore':'yes'},body:file});
  const result=await response.json();if(!response.ok)throw Error(result.error);form.reset();stateETag=null;await startSession();$('restore-feedback').textContent='Portefeuille hersteld. Gebruikers en rollen zijn behouden.';if(!accessSession)$('login-feedback').textContent='Portefeuille hersteld. Meld je opnieuw aan.';
 },'restore-feedback');
}
