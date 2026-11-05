const assert=require('node:assert/strict');
const {homeKey,homeReturn,homeSummary,homeRows,homeDailyMovers}=require('../portfolio/app/static/home.js');
const position=(name,extra={})=>({account_id:1,name,symbol:name,exchange:'AMSTERDAM',account_name:'Broker',currency:'EUR',quantity:'1',cost:'100',value:'120',dividend:'2',total_gain:'22',history:[{invested:'100'}],...extra});
const a=position('Alpha'),b=position('Beta',{value:null,total_gain:null}),c=position('Closed',{quantity:'0',cost:'0',value:'0',total_gain:'30',history:[{invested:'200'}]});
assert.equal(homeReturn(c),15); // Original invested capital, not remaining cost.
assert.equal(homeReturn(b),null);
assert.equal(homeReturn(position('Zero',{history:[{invested:'0'}]})),null);
assert.deepEqual(homeSummary([a,b,c]),{value:120,cost:200,gain:52,dividend:6,missing:1,open:2});
assert.deepEqual(homeRows([a,b,c],'','all','value').map(p=>p.name),['Alpha','Closed','Beta']);
assert.deepEqual(homeRows([a,b,c],'','all','loss').map(p=>p.name),['Closed','Alpha','Beta']);
assert.equal(homeRows([a,b,c],'broker','open','name').length,2);
assert.deepEqual(homeRows([a,b,c],'beta','missing','value'),[b]);
assert.equal(homeRows([a,b,c],'','winners','value').length,2);
assert.equal(homeRows([a,b,c],'','losers','value').length,0);
assert.notEqual(homeKey(a),homeKey({...a,account_id:2}));
const many=Array.from({length:125},(_,i)=>position('Test '+i,{value:String(i+1)}));
assert.equal(homeRows(many,'','open','value')[0].value,'125');
assert.equal(many[0].value,'1'); // Sorting must not mutate the server snapshot.
assert.equal(homeKey({...a,currency:'EUR',native_currency:'USD'}),homeKey({...a,currency:'USD'}));
assert.notEqual(homeKey({...a,currency:'EUR',native_currency:'USD'}),homeKey(a));
const day='2026-11-05';
const mover=(name,percent,extra={})=>position(name,{daily_move:{day,percent},...extra});
const movers=[mover('Alpha','2'),mover('Alpha','2',{account_id:2}),mover('Alpha','3',{exchange:'XETRA'}),
 mover('Bravo','-5'),mover('Charlie','-1',{currency:'USD'}),mover('Closed','10',{quantity:'0'}),
 mover('Stale','20',{daily_move:{day:'2026-11-04',percent:'20'}}),mover('Flat','0')];
const all=homeDailyMovers(movers,'ALL',day);
assert.deepEqual(all.gainers.map(row=>row.change),[3,2]);
assert.deepEqual(all.losers.map(row=>row.change),[-5,-1]);
assert.deepEqual(homeDailyMovers(movers,'EUR',day).losers.map(row=>row.change),[-5]);
assert.equal(homeDailyMovers(Array.from({length:8},(_,i)=>mover(String(i),i+1)),'ALL',day).gainers.length,5);
console.log('Home portfolio and daily movers checks passed');
