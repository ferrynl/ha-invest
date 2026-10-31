const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function node(value=''){return {value,disabled:false,hidden:false,textContent:'',events:{},addEventListener(name,handler){this.events[name]=handler;},setAttribute(){}};}
const fields={currency:node('EUR'),purchased_on:node('2026-10-12'),price:node('')},nodes={'purchase-eur-tools':node(),'purchase-eur-price':node(),'purchase-eur-status':node(),'purchase-eur-convert':node()};
nodes.purchase={elements:{namedItem:key=>fields[key]},addEventListener(){}};
const requests=[],timers=new Map();let timer=0;
const ctx=vm.createContext({globalThis:{},$:id=>nodes[id],JSON,Number,Intl,AbortController,appLocale:()=> 'en-GB',dayLabel:v=>v,setTimeout:(fn)=>{timers.set(++timer,fn);return timer;},clearTimeout:id=>timers.delete(id),jsonAction:(url,data,options)=>new Promise((resolve,reject)=>requests.push({url,data,options,resolve,reject}))});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../portfolio/app/static/purchase-fx.js'),'utf8'),ctx);
const run=source=>vm.runInContext(source,ctx);
function response(request,converted='12',rate='1.2'){return {from:'EUR',to:request.data.to,requested_on:request.data.day,rate_on:request.data.day,converted,rate};}
(async()=>{
 assert.equal(nodes['purchase-eur-tools'].hidden,true);assert.equal(nodes['purchase-eur-price'].disabled,true);assert.equal(requests.length,0);
 fields.currency.value='USD';run('syncPurchaseFx()');assert.equal(nodes['purchase-eur-tools'].hidden,false);
 nodes['purchase-eur-price'].value='10';const first=run('convertPurchaseEur()');assert.deepEqual(JSON.parse(JSON.stringify(requests[0].data)),{amount:'10',from:'EUR',to:'USD',day:'2026-10-12'});
 nodes['purchase-eur-price'].value='20';run('schedulePurchaseFx()');const second=run('convertPurchaseEur()');requests[1].resolve(response(requests[1],'24'));await second;requests[0].resolve(response(requests[0],'12'));await first;assert.equal(fields.price.value,'24');
 await run('preparePurchaseFx()');assert.equal(requests.length,2);
 fields.purchased_on.value='2026-10-13';run('schedulePurchaseFx()');assert.equal(fields.price.value,'');const changed=run('convertPurchaseEur()');requests[2].resolve(response(requests[2],'25'));await changed;assert.equal(fields.price.value,'25');
 fields.price.value='30';fields.price.events.input();assert.equal(nodes['purchase-eur-price'].value,'');assert.equal(fields.price.value,'30');
 nodes['purchase-eur-price'].value='10';const cancelled=run('convertPurchaseEur()');run('clearPurchaseFx()');requests[3].resolve(response(requests[3],'99'));await cancelled;assert.notEqual(fields.price.value,'99');
 fields.currency.value='GBX';run('syncPurchaseFx()');nodes['purchase-eur-price'].value='10';const pence=run('convertPurchaseEur()');requests[4].resolve(response(requests[4],'800','80'));await pence;assert.equal(fields.price.value,'800');
 nodes['purchase-eur-price'].value='11';run('schedulePurchaseFx()');const failed=run('convertPurchaseEur()');requests[5].reject(Error('missing rate'));await failed;assert.equal(fields.price.value,'');const retry=run('preparePurchaseFx()');requests[6].reject(Error('missing rate'));await assert.rejects(retry);
 const again=run('convertPurchaseEur()');requests[7].resolve(response(requests[7],'88','8'));await again;const forced=run('convertPurchaseEur(true)');assert.equal(requests.length,9);requests[8].resolve(response(requests[8],'99','9'));await forced;assert.equal(fields.price.value,'99');
 console.log('Purchase EUR conversion hides for EUR, preserves exact strings, rejects stale responses and clears invalid conversions.');
})().catch(error=>{console.error(error);process.exitCode=1;});
