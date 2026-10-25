const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.join(__dirname,'../portfolio/app/static');

function browser({account='',saved=null,cookie='',storageBlocked=false}={}){
 const elements=new Map();const preferences=new Map(saved?[['homeinvest.language',saved]]:[]);
 const element=id=>{if(!elements.has(id))elements.set(id,{value:'',hidden:false,textContent:'',disabled:false,events:{},open:false,addEventListener(name,callback){this.events[name]=callback;},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(id);};
 const markup=(text,tag='SPAN')=>{
  const parent={tagName:tag,value:'',hasAttribute:()=>false,textContent:text,
   closest:selector=>selector.split(',').includes('[lang]')?{tagName:'HTML'}:null};
  return {textContent:text,parentElement:parent};
 };
 const label=markup('Je portefeuille'),option=markup('Alles','OPTION'),userText=markup('Aandeel');
 let index=0;
 const document={body:{},cookie,documentElement:{dataset:{accountLanguage:account},lang:'nl'},
  createTreeWalker(){return {nextNode(){this.currentNode=[label,option][index++];return !!this.currentNode;}};},
  querySelectorAll:()=>[],getElementById:element};
 const calls=[];
 const context=vm.createContext({document,URL,NodeFilter:{SHOW_TEXT:4},localStorage:{getItem:key=>{if(storageBlocked)throw Error('blocked');return preferences.get(key)||null;},setItem:(key,value)=>{if(storageBlocked)throw Error('blocked');preferences.set(key,value);}},location:{href:'http://localhost/ingress/test/',reload(){calls.push('reload');}},jsonAction:async(...args)=>calls.push(args)});
 vm.runInContext(fs.readFileSync(path.join(root,'translations.js'),'utf8'),context);
 vm.runInContext(fs.readFileSync(path.join(root,'i18n.js'),'utf8'),context);
 return {context,document,label,option,userText,element,calls,preferences};
}

(async()=>{
 const spanish=browser({account:'es',saved:'en'});
 assert.equal(spanish.document.documentElement.lang,'es','account wins over browser preference');
 assert.equal(spanish.label.textContent,'Tu cartera','initial markup is translated despite html[lang]');
 assert.equal(spanish.option.textContent,'Todo');
 assert.equal(spanish.option.parentElement.value,'Alles','translation must preserve the original option value');
 assert.equal(spanish.userText.textContent,'Aandeel','later user data is never traversed');
 assert.equal(vm.runInContext("ui('  Instellingen  ')",spanish.context),'  Configuración  ');
 assert.equal(vm.runInContext("appLocale()",spanish.context),'es-ES');
 vm.runInContext("UI_TRANSLATIONS['Count {count}']={nl:'Aantal {count}',en:'Count {count}',es:'Cantidad {count}'}",spanish.context);
 assert.equal(vm.runInContext("ui('Count {count}',{count:3})",spanish.context),'Cantidad 3');
 const fallback=browser({storageBlocked:true,cookie:'homeinvest_language=en'});
 assert.equal(fallback.document.documentElement.lang,'en','preference cookie supports blocked localStorage');
 const first=browser();
 const started=vm.runInContext('initializeLanguage(null)',first.context);
 assert.equal(first.element('language-dialog').open,true,'first launch asks for a language');
 assert.equal(first.element('language-cancel').hidden,true);
 let cancelled=false;first.element('language-dialog').events.cancel({preventDefault(){cancelled=true;}});
 assert.equal(cancelled,true,'first launch requires a choice');
 first.element('language-choice').value='nl';
 const button={disabled:false};
 await first.element('language-form').events.submit({preventDefault(){},target:{querySelector:()=>button}});
 await started;
 assert.equal(first.preferences.get('homeinvest.language'),'nl');
 assert.equal(first.element('language-dialog').open,false);
 const returning=browser({saved:'en'});
 await vm.runInContext("initializeLanguage({id:2,language:''})",returning.context);
 assert.equal(returning.calls[0][0],'api/account/language');
 assert.equal(returning.calls[0][1].language,'en');
 console.log('Language UI checks passed (first launch, persistence, source data, locale and placeholders)');
})().catch(error=>{console.error(error);process.exitCode=1;});
