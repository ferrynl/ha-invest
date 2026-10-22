const assert=require('node:assert/strict');
const {stockDistribution}=require('../portfolio/app/static/stocks.js');
const positions=[{quantity:'1',categories:{sector:'Technologie'}},{quantity:'2',categories:{sector:'Technologie'}},{quantity:'1',categories:{}},{quantity:'0',categories:{sector:'Energie'}}];
assert.deepEqual(stockDistribution(positions,'sector'),[['Technologie',2],['Niet ingedeeld',1]]);
assert.deepEqual(stockDistribution([], 'country'),[]);
assert.deepEqual(stockDistribution(positions,'asset_type'),[['Niet ingedeeld',3]]);
console.log('Stock distribution checks passed');
