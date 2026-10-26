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
