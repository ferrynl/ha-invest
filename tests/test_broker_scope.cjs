const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const pending=[];const rendered=[];
const feedback={textContent:''};
const context=vm.createContext({state:{},currentBroker:'1',accessSession:{user:{role:'basic'}},$:()=>feedback,
 apiFetch:url=>new Promise(resolve=>pending.push({url,resolve})),rendered,refreshCategoryOverview(){}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../portfolio/app/static/stocks.js'),'utf8'),context);
vm.runInContext('renderStocksRows=()=>rendered.push(stocksData);renderStockComposition=()=>{};',context);
const respond=(request,account)=>request.resolve({ok:true,json:async()=>({account_id:account,positions:[{symbol:account}]})});
(async()=>{
 // A change can happen before the replacement request starts; the old scope
 // must not render even when its request generation is still the most recent.
 const old=context.loadStocksDashboard();assert.equal(pending[0].url,'api/stocks?account_id=1');
 context.currentBroker='2';respond(pending.shift(),'1');await old;assert.equal(rendered.length,0);
 const slow=context.loadStocksDashboard();assert.equal(pending[0].url,'api/stocks?account_id=2');
 context.currentBroker='1';const latest=context.loadStocksDashboard();
 respond(pending[1],'1');await latest;respond(pending[0],'2');await slow;
 assert.equal(rendered.length,1);assert.equal(rendered[0].account_id,'1');
 assert.equal(feedback.textContent,'');
 console.log('Broker scope checks passed (scoped request and out-of-order responses)');
})().catch(error=>{console.error(error);process.exitCode=1;});
