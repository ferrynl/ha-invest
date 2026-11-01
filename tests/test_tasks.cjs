const assert=require('node:assert/strict');
const {etfTaskSummary}=require('../portfolio/app/static/tasks.js');
assert.deepEqual(etfTaskSummary(['ready','queued','running','success','partial','waiting','skipped','error','unsupported','interrupted','cancelled'].map(status=>({status}))),{total:11,done:8,success:2,failed:3});
assert.deepEqual(etfTaskSummary([]),{total:0,done:0,success:0,failed:0});
console.log('ETF task progress checks passed.');
