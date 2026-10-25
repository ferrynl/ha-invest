/* Language is the only browser preference stored here; portfolio and session data stay off browser storage. */
let currentLanguage=document.documentElement.dataset.accountLanguage||'nl';
function browserLanguage(){
 try{const saved=localStorage.getItem('homeinvest.language');if(['nl','en','es'].includes(saved))return saved;}catch{}
 const saved=document.cookie.split('; ').find(value=>value.startsWith('homeinvest_language='))?.split('=')[1];
 return ['nl','en','es'].includes(saved)?saved:null;
}
if(!document.documentElement.dataset.accountLanguage)currentLanguage=browserLanguage()||'nl';
function appLocale(){return {nl:'nl-NL',en:'en-GB',es:'es-ES'}[currentLanguage];}
function ui(source,parameters={}){
 if(typeof source!=='string')return source;
 const key=source.trim(),entry=UI_TRANSLATIONS[key];
 const translated=entry?source.replace(key,()=>entry[currentLanguage]):source;
 return translated.replace(/\{(\w+)\}/g,(match,name)=>Object.hasOwn(parameters,name)?String(parameters[name]):match);
}
globalThis.HomeInvestTranslate=ui;
// Capture only original interface markup. Never traverse user/provider data added later.
const languageMarkup=[];
const languageWalker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(languageWalker.nextNode()){
 const node=languageWalker.currentNode;
 if(!node.parentElement.closest('script,style,code,pre,option[lang]')&&UI_TRANSLATIONS[node.textContent.trim()]){
  if(node.parentElement.tagName==='OPTION'&&!node.parentElement.hasAttribute('value'))node.parentElement.value=node.parentElement.textContent;
  languageMarkup.push([node,null,node.textContent]);
 }
}
for(const element of document.querySelectorAll('[title],[placeholder],[aria-label]'))for(const name of ['title','placeholder','aria-label']){
 const source=element.getAttribute(name);if(source&&UI_TRANSLATIONS[source.trim()])languageMarkup.push([element,name,source]);
}
function applyLanguage(language){
 currentLanguage=language;document.documentElement.lang=language;
 for(const [node,attribute,source] of languageMarkup){if(attribute)node.setAttribute(attribute,ui(source));else node.textContent=ui(source);}
 document.title=ui('Home')+' · Home Invest';
}
function rememberLanguage(language){
 try{localStorage.setItem('homeinvest.language',language);}catch{}
 // A harmless preference cookie also supports browsers that block localStorage.
 const path=new URL('.',location.href).pathname;
 document.cookie='homeinvest_language='+language+'; Path='+path+'; Max-Age=31536000; SameSite=Lax';
}
let languageUser=null,firstLanguageChoice=null;
async function initializeLanguage(user){
 languageUser=user;
 const saved=user?.language;
 if(saved&&saved!==currentLanguage){rememberLanguage(saved);location.reload();return new Promise(()=>{});}
 if(saved)return;
 const browserChoice=browserLanguage();
 if(['nl','en','es'].includes(browserChoice)){
  if(user)await jsonAction('api/account/language',{language:browserChoice});
  return;
 }
 await new Promise(resolve=>{firstLanguageChoice=resolve;openLanguageDialog(true);});
}
function openLanguageDialog(first=false){
 document.getElementById('language-choice').value=currentLanguage;
 document.getElementById('language-cancel').hidden=first;
 document.getElementById('language-feedback').textContent='';
 document.getElementById('language-dialog').showModal();
}
document.getElementById('language-open').addEventListener('click',()=>openLanguageDialog());
document.getElementById('language-cancel').addEventListener('click',()=>document.getElementById('language-dialog').close());
document.getElementById('language-dialog').addEventListener('cancel',event=>{if(firstLanguageChoice)event.preventDefault();});
document.getElementById('language-form').addEventListener('submit',async event=>{
 event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;
 try{
  const language=document.getElementById('language-choice').value;
  if(languageUser)await jsonAction('api/account/language',{language});
  rememberLanguage(language);
  if(language!==currentLanguage){location.reload();return;}
  document.getElementById('language-dialog').close();
  if(firstLanguageChoice){const resolve=firstLanguageChoice;firstLanguageChoice=null;resolve();}
 }catch(error){document.getElementById('language-feedback').textContent=ui(error.message);}finally{button.disabled=false;}
});
applyLanguage(currentLanguage);
