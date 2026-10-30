const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
global.appLocale=()=> 'nl-NL';
const {countryLookup,countryDistribution,countryLabelPositions}=require('../portfolio/app/static/country-map.js');
const root=path.join(__dirname,'../portfolio/app/static');
const atlas=JSON.parse(fs.readFileSync(path.join(root,'world-countries.json'),'utf8'));
const lookup=countryLookup(atlas);
for(const [name,code] of [['Verenigde Staten','US'],['USA','US'],['United States','US'],['Estados Unidos','US'],['Nederland','NL'],['NL','NL'],['NLD','NL'],['België','BE'],['Belgie','BE'],['UK','GB'],['Verenigd Koninkrijk','GB'],['Hongkong','HK'],['Singapore','SG'],['Luxemburg','LU']])assert.equal(lookup.get(name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,''))?.code,code,name);
const rows=countryDistribution([{name:'US',value:40},{name:'Verenigde Staten',value:20},{name:'Nederland',value:20},{name:'Onbekend fondsland',value:20},{name:'Fout',value:null},{name:'Japan',value:-2}],atlas);
assert.equal(rows.length,3);assert.equal(rows[0].country.code,'US');assert.equal(rows[0].weight,60);
assert.equal(rows.find(r=>r.country?.code==='NL').weight,20);
assert.equal(rows.find(r=>r.name==='Onbekend fondsland').country,undefined);
assert.equal(rows.reduce((sum,r)=>sum+r.weight,0),100);
assert.equal(countryDistribution([{name:'not a country <script>',value:100}],atlas)[0].name,'not a country <script>');
assert.equal(countryDistribution([{name:'NL',value:0}],atlas).length,0);
assert.ok(atlas.find(c=>c.code==='SG').anchor);assert.ok(atlas.find(c=>c.code==='NL').path.startsWith('M'));
for(const country of atlas){assert.match(country.code,/^[A-Z]{2}$/);assert.ok(fs.existsSync(path.join(root,'flags',country.code.toLowerCase()+'.svg')),country.code);if(country.anchor)assert.ok(country.anchor.every(Number.isFinite));}
const labels=countryLabelPositions(Array.from({length:7},(_,i)=>({key:i,x:185+i,y:100+i})),360,280);
assert.equal(labels.length,7);
for(const label of labels){assert.ok(label.x>=0&&label.x+82<=360);assert.ok(label.y>=0&&label.y+27<=280);}
for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++){const a=labels[i],b=labels[j];assert.ok(a.x+82<=b.x||b.x+82<=a.x||a.y+27<=b.y||b.y+27<=a.y);}
console.log('Country aliases merge correctly, unknown countries retain their weight, flags are local and mobile labels do not overlap.');
