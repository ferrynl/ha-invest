const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.value='';this.type='';this.events={};}
 append(...items){this.children.push(...items);}
 addEventListener(event,action){this.events[event]=action;}
 querySelectorAll(){return this.children.flatMap(child=>child.children||[]).filter(child=>child.dataset?.field);}
}
const rows=new Element('div'),context=vm.createContext({globalThis:{},document:{createElement:tag=>new Element(tag),createTextNode:text=>({text})},$:id=>{assert.equal(id,'transaction-cost-rows');return rows;},Number,Object,JSON,Date,chargeLabels:{COMMISSION:'Transactiekosten',VAT:'Btw'}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../portfolio/app/static/transactions.js'),'utf8'),context);
vm.runInContext("editingTransaction={currency:'EUR'};addTransactionCost({id:12,revision:'current',category:'VAT',amount:'0.123456789123456789',currency:'usd',included_in_net:1,description:'Original'});addTransactionCost({amount:'-0.2'});",context);
const result=JSON.parse(vm.runInContext('JSON.stringify(transactionCostInputs())',context));
assert.deepEqual(result,[{id:12,revision:'current',category:'VAT',amount:'0.123456789123456789',currency:'USD',description:'Original',included_in_net:1},{category:'COMMISSION',amount:'-0.2',currency:'EUR',description:'',included_in_net:0}]);
assert.equal(rows.children[0].children.at(-1).type,'button');
console.log('Transaction cost editor preserves decimal amounts, refunds, source identity, revision and net handling.');
