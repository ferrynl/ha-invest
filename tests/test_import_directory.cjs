
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {test}=require('node:test');

const root=path.join(__dirname,'../portfolio/app/static');
function setup(){
 const nodes=new Map();
 function create(){
  return {
   children:[],value:'',hidden:false,dataset:{},attrs:{},
   replaceChildren(){this.children=[];},append(...elements){this.children.push(...elements);},
   setAttribute(key,value){this.attrs[key]=value;},addEventListener(name,handler){this[name]=handler;},focus(){}
  };
 }
 const get=id=>{if(!nodes.has(id))nodes.set(id,create());return nodes.get(id);};
 const context=vm.createContext({$:get,document:{createElement:create},TextDecoder,TypeError,
  ui:(s,values={})=>s.replace(/\{(\w+)\}/g,(_,key)=>values[key]),globalThis:{},
  state:{accounts:[{id:1,name:'My Saxo',broker:'Saxo'}]},refreshImportAccounts:()=>{}});
 vm.runInContext(fs.readFileSync(path.join(root,'import-directory.js'),'utf8'),context);
 vm.runInContext(`importDirectoryProviders=[
  {id:'saxo',name:'Saxo',formats:['api','csv'],guide:'Saxo documentation'},
  {id:'lynx',name:'LYNX',formats:['xml'],guide:'LYNX documentation'}
 ]`,context);
 return {get,context};
}

test('API and XML filters are applied before showing the broker choices',()=>{
 const {get,context}=setup();
 get('import-format').value='api';
 context.renderImportDirectory();
 const [choice]=get('import-directory').children;
 assert.equal(get('import-directory').children.length,1);
 assert.equal(choice.children[0].textContent,'Saxo');
 assert.equal(choice.children[1].textContent,'API · CSV');
 assert.equal(choice.children[2].textContent,'1 brokeraccount');
 get('import-format').value='xml';
 context.renderImportDirectory();
 get('import-directory').children[0].click();
 assert.equal(get('import-provider').value,'lynx');
 assert.equal(get('import-broker-upload').textContent,'XML importeren');
 assert.equal(get('import-broker-api').hidden,true);
 assert.equal(get('import-broker-detail').hidden,false);
 assert.equal(get('import-directory').children[0].attrs['aria-pressed'],'true');
 get('import-search').value='missing';
 context.renderImportDirectory();
 assert.equal(get('import-directory').children.length,0);
 assert.equal(get('import-directory-status').textContent,'Geen brokers gevonden.');
});

test('broker upload decodes legacy Swedish and Danish export encodings',async()=>{
 const {context}=setup();
 vm.runInContext(fs.readFileSync(path.join(root,'imports.js'),'utf8'),context);
 const input='KØB;Värdepapper';
 const utf16=Buffer.concat([Buffer.from([255,254]),Buffer.from(input,'utf16le')]);
 for(const bytes of [utf16,Buffer.from(input,'utf8'),Buffer.from(input,'latin1')]){
  assert.equal(await context.readBrokerExport({arrayBuffer:async()=>bytes}),input);
 }
});
