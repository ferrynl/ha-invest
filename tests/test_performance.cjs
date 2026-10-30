const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const requests=[],timers=[],fields=new Map();
const context=vm.createContext({state:{data_revision:1},currentBroker:'all',accessSession:{user:{}},location:{hash:'#rapporten-performance'},AbortController,
 window:{addEventListener(){}},
 setTimeout:(callback,delay)=>{timers.push({callback,delay});return timers.length;},clearTimeout(){},
 $:id=>{if(!fields.has(id))fields.set(id,{value:'',textContent:'',replaceChildren(){}});return fields.get(id);},
 apiFetch:(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}))});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../portfolio/app/static/reports.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../portfolio/app/static/performance.js'),'utf8'),context);
vm.runInContext("reportType='performance';renderReports=()=>{};",context);
const reply=(request,revision=2)=>request.resolve({ok:true,json:async()=>({data_revision:revision,groups:[]})});
const value=expression=>vm.runInContext(expression,context);
(async()=>{
 // Report and selector list are separate snapshots: a newer quote is valid.
 const first=context.loadPerformance(context.reportHistoryScope());
 assert.equal(timers.at(-1).delay,60000);reply(requests.shift(),2);await first;
 assert.equal(value('performanceData.data_revision'),2);
 assert.equal(value('performanceError'),false);
 // Continuous quote writes must not cause a refresh/retry loop.
 for(let revision=3;revision<=5;revision++){
  const pending=context.loadPerformance(context.reportHistoryScope());reply(requests.shift(),revision);await pending;
  assert.equal(value('performanceData.data_revision'),revision);assert.equal(value('performanceError'),false);
 }
 context.clearPerformance();
 // A filter/account change still discards the previous scope's response.
 const old=context.loadPerformance(context.reportHistoryScope());context.currentBroker='2';reply(requests.shift());await old;
 assert.equal(value('performanceData'),null);
 const slow=context.loadPerformance(context.reportHistoryScope()),slowRequest=requests.shift();
 context.currentBroker='3';const latest=context.loadPerformance(context.reportHistoryScope());reply(requests.shift(),7);await latest;
 reply(slowRequest,6);await slow;assert.equal(value('performanceData.data_revision'),7);
 // A failed or hanging request stops loading and can be retried.
 context.clearPerformance();const hanging=context.loadPerformance(context.reportHistoryScope());const hangingRequest=requests.shift();
 timers.at(-1).callback();await hanging;
 assert.equal(value('performanceRequest'),null);assert.equal(value('performanceError'),true);assert.equal(hangingRequest.options.signal.aborted,true);
 assert.ok(value('performanceErrorDetails').includes('duurde te lang'));
 context.clearPerformance();const retry=context.loadPerformance(context.reportHistoryScope());reply(requests.shift(),8);await retry;
 assert.equal(value('performanceData.data_revision'),8);assert.equal(value('performanceError'),false);
 // Keep an actionable, application-authored server diagnostic reference.
 context.clearPerformance();const failed=context.loadPerformance(context.reportHistoryScope());requests.shift().resolve({ok:false,json:async()=>({error:'Rendementsrapport berekenen mislukt. · Log-ID test-reference'})});await failed;
 assert.equal(value('performanceErrorDetails'),'Rendementsrapport berekenen mislukt. · Log-ID test-reference');
 // Late private data never reappears after logout.
 context.clearPerformance();const logout=context.loadPerformance(context.reportHistoryScope());const late=requests.shift();
 context.accessSession=null;context.clearPerformance();reply(late,9);await logout;
 assert.equal(value('performanceData'),null);assert.equal(value('performanceRequest'),null);
 console.log('Performance loading accepts fresh quote snapshots, rejects stale filters, times out and clears private data on logout.');
})().catch(error=>{console.error(error);process.exitCode=1;});
