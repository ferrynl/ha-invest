const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const values={'report-year':{value:'2026'},'report-currency':{value:''}};
const requests=[],context=vm.createContext({globalThis:{},URLSearchParams,JSON,Date,console,document:{},location:{hash:'#rapporten-costs'},currentBroker:'1',state:{data_revision:1},reportType:'costs',accessSession:{user:{role:'admin'}},$:id=>values[id],apiFetch:url=>new Promise(resolve=>requests.push({url,resolve}))});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../portfolio/app/static/charges.js'),'utf8'),context);
vm.runInContext('var renders=0;renderChargeReport=()=>{renders++;};',context);
const read=source=>vm.runInContext(source,context);
(async()=>{
 const first=read('loadChargeReport()');read("currentBroker='2'");const second=read('loadChargeReport()');
 assert.match(requests[0].url,/account_id=1/);assert.match(requests[1].url,/account_id=2/);
 requests[1].resolve({ok:true,json:async()=>({marker:'second-account'})});await second;
 requests[0].resolve({ok:true,json:async()=>({marker:'first-account'})});await first;
 assert.equal(read('chargeData.marker'),'second-account');
 const logout=read('loadChargeReport()');read('clearChargeReport();accessSession=null;');requests[2].resolve({ok:true,json:async()=>({marker:'private'})});await logout;assert.equal(read('chargeData'),null);
 read("accessSession={user:{role:'admin'}};reportType='taxes';");const failed=read('loadChargeReport()');assert.match(requests[3].url,/view=taxes/);requests[3].resolve({ok:false,json:async()=>({error:'test error'})});await failed;
 assert.equal(read('chargeError'),'test error');assert.equal(read('chargePending'),false);
 read('clearChargeReport();');const stale=read('loadChargeReport()');read('state.data_revision=2;');requests[4].resolve({ok:true,json:async()=>({marker:'old revision'})});await stale;assert.equal(read('chargeData'),null);
 console.log('Cost report rejects stale account, logout and revision responses and exposes request failures.');
})().catch(error=>{console.error(error);process.exitCode=1;});
