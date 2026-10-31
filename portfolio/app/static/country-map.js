/* Local Natural Earth geometry and bundled SVG flags. No map-provider requests. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let countryAtlas=null,countryAtlasPending=null,countryAtlasError=false,countryMapSequence=0;
const countryIndexes=new WeakMap();
const countryMapViews=new Map();
function clearCountryMaps(){countryMapViews.clear();}
function countryToken(value){return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');}
function countryLookup(atlas){
 if(countryIndexes.has(atlas))return countryIndexes.get(atlas);
 const index=new Map(),locales=['nl','en','es'];
 const labels=locales.map(language=>new Intl.DisplayNames([language],{type:'region'}));
 for(const item of atlas){
  const aliases=[item.code,...item.aliases,...Object.values(item.names)];
  for(const formatter of labels)try{aliases.push(formatter.of(item.code));}catch{}
  for(const alias of aliases)if(alias)index.set(countryToken(alias),item);
 }
 countryIndexes.set(atlas,index);
 return index;
}
function countryDisplay(item){
 try{return new Intl.DisplayNames([appLocale()],{type:'region'}).of(item.code)||item.names.en;}catch{return item.names.en;}
}
function countryDistribution(values,atlas){
 const index=countryLookup(atlas),groups=new Map();let total=0;
 for(const row of values){const value=Number(row.value);if(!Number.isFinite(value)||value<=0)continue;total+=value;const country=index.get(countryToken(row.name)),key=country?.code||row.name;const group=groups.get(key)||{key,country,name:country?countryDisplay(country):row.name,value:0};group.value+=value;groups.set(key,group);}
 return [...groups.values()].sort((a,b)=>b.value-a.value).map(row=>({...row,weight:row.value/total*100}));
}
function countryLabelPositions(items,width,height){
 const placed=[],labelWidth=82,labelHeight=27;
 for(const item of items){
  const offsets=[[12,-32],[-94,-32],[12,7],[-94,7]];
  for(let radius=1;radius<=12;radius++)for(const [dx,dy] of [[1,0],[-1,0],[0,-1],[0,1],[1,-1],[-1,-1],[1,1],[-1,1]])offsets.push([dx*radius*48-41,dy*radius*34-13]);
  for(const [dx,dy] of offsets){const x=Math.max(6,Math.min(width-labelWidth-6,item.x+dx)),y=Math.max(6,Math.min(height-labelHeight-6,item.y+dy));if(placed.some(p=>x<p.x+labelWidth+5&&x+labelWidth+5>p.x&&y<p.y+labelHeight+5&&y+labelHeight+5>p.y))continue;placed.push({...item,x,y,anchorX:item.x,anchorY:item.y});break;}
 }
 return placed;
}
function countryFlag(code){const image=homeNode('img');image.src='flags/'+code.toLowerCase()+'.svg?v='+state.app_version;image.alt='';image.width=24;image.height=18;image.loading='lazy';return image;}
async function loadCountryAtlas(){
 if(countryAtlasPending)return countryAtlasPending;
 countryAtlasPending=(async()=>{try{const response=await apiFetch('world-countries.json?v='+state.app_version);if(!response.ok)throw Error();countryAtlas=await response.json();countryAtlasError=false;}catch{countryAtlasError=true;}finally{countryAtlasPending=null;if(state&&accessSession?.user&&reportType==='countries')renderReports();}})();
 return countryAtlasPending;
}
function renderCountryMap(card,values,currency,identity=currency){
 if(!countryAtlas){card.detail.textContent=countryAtlasError?ui('Wereldkaart laden mislukt.'):ui('Wereldkaart laden…');if(countryAtlasError){const retry=homeNode('button',ui('Opnieuw proberen'),'secondary');retry.type='button';retry.onclick=()=>{countryAtlasError=false;loadCountryAtlas();};card.plot.append(retry);}else loadCountryAtlas();return;}
 const rows=countryDistribution(values,countryAtlas);if(!rows.length){reportEmpty(card);return;}
 const layout=homeNode('div',undefined,'country-layout'),mapPanel=homeNode('div',undefined,'country-map-panel'),toolbar=homeNode('div',undefined,'country-map-toolbar'),buttons=homeNode('div',undefined,'country-map-controls');
 const world=homeNode('button',ui('Wereld'),'secondary'),europe=homeNode('button',ui('Europa'),'secondary');world.type=europe.type='button';buttons.append(world,europe);toolbar.append(homeNode('span',ui('Waar je beleggingen zitten')),buttons);mapPanel.append(toolbar);
 const map=homeNode('div',undefined,'country-map-canvas'),selection=homeNode('div',undefined,'country-map-selection'),list=homeNode('div',undefined,'country-ranking');selection.setAttribute('aria-live','polite');mapPanel.append(map,selection,homeNode('p',ui('Klik op een land of vlag voor de waarde en weging. De lijst bevat ook landen zonder kaartlocatie.'),'report-chart-note'));layout.append(mapPanel,list);card.plot.append(layout);card.detail.hidden=true;
 const byCode=new Map(rows.filter(r=>r.country).map(r=>[r.country.code,r])),listButtons=new Map(),viewKey=String(currentBroker)+':'+identity,saved=countryMapViews.get(viewKey)||{};let active=rows.some(r=>r.key===saved.active)?saved.active:rows[0].key,region=saved.region||'world';
 function select(row){active=row.key;selection.replaceChildren();if(row.country)selection.append(countryFlag(row.country.code));else selection.append(homeNode('span','◉','country-unknown-mark'));const text=homeNode('div');text.append(homeNode('strong',row.name),homeNode('small',row.country?.anchor?ui('Land van de belegging'):ui('Niet op de kaart geplaatst')));selection.append(text,homeNode('strong',reportPercent(row.weight),'country-selection-percent'),homeNode('span',money(row.value,currency),'country-selection-value'));
  countryMapViews.set(viewKey,{active,region});
  for(const [key,button] of listButtons)button.setAttribute('aria-pressed',String(key===active));
  for(const node of map.querySelectorAll('[data-country]'))node.classList.toggle('country-selected',node.dataset.country===row.country?.code);
 }
 const table=homeNode('table'),head=homeNode('thead'),heading=homeNode('tr'),body=homeNode('tbody');
 for(const label of [ui('Land'),ui('Marktwaarde'),ui('Weging')]){const th=homeNode('th',label);th.scope='col';heading.append(th);}head.append(heading);table.append(head,body);list.append(table);
 for(const row of rows){const entry=homeNode('tr'),name=homeNode('td'),button=homeNode('button',undefined,'country-ranking-row');button.type='button';button.setAttribute('aria-pressed','false');const header=homeNode('div',undefined,'country-ranking-heading');if(row.country)header.append(countryFlag(row.country.code));else header.append(homeNode('span','◉','country-unknown-mark'));header.append(homeNode('span',row.name));button.append(header);button.onclick=()=>select(row);listButtons.set(row.key,button);name.append(button);entry.append(name,homeNode('td',money(row.value,currency)),homeNode('td',reportPercent(row.weight)));body.append(entry);}

 function draw(){
  map.replaceChildren();world.setAttribute('aria-pressed',String(region==='world'));europe.setAttribute('aria-pressed',String(region==='europe'));
  const width=Math.max(300,map.clientWidth||600),height=Math.max(280,width*.44),svg=reportSvgNode('svg',{viewBox:'0 0 '+width+' '+height,role:'group','aria-label':ui('Wereldkaart met landenverdeling')}),clipId='country-clip-'+(++countryMapSequence);
  map.append(svg);const defs=reportSvgNode('defs',{},undefined,svg),clip=reportSvgNode('clipPath',{id:clipId},undefined,defs);reportSvgNode('rect',{width,height,rx:14},undefined,clip);
  const bounds=region==='europe'?{left:387.5,right:575,top:32.5,bottom:137.5}:{left:0,right:900,top:0,bottom:362.5},scale=Math.min((width-16)/(bounds.right-bounds.left),(height-20)/(bounds.bottom-bounds.top)),offsetX=(width-(bounds.right-bounds.left)*scale)/2-bounds.left*scale,offsetY=(height-(bounds.bottom-bounds.top)*scale)/2-bounds.top*scale;
  const clipped=reportSvgNode('g',{'clip-path':'url(#'+clipId+')'},undefined,svg),paths=reportSvgNode('g',{transform:'translate('+offsetX+' '+offsetY+') scale('+scale+')'},undefined,clipped);
  for(const country of countryAtlas){if(!country.path)continue;const row=byCode.get(country.code),shape=reportSvgNode('path',{d:country.path,fill:row?'#'+(row.weight>40?'66e9c2':row.weight>15?'3fbc99':row.weight>5?'28856e':'20594f'):'#1d3042',stroke:row?'#88eac9':'#385069','stroke-width':.7,'vector-effect':'non-scaling-stroke','data-country':country.code},undefined,paths);
   if(row){shape.setAttribute('tabindex','0');shape.setAttribute('role','button');shape.setAttribute('aria-label',row.name+' · '+reportPercent(row.weight));shape.onclick=()=>select(row);shape.onfocus=()=>select(row);shape.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(row);}};reportSvgNode('title',{},row.name+' · '+reportPercent(row.weight),shape);}
   else shape.setAttribute('aria-hidden','true');
  }
  const located=rows.filter(r=>r.country?.anchor).map(row=>{const [lon,lat]=row.country.anchor;return {...row,x:(lon+180)*2.5*scale+offsetX,y:(85-lat)*2.5*scale+offsetY};}).filter(r=>r.x>=0&&r.x<=width&&r.y>=0&&r.y<=height);
  for(const row of located)reportSvgNode('circle',{cx:row.x,cy:row.y,r:3.5,fill:'#9bf7d7',stroke:'#0c202c','stroke-width':1},undefined,clipped);
  for(const row of countryLabelPositions(located.slice(0,width<500?7:14),width,height)){
   const pin=reportSvgNode('g',{tabindex:0,role:'button','aria-label':row.name+' · '+reportPercent(row.weight),'data-country':row.country.code,'class':'country-map-pin'},undefined,clipped);reportSvgNode('line',{x1:row.anchorX,y1:row.anchorY,x2:row.x+41,y2:row.y+13.5,stroke:'#68a99b','stroke-width':1},undefined,pin);reportSvgNode('rect',{x:row.x,y:row.y,width:82,height:27,rx:8,fill:'#102c36',stroke:'#4a8f80','stroke-width':1},undefined,pin);reportSvgNode('image',{href:'flags/'+row.country.code.toLowerCase()+'.svg?v='+state.app_version,x:row.x+7,y:row.y+6,width:21,height:15},undefined,pin);reportSvgNode('text',{x:row.x+34,y:row.y+18,fill:'#e1fff3','font-size':12,'font-weight':650},reportPercent(row.weight),pin);pin.onclick=()=>select(row);pin.onfocus=()=>select(row);pin.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(row);}};
  }
  select(rows.find(r=>r.key===active)||rows[0]);
 }
 world.onclick=()=>{region='world';draw();};europe.onclick=()=>{region='europe';const inside=row=>row?.country?.anchor&&row.country.anchor[0]>=-25&&row.country.anchor[0]<=50&&row.country.anchor[1]>=30&&row.country.anchor[1]<=72;if(!inside(rows.find(r=>r.key===active))){const local=rows.find(inside);if(local)active=local.key;}draw();};draw();
}
if(typeof window!=='undefined')window.addEventListener('resize',()=>{if(typeof state!=='undefined'&&state&&reportType==='countries')renderReports();});
if(typeof module!=='undefined')module.exports={countryToken,countryLookup,countryDistribution,countryLabelPositions};
