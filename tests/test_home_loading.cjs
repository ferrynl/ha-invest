const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};}
const elements=new Map();
const element=()=>({textContent:'',children:[],append(...nodes){this.children.push(...nodes)},replaceChildren(...nodes){this.children=[...nodes]}});
let summary=deferred(),chart=deferred(),calls=[];
const context=vm.createContext({console,module:{exports:{}},AbortController,URLSearchParams,Intl,Set,Map,
 state:{data_revision:1},currentBroker:'all',accessSession:{user:{role:'admin'}},stateETag:null,
 document:{body:{classList:{contains:()=>true}},createElement:element,createTextNode:text=>({textContent:text})},
 $:id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id)},
 dayLabel:d=>d,appLocale:()=> 'nl-NL',setTimeout:()=>1,clearTimeout:()=>{},
 apiFetch:(url,options)=>{calls.push({url,options});return url.includes('/history?')?chart.promise:summary.promise;}});
vm.runInContext(fs.readFileSync('portfolio/app/static/home.js','utf8'),context);
vm.runInContext("homeCurrency='ALL';renderHomeDashboard=()=>{};draw=()=>showHomeEuroChartProgress();",context);
const response=data=>({ok:true,json:async()=>data});
(async()=>{
 const pending=vm.runInContext('loadHomeEuro()',context);
 // A harmless state refresh must not discard an otherwise current response.
 context.state={data_revision:1};
 summary.resolve(response({data_revision:1,chart_status:'pending',positions:[{value:'120'}],portfolios:[{history:[{day:'2026-11-02'}]}],fx_dates:[],as_of:'2026-11-02',excluded:[]}));
 await pending;
 assert.equal(vm.runInContext('homeEuro.positions[0].value',context),'120');
 assert.equal(vm.runInContext('homeEuro.chart_status',context),'loading');
 assert.equal(calls.length,2);assert.equal(calls[1].options.background,true);
 // A chart failure must leave the summary available and offer a retry.
 chart.reject(Error('offline'));await new Promise(setImmediate);
 assert.equal(vm.runInContext('homeEuro.chart_status',context),'error');
 assert.equal(vm.runInContext('homeEuro.positions[0].value',context),'120');
 assert(elements.get('chartnote').children.some(n=>typeof n.onclick==='function'));
 // Retry fills the chart, without fetching or replacing the totals again.
 chart=deferred();vm.runInContext("homeEuro.chart_status='pending';showHomeEuroChartProgress();",context);
 chart.resolve(response({data_revision:1,portfolios:[{history:[{day:'2026-11-01'},{day:'2026-11-02'}]}]}));
 await new Promise(setImmediate);
 assert.equal(vm.runInContext('homeEuro.chart_status',context),'ready');
 assert.equal(vm.runInContext('homeEuro.portfolios[0].history.length',context),2);
 assert.equal(calls.filter(c=>!c.url.includes('/history?')).length,1);
 // No late financial response is applied after logout.
 chart=deferred();vm.runInContext("homeEuro.chart_status='pending';showHomeEuroChartProgress();",context);
 context.accessSession=null;chart.resolve(response({data_revision:1,portfolios:[]}));await new Promise(setImmediate);
 assert.equal(vm.runInContext('homeEuro.portfolios.length',context),1);
 // Keep native EUR amounts available if there is no combined summary yet.
 context.accessSession={user:{role:'admin'}};
 context.state={data_revision:2,positions:[{currency:'EUR',value:'10'},{currency:'USD',value:'20'}]};
 vm.runInContext('homeEuro=null;',context);
 summary=deferred();
 const failed=vm.runInContext('loadHomeEuro()',context);
 summary.resolve({ok:false,json:async()=>({error:'Failed',log_id:'test-id'})});
 await failed;
 assert.equal(vm.runInContext('homeScope().length',context),1);
 assert.equal(vm.runInContext('homeScope()[0].currency',context),'EUR');
 assert.equal(vm.runInContext('homeEuroError',context),'Failed · Log-ID test-id');
 summary=deferred();
 const recovered=vm.runInContext('loadHomeEuro()',context);
 summary.resolve(response({data_revision:2,chart_status:'pending',positions:[{currency:'EUR',value:'28'}],fx_dates:[],as_of:'2026-11-02',excluded:[]}));
 await recovered;
 assert.equal(vm.runInContext('homeScope()[0].value',context),'28');
 assert.equal(vm.runInContext('homeEuroError',context),false);
 console.log('Home totals load independently; chart failure, retry and logout guards passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
