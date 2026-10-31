const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
function element(){return {value:'',disabled:false,hidden:false,textContent:'',options:[],replaceChildren(){this.options=[];this.value='';},append(option){this.options.push(option);if(this.options.length===1)this.value=String(option.value);},querySelector(){return get('submit');}};}
function get(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);}
const context=vm.createContext({$:get,document:{createElement:element},state:{accounts:[{id:1,name:'Invest',broker:'Trading 212'},{id:2,name:'Rekening',broker:'Revolut'},{id:3,name:'Tweede',broker:'Revolut'}]},globalThis:{}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../portfolio/app/static/imports.js'),'utf8'),context);
get('import-provider').value='traderepublic';context.refreshImportAccounts();
assert.equal(get('import-account').value,'');assert.equal(get('import-account').options[0].textContent,'Nog geen passende brokerrekening');assert.equal(get('import-account').disabled,true);assert.equal(get('submit').disabled,true);assert.equal(get('import-account-help').hidden,false);
get('import-provider').value='revolut';context.refreshImportAccounts();
assert.deepEqual(get('import-account').options.map(o=>o.value),[2,3]);assert.equal(get('import-account').disabled,false);assert.equal(get('submit').disabled,false);assert.equal(get('import-account-help').hidden,true);
get('import-account').value='3';context.refreshImportAccounts();assert.equal(get('import-account').value,'3');
get('import-provider').value='trading212';context.refreshImportAccounts();assert.equal(get('import-account').value,'1');
console.log('Broker account selection and empty-state checks passed.');
