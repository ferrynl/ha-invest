const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'../portfolio/app/static');
const nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',disabled:false,events:{},addEventListener(name,handler){this.events[name]=handler;}});return nodes.get(id);};
let attempts=0,mode='timeout';const signal={};
const context=vm.createContext({$:element,globalThis:{},accessSession:{user:{role:'admin'}},openPopup(){},AbortSignal:{timeout(ms){assert.equal(ms,60000);return signal;}},
 apiFetch:async()=>({ok:true,json:async()=>({account_id:2,label:'Rekening',revision:'revision',counts:{}})}),
 jsonAction:async(url,data,options)=>{attempts++;assert.equal(url,'api/accounts/delete');assert.equal(options.signal,signal);if(mode==='timeout'){const error=new Error('timeout');error.name='TimeoutError';throw error;}throw Error('Administratie is bezet.');}});
vm.runInContext(fs.readFileSync(path.join(root,'brokers.js'),'utf8'),context);
(async()=>{
 context.bindBrokerManagement();await context.openBrokerDeletion(2);element('broker-delete-confirm').value='VERWIJDEREN';
 await element('broker-delete-form').events.submit({preventDefault(){}});
 assert.match(element('broker-delete-feedback').textContent,/Geen bevestiging/);assert.equal(element('broker-delete-submit').disabled,true);
 await element('broker-delete-form').events.submit({preventDefault(){}});assert.equal(attempts,1,'An uncertain result must not allow a blind retry.');
 mode='busy';await context.openBrokerDeletion(2);element('broker-delete-confirm').value='VERWIJDEREN';await element('broker-delete-form').events.submit({preventDefault(){}});
 assert.equal(element('broker-delete-feedback').textContent,'Administratie is bezet.');assert.equal(element('broker-delete-submit').disabled,false);
 const access=vm.createContext({window:{fetch(){}},globalThis:{}});vm.runInContext(fs.readFileSync(path.join(root,'access.js'),'utf8'),access);
 let received;access.apiFetch=async(url,options)=>{received=options;return {ok:true,json:async()=>({ok:true})};};await access.jsonAction('api/accounts/delete',{id:2},{signal});assert.equal(received.signal,signal);assert.equal(received.method,'POST');
 console.log('Broker deletion timeout, safe retry and request signal checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
