/* Column filters and stable sorts are local; paged tables apply them before pagination. */
const tableColumnFilters=new Map(),tableColumnSorts=new Map(),tableColumnTypes=new Map();
const filterText=value=>String(value??'').normalize('NFKC').toLocaleLowerCase('nl-NL').replace(/\s+/g,' ').trim();
function matchesTableColumns(id,values){return (tableColumnFilters.get(id)||[]).every((term,index)=>!term||filterText(values[index]).includes(term));}
function tableSortValue(value,type){
 const text=String(value??'').trim();if(!text||/^(—|nog geen|wacht|onbekend|onvolledig)/i.test(text))return null;
 if(type==='date'){
  if(/^\d{4}-\d{2}-\d{2}/.test(text))return text;
  const match=text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(.*)/);if(match)return match[3]+'-'+match[2].padStart(2,'0')+'-'+match[1].padStart(2,'0')+match[4];
 }
 if(type==='number'){
  const cleaned=text.replace(/[^0-9.,+−-]/g,'').replace('−','-');if(!cleaned)return null;
  const number=Number(cleaned.includes(',')?cleaned.replace(/\./g,'').replace(',','.'):cleaned);return Number.isFinite(number)?number:null;
 }
 return filterText(text);
}
function clearTableControls(){for(const terms of tableColumnFilters.values())terms.fill('');tableColumnSorts.clear();document.querySelectorAll('.column-filters input').forEach(input=>{input.value='';});document.querySelectorAll('th[aria-sort]').forEach(header=>header.setAttribute('aria-sort','none'));}
function clearTableSort(id){tableColumnSorts.delete(id);if(typeof document!=='undefined'){const body=document.getElementById(id);body?.closest('table').querySelectorAll('thead tr:first-child th').forEach(h=>h.setAttribute('aria-sort','none'));}}
function sortTableData(id,rows,values){
 const sort=tableColumnSorts.get(id);if(!sort)return rows;
 const type=tableColumnTypes.get(id)?.[sort.index]??'text';
 return rows.map((row,index)=>({row,index,value:tableSortValue(values(row)[sort.index],type)})).sort((a,b)=>{
  if(a.value===null)return b.value===null?a.index-b.index:1;if(b.value===null)return -1;
  const result=typeof a.value==='number'&&typeof b.value==='number'?a.value-b.value:String(a.value).localeCompare(String(b.value),'nl',{numeric:true});return result*sort.direction||a.index-b.index;
 }).map(item=>item.row);
}
function installTableFilters(){
 for(const table of document.querySelectorAll('table')){
  const body=table.tBodies[0],head=table.tHead;if(!body?.id||!head?.rows.length)continue;
  const id=body.id,headers=[...head.rows[0].cells],row=document.createElement('tr');row.className='column-filters';
  const labels=headers.map(h=>h.textContent),terms=headers.map(()=>'');tableColumnFilters.set(id,terms);
  tableColumnTypes.set(id,labels.map(label=>/datum|tijd|^maand$/i.test(label)?'date':/^(aant(al|allen)|inleg|koers$|waarde|marktwaarde|weging|.*winst|dividend|netto|prijs|bedrag|factor|uitkeringen|aandelen$|1 eenheid)/i.test(label)?'number':'text'));
  const values=item=>[...item.cells].map((c,index)=>c.dataset.sortValue??(tableColumnTypes.get(id)[index]==='number'?(c.dataset.sortValue??c.firstChild?.textContent??c.textContent):c.textContent+' '+[...c.querySelectorAll('input[type="checkbox"]')].map(i=>i.checked?'Geselecteerd':'Niet geselecteerd').join(' ')));
  const apply=()=>{
   if(id==='home-positions'||id==='transaction-list')return;
   for(const item of body.rows){const visible=matchesTableColumns(id,[...item.cells].map(c=>c.textContent));if(item.hidden===visible)item.hidden=!visible;}
   const original=[...body.rows],sorted=sortTableData(id,original,values);if(sorted.some((item,index)=>item!==original[index]))body.append(...sorted);
  };
  const refresh=()=>{if(id==='home-positions'){homePage=0;renderHomeTable();}else if(id==='transaction-list'){transactionPage=0;renderTransactions();}else apply();};
  for(const [index,header] of headers.entries()){
   header.setAttribute('scope','col');const button=document.createElement('button');button.type='button';button.className='column-sort';button.textContent=labels[index];button.setAttribute('aria-label','Sorteren op '+labels[index]);header.replaceChildren(button);header.setAttribute('aria-sort','none');
   button.addEventListener('click',()=>{const previous=tableColumnSorts.get(id),direction=previous?.index===index?-previous.direction:1;tableColumnSorts.set(id,{index,direction});headers.forEach((h,i)=>h.setAttribute('aria-sort',i===index?(direction===1?'ascending':'descending'):'none'));refresh();});
   const cell=document.createElement('th'),input=document.createElement('input');input.type='search';input.placeholder='Filter '+labels[index];input.setAttribute('aria-label','Filter '+labels[index]);input.autocomplete='off';
   input.addEventListener('input',()=>{terms[index]=filterText(input.value);refresh();});cell.append(input);row.append(cell);
  }
  head.append(row);
  const note=document.createElement('small');note.className='table-filter-note';note.textContent=(id==='home-positions'||id==='transaction-list')?'Klik op een kolomnaam om te sorteren. Kolomfilters combineren; sortering en filters gelden over alle pagina’s binnen de gekozen selectie.':'Klik op een kolomnaam om te sorteren. Kolomfilters combineren; filters en sortering gelden voor de geladen regels.';table.parentElement.before(note);
  new MutationObserver(apply).observe(body,{childList:true,subtree:true,characterData:true});body.addEventListener('change',apply);apply();
 }
}
if(typeof document!=='undefined')installTableFilters();
if(typeof module!=='undefined')module.exports={tableSortValue,sortTableData,tableColumnSorts,tableColumnTypes};
