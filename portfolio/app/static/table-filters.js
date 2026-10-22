/* Column filters stay in memory and combine with AND; refreshed rows retain filters. */
const tableColumnFilters=new Map();
const filterText=value=>String(value??'').normalize('NFKC').toLocaleLowerCase('nl-NL').replace(/\s+/g,' ').trim();
function matchesTableColumns(id,values){return (tableColumnFilters.get(id)||[]).every((term,index)=>!term||filterText(values[index]).includes(term));}
function installTableFilters(){
 for(const table of document.querySelectorAll('table')){
  const body=table.tBodies[0],head=table.tHead;if(!body?.id||!head?.rows.length)continue;
  const id=body.id,headers=[...head.rows[0].cells],row=document.createElement('tr');row.className='column-filters';
  const terms=headers.map(()=>'');tableColumnFilters.set(id,terms);
  const apply=()=>{if(id==='home-positions')return;for(const item of body.rows){const visible=matchesTableColumns(id,[...item.cells].map(c=>c.textContent+' '+[...c.querySelectorAll('input[type="checkbox"]')].map(i=>i.checked?'Geselecteerd':'Niet geselecteerd').join(' ')));if(item.hidden===visible)item.hidden=!visible;}};
  for(const [index,header] of headers.entries()){
   const cell=document.createElement('th'),input=document.createElement('input');input.type='search';input.placeholder='Filter '+header.textContent;input.setAttribute('aria-label','Filter '+header.textContent);input.autocomplete='off';
   input.addEventListener('input',()=>{terms[index]=filterText(input.value);if(id==='home-positions'){homePage=0;renderHomeTable();}else apply();});cell.append(input);row.append(cell);
  }
  head.append(row);
  const note=document.createElement('small');note.className='table-filter-note';note.textContent=id==='home-positions'?'Kolomfilters combineren en doorzoeken alle posities binnen de gekozen valuta en algemene filters, over alle pagina’s.':'Kolomfilters combineren. Ze doorzoeken de geladen regels; wis een veld om het filter op te heffen.';table.parentElement.before(note);
  new MutationObserver(apply).observe(body,{childList:true,subtree:true,characterData:true});body.addEventListener('change',apply);apply();
 }
}
installTableFilters();
