const assert=require('node:assert/strict');
const {stockDistribution}=require('../portfolio/app/static/stocks.js');
const positions=[{quantity:'1',categories:{sector:'Technologie'}},{quantity:'2',categories:{sector:'Technologie'}},{quantity:'1',categories:{}},{quantity:'0',categories:{sector:'Energie'}}];
assert.deepEqual(stockDistribution(positions,'sector'),[['Technologie',2],['Niet ingedeeld',1]]);
assert.deepEqual(stockDistribution([], 'country'),[]);
assert.deepEqual(stockDistribution(positions,'asset_type'),[['Niet ingedeeld',3]]);
console.log('Stock distribution checks passed');

const {stockSectorTheme}=require('../portfolio/app/static/stocks.js');
for(const [a,b] of [['Technologie','Technology'],['Gezondheidszorg','Healthcare'],['Financiële diensten','Financial Services'],['Basismaterialen','Basic Materials'],['Nutsbedrijven','Utilities']])assert.equal(stockSectorTheme(a),stockSectorTheme(b));
assert.notEqual(stockSectorTheme('Technology').icon,stockSectorTheme('Energy').icon);
assert.equal(stockSectorTheme('Mijn eigen sector').note,'Eigen of nog niet ingedeelde sector');
console.log('Sector symbols match Dutch and provider categories and retain a fallback.');
