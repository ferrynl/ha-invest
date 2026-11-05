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
 {id:'daily-movers',title:ui('Stijgers en dalers vandaag'),width:'full'},
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

function updateDashboardModule(rows,id,settings){return rows.map(row=>row.id===id?{...row,...settings,id}:({...row}));}
let dashboardChart='value',dashboardChartDraft='value',dashboardChartBeforeEdit='value';
let dashboardLayout=defaultDashboardLayout(),dashboardDraft=[],dashboardLayoutReady=false,dashboardLayoutRequest=0,dashboardEditing=false,dashboardSaving=false,dashboardDrag=null,dashboardScrollFrame=null,dashboardSettingsId=null;
const dashboardNodes=new Map();
const activeDashboardLayout=()=>dashboardEditing?dashboardDraft:dashboardLayout;
function initializeDashboardModules(){
 const home=document.querySelector('[data-page="home"]'),board=document.createElement('div');board.id='home-module-board';board.className='home-module-board';$('totals').before(board);
 const insights=home.querySelector('.home-insights'),original={currencies:$('home-currencies'),chart:$('home-chart-panel'),allocation:insights.children[0],movers:insights.children[1],holdings:home.querySelector('.home-holdings')};
 const notice=document.createElement('section');notice.append($('home-euro-status'),$('home-health'));original.notice=notice;
 original['daily-movers']=$('home-daily-movers-panel');
 for(const module of dashboardModules)mountDashboardModule(board,module,original[module.id]);
 insights.remove();$('totals').hidden=true;
 const error=document.createElement('p');error.id='dashboard-layout-error';error.setAttribute('role','status');board.before(error);
 const toolbar=document.createElement('section');toolbar.id='dashboard-edit-toolbar';toolbar.className='dashboard-edit-toolbar';toolbar.hidden=true;
 const note=document.createElement('p');note.textContent=ui('Versleep onderdelen op je dashboard. Gebruik de instellingenknop per onderdeel.');
 const actions=document.createElement('div');actions.className='dashboard-edit-actions';
 const save=dashboardEditorButton(ui('Indeling opslaan'),saveDashboardLayout);save.id='dashboard-edit-save';
 const cancel=dashboardEditorButton(ui('Annuleren'),cancelDashboardEditor);cancel.id='dashboard-edit-cancel';
 const reset=dashboardEditorButton(ui('Standaardindeling'),()=>{if(dashboardSaving)return;dashboardDraft=defaultDashboardLayout();dashboardChartDraft='value';$('chart-measure').value=dashboardChartDraft;applyDashboardLayout();refreshDashboardPreview();});reset.id='dashboard-edit-reset';
 const feedback=document.createElement('p');feedback.id='dashboard-layout-feedback';feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');actions.append(save,cancel,reset);toolbar.append(note,actions,feedback);board.before(toolbar);
 const add=dashboardEditorButton(ui('Module toevoegen'),()=>{
  const id=dashboardExtraIds.find(key=>!dashboardDraft.some(row=>row.id===key));
  if(id)openDashboardModuleSettings(id);
 });
 add.id='dashboard-add-module';actions.prepend(add);
 const empty=document.createElement('p');empty.id='dashboard-layout-empty';empty.className='home-muted';empty.textContent=ui('Je dashboard is leeg. Kies Dashboard aanpassen om modules aan te zetten.');board.after(empty);applyDashboardLayout();
}
function mountDashboardModule(board,module,existing){
  const content=existing||document.createElement('article');if(!existing)content.className='home-metric';content.id='home-module-'+module.id;content.classList.add('dashboard-widget-content');
  if(module.id==='currencies')content.id='home-currencies';if(module.id==='chart')content.id='home-chart-panel';
  const node=document.createElement('section');node.className='home-module dashboard-widget';node.dataset.module=module.id;
  const controls=document.createElement('div');controls.className='dashboard-widget-controls';controls.hidden=true;
  const title=document.createElement('strong');title.textContent=module.title;
  const handle=dashboardEditorButton(ui('Verslepen'),()=>{});handle.textContent='⠿';handle.classList.add('dashboard-widget-handle');handle.setAttribute('aria-label',ui('Versleep module {name}',{name:module.title}));handle.setAttribute('title',ui('Versleep of gebruik de pijltjestoetsen'));
  handle.addEventListener('pointerdown',event=>startDashboardDrag(event,module.id));
  handle.addEventListener('keydown',event=>{const index=dashboardDraft.findIndex(row=>row.id===module.id),target=index+(event.key==='ArrowUp'||event.key==='ArrowLeft'?-1:1);if(!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)||!dashboardEditing||dashboardSaving)return;event.preventDefault();moveDashboardDraft(module.id,target,true);});
  const actions=document.createElement('div');actions.className='dashboard-widget-actions';
  for(const [delta,text] of [[-1,ui('Omhoog')],[1,ui('Omlaag')]]){const button=dashboardEditorButton(text,()=>moveDashboardDraft(module.id,dashboardDraft.findIndex(row=>row.id===module.id)+delta,true));button.textContent=delta<0?'↑':'↓';button.dataset.direction=String(delta);button.setAttribute('aria-label',module.title+' · '+text);actions.append(button);}
  const settings=dashboardEditorButton(ui('Instellingen'),()=>openDashboardModuleSettings(module.id));settings.textContent='⚙';settings.setAttribute('title',ui('Instellingen'));settings.setAttribute('aria-label',ui('Instellingen voor {name}',{name:module.title}));settings.classList.add('dashboard-widget-settings');actions.append(settings);
  const disabled=document.createElement('p');disabled.className='dashboard-widget-disabled';disabled.textContent=ui('Uitgeschakeld');disabled.hidden=true;
  controls.append(handle,title,actions);node.append(controls,content,disabled);dashboardNodes.set(module.id,node);board.append(node);
}

const dashboardExtraIds=Array.from({length:12},(_,index)=>'extra-'+(index+1));
function dashboardModuleTitle(row){
 if(row.title)return row.title;
 const metric=row.metric||row.id;
 if(Object.hasOwn(homeMetricOptions,metric))return homeMetricOptions[metric]();
 return dashboardModules.find(module=>module.id===row.id)?.title||ui('Extra cijferkaart');
}
function dashboardPreview(){
 const id=dashboardSettingsId,chart=id==='chart',target=$('dashboard-module-preview');
 target.replaceChildren();
 if(target.hidden)return;
 target.append(homeNode('small',ui('Voorbeeld')));
 if(chart){
  const choice=$('dashboard-module-chart-choice').value,preset=chartPresets[choice],svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 120 38');svg.setAttribute('aria-hidden','true');
  const path=(d,stroke,fill='none')=>{
   const node=document.createElementNS(svg.namespaceURI,'path');node.setAttribute('d',d);
   node.setAttribute('stroke',stroke);node.setAttribute('stroke-width','2');node.setAttribute('fill',fill);svg.append(node);
  };
  path('M1 2V36H119','#526680');
  const line='M4 29L24 22 43 26 64 15 82 18 113 6';
  if(preset.shape==='columns')path('M7 35V26H19V35ZM26 35V20H38V35ZM45 35V23H57V35ZM64 35V13H76V35ZM83 35V17H95V35ZM102 35V5H114V35Z','#47dcb0','#47dcb0');
  else if(preset.shape==='step')path('M4 29H24V24H47V17H72V12H92V5H113','#47dcb0');
  else{
   if(preset.shape==='area'||choice==='return')path(line+'V35H4Z','none','#47dcb048');
   if(preset.fields.length>1)path('M4 32L26 29 46 30 67 24 87 25 113 20','#70b7ff');
   path(line,'#47dcb0');
  }
  target.append(svg,homeNode('span',preset.label()));
 }else{
  const metric=$('dashboard-module-metric-choice').value;
  const card=homeNode('div',undefined,'home-metric');
  card.dataset.style=$('dashboard-module-style').value;
  const value=['open','closed','missing'].includes(metric)?'12':['return','dividend_yield'].includes(metric)?homePercent(8.4):money(1234.56,homeDisplayCurrency());
  card.append(homeNode('span',$('dashboard-module-custom-title').value.trim()||homeMetricOptions[metric](),'home-metric-label'),homeNode('strong',value));
  if($('dashboard-module-note').checked)card.append(homeNode('small',ui('Binnen de huidige selectie')));
  target.append(card);
 }
}
function dashboardEditorButton(text,action){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=text;button.addEventListener('click',action);return button;}
function applyDashboardLayout(){
 const rows=activeDashboardLayout(),board=$('home-module-board');document.body.classList.toggle('dashboard-editing',dashboardEditing);
 const activeIds=new Set(rows.map(row=>row.id));
 for(const id of dashboardExtraIds){
  if(!activeIds.has(id)&&dashboardNodes.has(id)){dashboardNodes.get(id).remove();dashboardNodes.delete(id);}
 }
 rows.forEach((row,index)=>{
  if(!dashboardNodes.has(row.id))mountDashboardModule(board,{id:row.id,title:dashboardModuleTitle(row)});
  const node=dashboardNodes.get(row.id);
  if(dashboardEditing){
   const title=dashboardModuleTitle(row);
   node.querySelector('.dashboard-widget-controls strong').textContent=title;
   node.querySelector('.dashboard-widget-settings').setAttribute('aria-label',ui('Instellingen voor {name}',{name:title}));
  }node.hidden=!dashboardEditing&&!row.enabled;node.dataset.width=row.width;node.classList.toggle('is-disabled',!row.enabled);node.querySelector('.dashboard-widget-controls').hidden=!dashboardEditing;node.querySelector('.dashboard-widget-disabled').hidden=!dashboardEditing||row.enabled;
  for(const button of node.querySelectorAll('.dashboard-widget-controls button'))button.disabled=dashboardSaving;
  for(const button of node.querySelectorAll('[data-direction]'))button.disabled=dashboardSaving||index+Number(button.dataset.direction)<0||index+Number(button.dataset.direction)>=rows.length;
  // Insert only moved nodes, preserving focus and pointer gestures on other widgets.
  if(board.children[index]!==node)board.insertBefore(node,board.children[index]||null);
 });
 $('dashboard-edit-toolbar').hidden=!dashboardEditing;$('dashboard-layout-open').hidden=dashboardEditing;$('dashboard-layout-empty').hidden=dashboardEditing||rows.some(row=>row.enabled);
 $('dashboard-add-module').disabled=dashboardSaving||dashboardExtraIds.every(id=>activeIds.has(id));
 for(const id of ['dashboard-edit-save','dashboard-edit-cancel','dashboard-edit-reset'])$(id).disabled=dashboardSaving;
}
function dashboardModuleEnabled(id){return activeDashboardLayout().some(row=>row.id===id&&row.enabled);}
function refreshDashboardPreview(){if(typeof state!=='undefined'&&state&&document.body.classList.contains('home-page')){renderHomeDashboard();requestAnimationFrame(draw);}}
function clearDashboardLayout(){finishDashboardDrag(true);dashboardLayoutRequest++;dashboardEditing=false;dashboardSaving=false;dashboardLayoutReady=false;dashboardLayout=defaultDashboardLayout();dashboardChart='value';dashboardDraft=[];applyDashboardLayout();applyHomeChartPreference();$('dashboard-chart-status').textContent='';$('dashboard-chart-feedback').textContent='';$('dashboard-chart-form').querySelector('button[type="submit"]').disabled=false;}
async function loadDashboardLayout(){
 const request=++dashboardLayoutRequest;
 try{const response=await apiFetch('api/account/dashboard');if(!response.ok)throw Error();const result=await response.json();if(request!==dashboardLayoutRequest||!accessSession?.user)return;dashboardLayout=result.modules;dashboardChart=result.chart||'value';dashboardLayoutReady=true;applyDashboardLayout();applyHomeChartPreference();refreshDashboardPreview();}
 catch{if(request===dashboardLayoutRequest){dashboardLayoutReady=false;$('dashboard-layout-error').textContent=ui('Indeling laden mislukt. Probeer Dashboard aanpassen opnieuw.');}}
}
async function openDashboardEditor(){
 if(dashboardEditing||dashboardSaving)return;$('dashboard-layout-error').textContent='';closeAllPopups();$('dashboard-layout-open').disabled=true;
 if(!dashboardLayoutReady)await loadDashboardLayout();$('dashboard-layout-open').disabled=false;
 if(!dashboardLayoutReady||!accessSession?.user)return;
 dashboardDraft=dashboardLayout.map(row=>({...row}));dashboardChartBeforeEdit=$('chart-measure').value;dashboardChartDraft=dashboardChart;dashboardEditing=true;$('dashboard-layout-feedback').textContent='';applyDashboardLayout();$('dashboard-edit-save').focus();
}
function cancelDashboardEditor(){if(dashboardSaving)return;finishDashboardDrag(true);$('dashboard-module-dialog').close();dashboardEditing=false;dashboardDraft=[];$('chart-measure').value=dashboardChartBeforeEdit;applyDashboardLayout();refreshDashboardPreview();$('dashboard-layout-open').focus();}
async function saveDashboardLayout(){
 if(!dashboardEditing||!dashboardLayoutReady||dashboardSaving)return;finishDashboardDrag(false);const request=dashboardLayoutRequest,modules=dashboardDraft.map(row=>({...row}));dashboardSaving=true;applyDashboardLayout();
 try{const result=await jsonAction('api/account/dashboard',{modules,chart:dashboardChartDraft});if(request!==dashboardLayoutRequest||!accessSession?.user)return;dashboardLayout=result.modules;dashboardChart=result.chart;applyHomeChartPreference();dashboardEditing=false;dashboardDraft=[];applyDashboardLayout();refreshDashboardPreview();$('dashboard-layout-open').focus();}
 catch{if(request===dashboardLayoutRequest)$('dashboard-layout-feedback').textContent=ui('Indeling opslaan mislukt. Probeer opnieuw.');}
 finally{if(request===dashboardLayoutRequest){dashboardSaving=false;applyDashboardLayout();}}
}
function moveDashboardDraft(id,target,focus=false){
 if(!dashboardEditing||dashboardSaving)return;dashboardDraft=moveDashboardModule(dashboardDraft,id,target);applyDashboardLayout();
 const index=dashboardDraft.findIndex(row=>row.id===id);$('dashboard-layout-feedback').textContent=ui('Module {name} verplaatst naar plek {position}.',{name:dashboardModuleTitle(dashboardDraft[index]),position:index+1});
 if(focus)dashboardNodes.get(id).querySelector('.dashboard-widget-handle').focus({preventScroll:true});
}
function startDashboardDrag(event,id){
 if(!dashboardEditing||dashboardSaving||event.button!==0||event.isPrimary===false)return;event.preventDefault();finishDashboardDrag(false);
 dashboardDrag={id,pointer:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY,moved:false,before:dashboardDraft.map(row=>({...row}))};
 document.addEventListener('pointermove',moveDashboardPointer,{passive:false});document.addEventListener('pointerup',endDashboardPointer);document.addEventListener('pointercancel',cancelDashboardPointer);document.body.classList.add('dashboard-dragging');
 dashboardScrollFrame=requestAnimationFrame(scrollDashboardDrag);
}
function dashboardDragTarget(rows,id,targetId){const from=rows.findIndex(row=>row.id===id),to=rows.findIndex(row=>row.id===targetId);return from<0||to<0||from===to?rows:moveDashboardModule(rows,id,to);}
function moveDashboardPointer(event){
 if(!dashboardDrag||event.pointerId!==dashboardDrag.pointer)return;event.preventDefault();dashboardDrag.x=event.clientX;dashboardDrag.y=event.clientY;
 if(Math.hypot(event.clientX-dashboardDrag.startX,event.clientY-dashboardDrag.startY)<6&&!dashboardDrag.moved)return;
 dashboardDrag.moved=true;dashboardNodes.get(dashboardDrag.id).classList.add('is-dragging');updateDashboardDragTarget();
}
function updateDashboardDragTarget(){
 if(!dashboardDrag?.moved)return;
 const target=document.elementFromPoint(dashboardDrag.x,dashboardDrag.y)?.closest('.dashboard-widget');if(!target||target.dataset.module===dashboardDrag.id)return;
 const rect=target.getBoundingClientRect();if(dashboardDrag.x<rect.left+8||dashboardDrag.x>rect.right-8||dashboardDrag.y<rect.top+8||dashboardDrag.y>rect.bottom-8)return;
 const id=dashboardDrag.id,from=dashboardDraft.findIndex(row=>row.id===id),to=dashboardDraft.findIndex(row=>row.id===target.dataset.module);
 // Cross the target midpoint before moving, avoiding oscillation at module edges.
 const source=dashboardNodes.get(id).getBoundingClientRect(),sameRow=Math.abs(source.top-rect.top)<30;
 if(sameRow?(from<to?dashboardDrag.x<rect.left+rect.width/2:dashboardDrag.x>rect.left+rect.width/2):(from<to?dashboardDrag.y<rect.top+rect.height/2:dashboardDrag.y>rect.top+rect.height/2))return;
 dashboardDraft=dashboardDragTarget(dashboardDraft,id,target.dataset.module);applyDashboardLayout();
}
function scrollDashboardDrag(){
 if(!dashboardDrag)return;if(dashboardDrag.moved){const y=dashboardDrag.y,amount=y<90?-14:y>window.innerHeight-90?14:0;if(amount){window.scrollBy(0,amount);updateDashboardDragTarget();}}
 dashboardScrollFrame=requestAnimationFrame(scrollDashboardDrag);
}
function endDashboardPointer(event){if(dashboardDrag&&event.pointerId===dashboardDrag.pointer)finishDashboardDrag(false);}
function cancelDashboardPointer(event){if(dashboardDrag&&event.pointerId===dashboardDrag.pointer)finishDashboardDrag(true);}
function finishDashboardDrag(cancel){
 if(dashboardScrollFrame!==null)cancelAnimationFrame(dashboardScrollFrame);dashboardScrollFrame=null;
 document.removeEventListener('pointermove',moveDashboardPointer);document.removeEventListener('pointerup',endDashboardPointer);document.removeEventListener('pointercancel',cancelDashboardPointer);document.body.classList.remove('dashboard-dragging');
 if(!dashboardDrag)return;const id=dashboardDrag.id;if(cancel)dashboardDraft=dashboardDrag.before;dashboardDrag=null;dashboardNodes.get(id)?.classList.remove('is-dragging');if(dashboardEditing)applyDashboardLayout();
}
function openDashboardModuleSettings(id){
 if(!dashboardEditing||dashboardSaving)return;
 finishDashboardDrag(false);
 const existing=dashboardDraft.find(item=>item.id===id),extra=dashboardExtraIds.includes(id);
 if(!existing&&!extra)return;
 const row=existing||{id,width:'quarter',enabled:true,metric:'market'};
 dashboardSettingsId=id;
 $('dashboard-module-title').textContent=existing?ui('Instellingen voor {name}',{name:dashboardModuleTitle(row)}):ui('Extra cijferkaart');
 $('dashboard-module-enabled').checked=row.enabled;$('dashboard-module-width').value=row.width;
 const isMetric=extra||Object.hasOwn(homeMetricOptions,id);
 $('dashboard-module-chart').hidden=id!=='chart';$('dashboard-module-metric').hidden=!isMetric;
 $('dashboard-module-remove').hidden=!extra||!existing;
 $('dashboard-module-preview').hidden=id!=='chart'&&!isMetric;
 $('dashboard-module-chart-choice').value=dashboardChartDraft;
 if(isMetric){
  $('dashboard-module-metric-choice').value=row.metric||id;
  $('dashboard-module-custom-title').value=row.title||'';
  $('dashboard-module-style').value=row.style||'standard';
  $('dashboard-module-note').checked=row.note!==false;
 }
 dashboardPreview();$('dashboard-module-dialog').showModal();
}
function applyDashboardModuleSettings(event){
 event.preventDefault();if(!dashboardEditing||dashboardSaving||!dashboardSettingsId)return;
 const id=dashboardSettingsId;
 const settings={enabled:$('dashboard-module-enabled').checked,width:$('dashboard-module-width').value};
 if(!$('dashboard-module-metric').hidden)Object.assign(settings,{
  metric:$('dashboard-module-metric-choice').value,title:$('dashboard-module-custom-title').value.trim(),
  style:$('dashboard-module-style').value,note:$('dashboard-module-note').checked
 });
 if(id==='chart'){
  dashboardChartDraft=$('dashboard-module-chart-choice').value;
  $('chart-measure').value=dashboardChartDraft;
 }
 dashboardDraft=dashboardDraft.some(row=>row.id===id)?updateDashboardModule(dashboardDraft,id,settings):[...dashboardDraft,{id,...settings}];
 applyDashboardLayout();$('dashboard-module-dialog').close();refreshDashboardPreview();
}

function applyHomeChartPreference(){$('chart-measure').value=dashboardChart;}
function bindDashboardChartSettings(){
 const dialog=$('dashboard-chart-dialog'),form=$('dashboard-chart-form'),choice=$('dashboard-chart-choice'),open=$('dashboard-chart-open'),submit=form.querySelector('button[type="submit"]');
 fillChartPresets(choice);
 open.addEventListener('click',async()=>{
  if(dashboardSaving)return;
  open.disabled=true;
  if(!dashboardLayoutReady)await loadDashboardLayout();
  open.disabled=false;
  if(!dashboardLayoutReady||!accessSession?.user)return;
  choice.value=dashboardChart;$('dashboard-chart-feedback').textContent='';dialog.showModal();
 });
 $('dashboard-chart-cancel').addEventListener('click',()=>dialog.close());
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(dashboardSaving||!dashboardLayoutReady||!accessSession?.user)return;
  const request=dashboardLayoutRequest;
  dashboardSaving=true;submit.disabled=true;
  try{
   const result=await jsonAction('api/account/dashboard',{modules:dashboardLayout,chart:choice.value});
   if(request!==dashboardLayoutRequest||!accessSession?.user)return;
   dashboardLayout=result.modules;dashboardChart=result.chart;applyHomeChartPreference();
   $('dashboard-chart-status').textContent=ui('Standaardgrafiek opgeslagen.');dialog.close();refreshDashboardPreview();
  }catch{if(request===dashboardLayoutRequest)$('dashboard-chart-feedback').textContent=ui('Indeling opslaan mislukt. Probeer opnieuw.');}
  finally{if(request===dashboardLayoutRequest){dashboardSaving=false;submit.disabled=false;}}
 });
}
function bindDashboardLayout(){
 fillChartPresets($('dashboard-module-chart-choice'));
 for(const [id,label] of Object.entries(homeMetricOptions)){
  const option=homeNode('option',label());option.value=id;$('dashboard-module-metric-choice').append(option);
 }
 initializeDashboardModules();bindDashboardChartSettings();$('dashboard-layout-open').addEventListener('click',openDashboardEditor);
 for(const id of ['dashboard-module-close','dashboard-module-cancel'])$(id).addEventListener('click',()=>$('dashboard-module-dialog').close());
 $('dashboard-module-dialog').addEventListener('close',()=>{const id=dashboardSettingsId;dashboardSettingsId=null;if(dashboardEditing&&id)(dashboardNodes.get(id)?.querySelector('.dashboard-widget-settings')||$('dashboard-add-module')).focus({preventScroll:true});});
 $('dashboard-module-form').addEventListener('submit',applyDashboardModuleSettings);
 $('dashboard-module-form').addEventListener('input',dashboardPreview);
 $('dashboard-module-remove').addEventListener('click',()=>{
  if(!dashboardEditing||dashboardSaving||!dashboardExtraIds.includes(dashboardSettingsId))return;
  dashboardDraft=dashboardDraft.filter(row=>row.id!==dashboardSettingsId);applyDashboardLayout();$('dashboard-module-dialog').close();refreshDashboardPreview();
 });
 document.addEventListener('keydown',event=>{if(event.key!=='Escape'||!dashboardEditing||document.querySelector('dialog[open]'))return;event.preventDefault();if(dashboardDrag)finishDashboardDrag(true);else cancelDashboardEditor();});
 window.addEventListener('hashchange',()=>{if(dashboardEditing&&!dashboardSaving)cancelDashboardEditor();});
}
if(typeof module!=='undefined')module.exports={moveDashboardModule,defaultDashboardLayout,updateDashboardModule,dashboardDragTarget};
if(typeof document!=='undefined')bindDashboardLayout();
