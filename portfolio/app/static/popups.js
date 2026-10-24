/* Every persistent change is made in a modal; filters stay on the page. */
const appPopups=new Map();
function closePopup(id){const popup=appPopups.get(id);if(popup?.dialog.open)popup.dialog.close();if(popup?.panel)popup.panel.hidden=true;}
function closeAllPopups(){for(const dialog of document.querySelectorAll('dialog[open]'))dialog.close();}
function openPopup(id){
 const popup=appPopups.get(id);if(!popup)return;
 if(!popup.dialog.open){closeAllPopups();popup.panel.hidden=false;popup.dialog.showModal();}
 popup.panel.querySelector('input:not([type="hidden"]):not(:disabled),select:not(:disabled),textarea:not(:disabled),button')?.focus();
}
function registerPopup(id,title){
 const panel=$(id),dialog=document.createElement('dialog');dialog.id=id+'-popup';dialog.className='app-popup';
 const bar=document.createElement('div');bar.className='popup-bar';const caption=document.createElement('h2');caption.id=id+'-popup-title';caption.textContent=title;bar.append(caption);
 const close=document.createElement('button');close.type='button';close.className='popup-close secondary';close.textContent='Sluiten';close.setAttribute('aria-label',title+' sluiten');close.addEventListener('click',()=>closePopup(id));bar.append(close);dialog.append(bar,panel);dialog.setAttribute('aria-labelledby',caption.id);document.body.append(dialog);
 panel.hidden=true;appPopups.set(id,{panel,dialog});
 dialog.addEventListener('close',()=>{panel.hidden=true;if(id==='transaction-editor')editingTransaction=null;if(id==='settings-form-editor'){settingsDirty=false;if(state)$('settings-form').elements.namedItem('default_range').value=state.settings.default_range;}panel.querySelectorAll('input[type="password"]').forEach(input=>{input.value='';});});
 return dialog;
}
function formPopup(id,title,label,feedbackIds=[]){
 const form=$(id),button=document.createElement('button'),panel=document.createElement('section');panel.id=id+'-editor';panel.className='popup-content';
 button.type='button';button.className='popup-launch';button.textContent=label;button.id=id+'-open';button.hidden=form.hidden;form.before(button);panel.append(form);for(const feedback of feedbackIds){const note=$(feedback);if(note)panel.append(note);}
 document.body.append(panel);registerPopup(panel.id,title);
 new MutationObserver(()=>{button.hidden=form.hidden;if(form.hidden)closePopup(panel.id);}).observe(form,{attributes:true,attributeFilter:['hidden']});
 button.addEventListener('click',()=>{if(id==='user-form')newUser();openPopup(panel.id);});
 const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='Annuleren';cancel.addEventListener('click',()=>closePopup(panel.id));form.append(cancel);
}
function bindPopups(){
 registerPopup('import-api-report','Trading 212-rapport ophalen');
 registerPopup('stock-valuation-editor','Koers instellen');
 registerPopup('stock-category-editor','Categorieën aanpassen');
 registerPopup('transaction-editor','Transactie bekijken en wijzigen');
 registerPopup('mapping-edit','Aandelenkoppeling aanpassen');
 registerPopup('issue-editor','Importregel aanpassen');
 const deletePanel=$('delete-settings'),placeholder=document.createElement('section');placeholder.className='panel';const heading=document.createElement('h2');heading.textContent='Portefeuillegegevens verwijderen';const text=document.createElement('p');text.textContent='Verwijder alles of één brokeraccount. Het overzicht, de bevestiging en de herstelback-up staan in de pop-up.';const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='Verwijderen instellen';button.addEventListener('click',()=>openPopup('delete-settings'));placeholder.append(heading,text,button);deletePanel.before(placeholder);registerPopup('delete-settings','Portefeuillegegevens verwijderen');
 for(const [id,title,label,feedback] of [
  ['import-form','Transactiehistorie importeren','CSV importeren',['import-source-help','import-account-help','import-upload-feedback']],
  ['purchase','Aankoop toevoegen','Aankoop toevoegen',['feedback','search-status']],
  ['dividend-form','Dividend boeken','Dividend toevoegen',['dividend-feedback']],
  ['broker-form','Brokeraccount toevoegen','Brokeraccount toevoegen',['broker-feedback']],
  ['settings-form','Dashboardinstellingen aanpassen','Dashboard aanpassen',['settings-feedback']],
  ['user-form','Gebruiker toevoegen of wijzigen','Gebruiker toevoegen',['users-feedback']],
  ['enable-auth','Gebruikersbeveiliging inschakelen','Beveiliging inschakelen',[]],
  ['disable-auth','Gebruikersbeveiliging uitschakelen','Beveiliging uitschakelen',[]],
  ['restore-form','Portefeuille herstellen','Back-up terugzetten',['restore-feedback']],
  ['t212-connection','Trading 212-verbinding aanpassen','API-verbinding aanpassen',['t212-connection-feedback']]
 ])formPopup(id,title,label,feedback);
 $('user-cancel').addEventListener('click',()=>closePopup('user-form-editor'));
}
