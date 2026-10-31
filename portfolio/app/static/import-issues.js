/* UI strings use the shared catalogue; pure Node tests retain Dutch defaults. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let reviewIssues=[];
function clearImportIssues(){reviewIssues=[];$('issue-list').replaceChildren();$('capital-list').replaceChildren();$('issue-form').reset();closePopup('issue-editor');$('issue-title').textContent='';$('issue-choice-feedback').textContent='';$('issue-filter').value='pending';$('issue-feedback').textContent='';}
async function loadImportIssues(){
 try{const response=await apiFetch('api/imports/issues');const result=await response.json();if(!response.ok)throw Error(result.error);reviewIssues=result.issues;renderImportIssues();const selectedId=Number($('issue-form').elements.namedItem('id').value);if(selectedId&&!reviewIssues.some(i=>i.id===selectedId&&i.state==='pending')){closePopup('issue-editor');$('issue-form').reset();}
 $('capital-list').replaceChildren();for(const item of result.capital_returns){const row=document.createElement('tr');for(const value of [item.account_name,item.ticker,item.paid_on,money(item.amount,item.currency)])cell(row,value);$('capital-list').append(row);}
 $('issue-feedback').textContent=reviewIssues.filter(i=>i.state==='pending').length+ui(' regels wachten op jouw keuze. De overige geldige regels zijn onafhankelijk verwerkt.');
 }catch(error){$('issue-feedback').textContent=error.message;}
}
function renderImportIssues(){
 const filter=$('issue-filter').value;$('issue-list').replaceChildren();
 for(const item of reviewIssues){if(filter!=='all'&&item.state!==filter)continue;const row=document.createElement('div');row.className='auto-mapping-row';row.setAttribute('role','listitem');const title=document.createElement('strong');title.textContent=item.ticker+' - '+item.account_name+ui(' - regel ')+item.line;row.append(title);
 for(const value of [item.filename,item.action+' - '+item.day+' - '+item.amount+' '+item.currency,ui(item.reason),item.state==='pending'?ui('Jouw keuze nodig'):item.state==='ignored'?ui('Bewust overgeslagen'):ui('Verwerkt')]){const detail=document.createElement('p');detail.textContent=value;row.append(detail);}
 const action=document.createElement('div');row.append(action);if(item.state==='pending'){const button=document.createElement('button');button.type='button';button.textContent=ui('Wat moet dit worden?');button.addEventListener('click',()=>{const form=$('issue-form');form.reset();form.elements.namedItem('id').value=item.id;$('issue-title').textContent=item.ticker+ui(' - regel ')+item.line+' - '+item.action;openPopup('issue-editor');$('issue-choice-feedback').textContent=ui(item.reason);form.elements.namedItem('decision').focus();});action.append(button);}$('issue-list').append(row);
 }
}
function bindImportIssues(){
 $('issue-filter').addEventListener('change',renderImportIssues);$('issue-refresh').addEventListener('click',loadImportIssues);$('issue-close').addEventListener('click',()=>{closePopup('issue-editor');});
 $('issue-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('[type="submit"]');button.disabled=true;
 try{const result=await jsonAction('api/imports/issues/resolve',Object.fromEntries(new FormData(event.target)));stateETag=null;await load();await loadImportIssues();const message=result.imported+ui(' regels verwerkt; ')+result.pending+ui(' regels vragen nog aandacht in deze import. Bij een resterende fout blijft de regel bewaard.');$('issue-choice-feedback').textContent=message;$('issue-feedback').textContent+=' '+message;}
 catch(error){$('issue-choice-feedback').textContent=error.message;}finally{button.disabled=false;}});
}
