const assert=require('node:assert/strict'),{reportRows,reportData}=require('../portfolio/app/static/reports.js');
const p={symbol:'AAA',exchange:'AMS',currency:'EUR',name:'Alpha',cost:'100',value:'120',realised:'5',dividend:'3'};
const positions=[p,{...p,cost:'50',value:null},{...p,currency:'USD',value:'200'}];
let rows=reportRows(positions,[],'portfolio','2026','','');assert.equal(rows.length,2);assert.equal(rows[0].cost,100);assert.equal(rows[0].value,120);assert.equal(rows[1].currency,'USD');
assert.equal(reportRows(positions,[],'stocks','2026','','EUR').length,1);
const dividends=[{...p,paid_on:'2026-01-12',amount:'4'},{...p,paid_on:'2026-02-12',amount:'6'},{...p,paid_on:'2025-01-12',amount:'10'},{...p,currency:'USD',paid_on:'2026-01-12',amount:'8'}];
rows=reportRows([],dividends,'income','2026','','EUR');assert.equal(rows[0].dividend,10);assert.equal(rows[0].count,2);
assert.equal(reportRows([],dividends,'months','2026','','').length,3);
assert.deepEqual(reportRows(positions,dividends,'income','2024','',''),[]);
const key=JSON.stringify(['AAA','AMS','EUR']);assert.equal(reportRows(positions,dividends,'stocks','2026',key,'')[0].count,1);
console.log('Report grouping, filters, missing prices and currency separation passed.');

for(const field of ['value','cost','realised','dividend'])for(const bad of [null,undefined,'',' ',NaN,Infinity,'invalid',false]){
 const result=reportData([p,{...p,[field]:bad}],[],'portfolio','2026','','');assert.equal(result.skipped,1);assert.equal(result.rows[0].count,1);assert.equal(result.rows[0].cost,100);
}
assert.equal(reportData([{...p,value:0,cost:'0',realised:'0',dividend:'0'}],[],'stocks','2026','','').rows.length,1);
assert.deepEqual(reportData([{...p,value:null}],[],'stocks','2026','',''),{rows:[],skipped:1});
let result=reportData([], [...dividends,{...dividends[0],amount:null},{...dividends[0],paid_on:'2026-02-30'},{...dividends[0],paid_on:null}], 'income','2026','','EUR');assert.equal(result.skipped,3);assert.equal(result.rows[0].dividend,10);
assert.equal(reportData([{...p,value:null}],dividends,'income','2026','','EUR').rows[0].dividend,10);
assert.equal(reportData([{...p,value:null},{...p,currency:'USD',value:null}],[],'portfolio','2026','','EUR').skipped,1);
assert.equal(reportData([{...p,currency:'???'}],[],'stocks','2026','','').skipped,1);
console.log('Incomplete rows are excluded without affecting valid rows or independent dividends.');

const {reportAnalytics}=require('../portfolio/app/static/reports.js');
const classified=[{...p,categories:{sector:'Technology',country:'NL'}},{...p,symbol:'BBB',value:'80',cost:'100',categories:{sector:'Energy',country:'US'}},{...p,symbol:'CCC',value:null}];
let analytics=reportAnalytics(classified,dividends,'2026');
assert.equal(analytics.skipped,1);
const euro=analytics.groups.find(g=>g.currency==='EUR');
assert.equal(euro.total.value,200);
assert.equal(euro.total.profit,16);
assert.equal(euro.allocation[0].weight,60);
assert.equal(euro.concentration,100);
assert.deepEqual(euro.sectors.map(p=>p.value),[120,80]);
assert.equal(euro.months.length,12);
assert.equal(euro.months[2].value,0);
assert.equal(euro.cumulative.at(-1).value,10);
assert.equal(euro.priorIncome,10);
assert.equal(euro.calendar.find(p=>p.name==='2025-01').value,10);
analytics=reportAnalytics(classified,dividends,'2026',JSON.stringify(['AAA','AMS','EUR']),'EUR');
assert.equal(analytics.groups.length,1);
assert.equal(analytics.groups[0].total.value,120);
assert.equal(analytics.groups[0].annualIncome,10);
assert.equal(reportAnalytics([],dividends,'2026').groups.find(g=>g.currency==='EUR').annualIncome,10);
assert.deepEqual(reportAnalytics([],[],'2026').groups,[]);
console.log('Report analytics: allocation, concentration, categories, cash income and filters passed.');

const {reportCalendarWindow}=require('../portfolio/app/static/reports.js');
assert.deepEqual(reportCalendarWindow([{name:'2019-01'},{name:'2020-01'},{name:'2025-01'},{name:'2026-01'}],'2025').map(p=>p.name),['2020-01','2025-01']);
global.chartPeriodStart=require('../portfolio/app/static/chart.js').chartPeriodStart;
const {reportHistoryWindow}=require('../portfolio/app/static/reports.js');
const sparse={as_of:'2026-10-28',history:[{day:'2026-07-01'},{day:'2026-10-10'}]};
assert.deepEqual(reportHistoryWindow(sparse,'1M').map(p=>p.day),['2026-10-10']);
assert.equal(reportHistoryWindow(sparse,'ALL').length,2);
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const pendingHistory=[],elements=new Map();
const context=vm.createContext({state:{data_revision:1},currentBroker:'1',accessSession:{user:{role:'basic'}},location:{hash:'#rapporten'},stateETag:'old',loads:0,
 $:id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',replaceChildren(){}});return elements.get(id);},
 apiFetch:url=>new Promise(resolve=>pendingHistory.push({url,resolve})),load:async()=>{context.loads++;}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../portfolio/app/static/reports.js'),'utf8'),context);
vm.runInContext("reportType='growth';renderReports=()=>{};",context);
const reply=(request,revision=1)=>request.resolve({ok:true,json:async()=>({data_revision:revision,currencies:[]})});
(async()=>{
 const old=context.loadReportHistory();assert.ok(pendingHistory[0].url.includes('account_id=1'));
 context.currentBroker='2';reply(pendingHistory.shift());await old;
 assert.equal(vm.runInContext('reportHistory',context),null);
 const slow=context.loadReportHistory();context.currentBroker='1';const latest=context.loadReportHistory();
 reply(pendingHistory[1]);await latest;const accepted=vm.runInContext('reportHistory',context);reply(pendingHistory[0]);await slow;
 assert.equal(vm.runInContext('reportHistory',context),accepted);
 pendingHistory.length=0;elements.get('report-stock').value='changed';const stale=context.loadReportHistory();reply(pendingHistory.shift(),2);await stale;assert.equal(context.loads,1);
 context.clearReports();assert.equal(vm.runInContext('reportHistory',context),null);
 console.log('Report history ignores stale scopes and refreshes changed data revisions.');
})().catch(error=>{console.error(error);process.exitCode=1;});
