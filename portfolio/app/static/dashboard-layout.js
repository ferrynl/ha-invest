/* Personal module layout lives on the server; the editor holds only an unsaved draft. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
const dashboardModules=[
 {id:'currencies',title:ui('Valutakeuze'),width:'full'},
 {id:'market',title:ui('Marktwaarde'),width:'quarter'},
 {id:'cost',title:ui('Openstaande kostprijs'),width:'quarter'},
 {id:'gain',title:ui('Totale winst'),width:'quarter'},
 {id:'income',title:ui('Ontvangen dividend'),width:'quarter'},
 {id:'notice',title:ui('Koers- en valuta-informatie'),width:'full'},
 {id:'chart',title:ui('Je portefeuille in beeld'),width:'full'},
 {id:'allocation',title:ui('Grootste posities'),width:'half'},
 {id:'movers',title:ui('Resultaten in beeld'),width:'half'},
 {id:'holdings',title:ui('Je posities'),width:'full'}
];
function defaultDashboardLayout(){return dashboardModules.map(({id,width})=>({id,width,enabled:true}));}
function moveDashboardModule(rows,id,target){
 const result=rows.map(row=>({...row})),index=result.findIndex(row=>row.id===id);
 if(index<0||target<0||target>=result.length)return result;
 const [item]=result.splice(index,1);result.splice(target,0,item);return result;
}
let dashboardLayout=defaultDashboardLayout(),dashboardDraft=[],dashboardLayoutReady=false,dashboardLayoutRequest=0,dashboardDragged=null;
const dashboardNodes=new Map();
function initializeDashboardModules(){
 const home=document.querySelector('[data-page="home"]'),board=document.createElement('div');board.id='home-module-board';board.className='home-module-board';
 $('totals').before(board);
 const insights=home.querySelector('.home-insights');
 const original={currencies:$('home-currencies'),chart:$('home-chart-panel'),allocation:insights.children[0],movers:insights.children[1],holdings:home.querySelector('.home-holdings')};
 const notice=document.createElement('section');notice.append($('home-euro-status'),$('home-health'));original.notice=notice;
 for(const module of dashboardModules){
  const node=original[module.id]||document.createElement('article');
  if(!original[module.id])node.className='home-metric';
  node.id='home-module-'+module.id;node.dataset.module=module.id;node.classList.add('home-module');
  // Existing renderers retain their named targets inside the movable module.
  if(module.id==='currencies'){node.id='home-currencies';}
  if(module.id==='chart'){node.id='home-chart-panel';}
  dashboardNodes.set(module.id,node);board.append(node);
 }
 insights.remove();$('totals').hidden=true;
 const empty=document.createElement('p');empty.id='dashboard-layout-empty';empty.className='home-muted';empty.textContent=ui('Je dashboard is leeg. Kies Dashboard aanpassen om modules aan te zetten.');board.after(empty);
 applyDashboardLayout();
}
function applyDashboardLayout(){
 const board=$('home-module-board');
 for(const row of dashboardLayout){const node=dashboardNodes.get(row.id);node.hidden=!row.enabled;node.dataset.width=row.width;board.append(node);}
 $('dashboard-layout-empty').hidden=dashboardLayout.some(row=>row.enabled);
}
function dashboardModuleEnabled(id){return dashboardLayout.some(row=>row.id===id&&row.enabled);}
function clearDashboardLayout(){dashboardLayoutRequest++;dashboardLayoutReady=false;dashboardLayout=defaultDashboardLayout();dashboardDraft=[];applyDashboardLayout();}
async function loadDashboardLayout(){
 const request=++dashboardLayoutRequest;
 try{
  const response=await apiFetch('api/account/dashboard');if(!response.ok)throw Error();const result=await response.json();
  if(request!==dashboardLayoutRequest||!accessSession?.user)return;
  dashboardLayout=result.modules;dashboardLayoutReady=true;applyDashboardLayout();
 }catch{if(request===dashboardLayoutRequest){dashboardLayoutReady=false;$('dashboard-layout-feedback').textContent=ui('Indeling laden mislukt. Sluit dit venster en probeer opnieuw.');}}
}
function dashboardEditorButton(text,action){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=text;button.addEventListener('click',action);return button;}
function renderDashboardEditor(focusId=null,focusAction=null){
 const list=$('dashboard-layout-list');list.replaceChildren();
 dashboardDraft.forEach((row,index)=>{
  const module=dashboardModules.find(item=>item.id===row.id),item=document.createElement('div');item.className='dashboard-layout-row';item.dataset.module=row.id;item.setAttribute('role','listitem');
  const handle=dashboardEditorButton(ui('Verslepen'),()=>{});handle.classList.add('dashboard-drag-handle');handle.draggable=true;handle.setAttribute('aria-label',ui('Versleep module {name}',{name:module.title}));
  handle.addEventListener('dragstart',event=>{dashboardDragged=row.id;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',row.id);item.classList.add('dragging');});
  handle.addEventListener('dragend',()=>{dashboardDragged=null;item.classList.remove('dragging');list.querySelectorAll('.drop-target').forEach(node=>node.classList.remove('drop-target'));});
  item.addEventListener('dragover',event=>{if(!dashboardDragged)return;event.preventDefault();event.dataTransfer.dropEffect='move';item.classList.add('drop-target');});
  item.addEventListener('dragleave',()=>item.classList.remove('drop-target'));
  item.addEventListener('drop',event=>{event.preventDefault();if(!dashboardDragged)return;const id=dashboardDragged;dashboardDragged=null;dashboardDraft=moveDashboardModule(dashboardDraft,id,index);renderDashboardEditor(id,'up');});
  const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=row.enabled;check.addEventListener('change',()=>{row.enabled=check.checked;});label.append(check,document.createTextNode(module.title));
  const widthLabel=document.createElement('label');widthLabel.textContent=ui('Breedte');const width=document.createElement('select');
  for(const [value,text] of [['quarter',ui('Klein')],['half',ui('Halfbreed')],['full',ui('Volle breedte')]]){const option=document.createElement('option');option.value=value;option.textContent=text;width.append(option);}
  width.value=row.width;width.addEventListener('change',()=>{row.width=width.value;});widthLabel.append(width);
  const actions=document.createElement('div');actions.className='dashboard-move-actions';
  for(const [action,delta,text] of [['up',-1,ui('Omhoog')],['down',1,ui('Omlaag')]]){
   const button=dashboardEditorButton(text,()=>{dashboardDraft=moveDashboardModule(dashboardDraft,row.id,index+delta);renderDashboardEditor(row.id,action);$('dashboard-layout-feedback').textContent=ui('Module {name} verplaatst naar plek {position}.',{name:module.title,position:index+delta+1});});
   button.dataset.action=action;button.disabled=index+delta<0||index+delta>=dashboardDraft.length;button.setAttribute('aria-label',module.title+' · '+text);actions.append(button);
  }
  item.append(handle,label,widthLabel,actions);list.append(item);
 });
 if(focusId){const item=[...list.children].find(node=>node.dataset.module===focusId);(item.querySelector('[data-action="'+focusAction+'"]:not(:disabled)')||item.querySelector('input')).focus();}
}
async function openDashboardEditor(){
 closeAllPopups();$('dashboard-layout-feedback').textContent='';$('dashboard-layout-dialog').showModal();
 $('dashboard-layout-list').setAttribute('role','list');$('dashboard-layout-list').setAttribute('aria-label',ui('Dashboardmodules'));
 $('dashboard-layout-form').querySelector('button[type="submit"]').disabled=true;
 if(!dashboardLayoutReady)await loadDashboardLayout();
 if(!$('dashboard-layout-dialog').open)return;
 dashboardDraft=dashboardLayout.map(row=>({...row}));renderDashboardEditor();$('dashboard-layout-form').querySelector('button[type="submit"]').disabled=!dashboardLayoutReady;
}
function bindDashboardLayout(){
 initializeDashboardModules();
 $('dashboard-layout-open').addEventListener('click',openDashboardEditor);
 for(const id of ['dashboard-layout-close','dashboard-layout-cancel'])$(id).addEventListener('click',()=>$('dashboard-layout-dialog').close());
 $('dashboard-layout-dialog').addEventListener('close',()=>{dashboardDraft=[];dashboardDragged=null;});
 $('dashboard-layout-reset').addEventListener('click',()=>{dashboardDraft=defaultDashboardLayout();renderDashboardEditor();$('dashboard-layout-feedback').textContent=ui('Standaardindeling klaargezet. Kies Indeling opslaan om te bewaren.');});
 $('dashboard-layout-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!dashboardLayoutReady)return;const button=event.target.querySelector('button[type="submit"]'),request=dashboardLayoutRequest,modules=dashboardDraft.map(row=>({...row}));button.disabled=true;
  try{const result=await jsonAction('api/account/dashboard',{modules});if(request!==dashboardLayoutRequest||!accessSession?.user)return;dashboardLayout=result.modules;applyDashboardLayout();$('dashboard-layout-dialog').close();if(state){renderHomeDashboard();draw();}}
  catch{$('dashboard-layout-feedback').textContent=ui('Indeling opslaan mislukt. Probeer opnieuw.');}
  finally{button.disabled=false;}
 });
}
if(typeof module!=='undefined')module.exports={moveDashboardModule,defaultDashboardLayout};
if(typeof document!=='undefined')bindDashboardLayout();
