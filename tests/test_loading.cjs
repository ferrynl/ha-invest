const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');let now=0,route='#home',next=0;const tasks=new Map(),classes=new Set(),listeners={};
const elements={'loading-indicator':{hidden:true},'loading-description':{textContent:''},'main-content':{setAttribute(k,v){this[k]=v;}}};
const context=vm.createContext({location:{get hash(){return route;}},Date:{now:()=>now},document:{body:{classList:{contains:k=>classes.has(k)}},getElementById:id=>elements[id]},window:{addEventListener:(name,fn)=>listeners[name]=fn},setTimeout:(fn,ms)=>{const id=++next;tasks.set(id,{fn,at:now+ms});return id;},clearTimeout:id=>tasks.delete(id)});
vm.runInContext(fs.readFileSync('portfolio/app/static/loading.js','utf8'),context);
function advance(ms){now+=ms;for(const [id,task] of [...tasks])if(task.at<=now){tasks.delete(id);task.fn();}}
let finish=context.beginPageLoading();finish();advance(200);assert.equal(elements['loading-indicator'].hidden,true);
finish=context.beginPageLoading();advance(200);assert.equal(elements['loading-indicator'].hidden,false);assert.equal(elements['main-content']['aria-busy'],'true');
route='#rapporten';listeners.hashchange();assert.equal(elements['loading-indicator'].hidden,true);finish();
const fast=context.beginPageLoading();advance(100);const slow=context.beginPageLoading();fast();advance(90);assert.equal(elements['loading-indicator'].hidden,true);advance(100);assert.equal(elements['loading-indicator'].hidden,false);advance(8000);assert.match(elements['loading-description'].textContent,/langer/);slow();assert.equal(elements['loading-indicator'].hidden,true);
console.log('Loading animation: fast requests, overlap, route changes, long waits and completion passed.');
