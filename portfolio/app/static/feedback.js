/* Public issue text is rendered as plain text. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let feedbackItems=[],feedbackGeneration=0,feedbackBusy=false;
function clearFeedback(){feedbackGeneration++;feedbackItems=[];$('feedback-list').replaceChildren();$('feedback-status').textContent='';$('feedback-form').reset();}
function renderFeedback(){
 const query=$('feedback-search').value.trim().toLocaleLowerCase(appLocale()),kind=$('feedback-kind').value,status=$('feedback-state').value;
 const rows=feedbackItems.filter(item=>(kind==='all'||item.kind===kind)&&(status==='all'||item.state===status)&&('#'+item.number+' '+item.title).toLocaleLowerCase(appLocale()).includes(query));
 $('feedback-list').replaceChildren();
 for(const item of rows){const row=document.createElement('li'),link=document.createElement('a'),meta=document.createElement('span');link.textContent='#'+item.number+' '+item.title;link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';meta.textContent=(item.kind==='bug'?ui('Bug'):item.kind==='wish'?ui('Wens'):ui('Overig'))+' · '+(item.state==='closed'?ui('Gesloten'):ui('Open'));row.append(link,meta);$('feedback-list').append(row);}
 if(!rows.length){const row=document.createElement('li');row.textContent=ui('Geen meldingen voor deze filters.');$('feedback-list').append(row);}
}
async function loadFeedback(){
 if(!accessSession?.user||feedbackBusy)return;
 feedbackBusy=true;const generation=feedbackGeneration;$('feedback-refresh').disabled=true;$('feedback-status').textContent=ui('Meldingen laden…');
 try{const response=await apiFetch('api/feedback');const data=await response.json();if(generation!==feedbackGeneration||!accessSession?.user)return;if(!response.ok)throw Error(data.error);feedbackItems=data.issues;renderFeedback();$('feedback-status').textContent=ui('Bijgewerkt:')+' '+new Date(data.checked_at).toLocaleString(appLocale())+(data.limited?' · '+ui('De 100 recent bijgewerkte GitHub-items. Bekijk GitHub voor het volledige overzicht.'):'');}
 catch(error){if(generation===feedbackGeneration)$('feedback-status').textContent=error.message;}
 finally{feedbackBusy=false;$('feedback-refresh').disabled=false;}
}
function bindFeedback(){
 registerPopup('feedback-editor',ui('Nieuwe melding'));
 $('feedback-new').addEventListener('click',()=>openPopup('feedback-editor'));
 $('feedback-cancel').addEventListener('click',()=>closePopup('feedback-editor'));
 $('feedback-refresh').addEventListener('click',loadFeedback);
 for(const id of ['feedback-search','feedback-kind','feedback-state'])$(id).addEventListener('input',renderFeedback);
 $('feedback-form').addEventListener('submit',event=>{event.preventDefault();const form=event.target;if(!form.reportValidity())return;const title=form.elements.title.value.trim(),description=form.elements.description.value.trim();if(!title||!description)return;const url=new URL('https://github.com/ferrynl/ha-invest/issues/new');url.searchParams.set('title',(form.elements.kind.value==='bug'?'[Bug] ':'[Wens] ')+title);url.searchParams.set('body',description+'\n\nHome Invest '+(state?.app_version||''));window.open(url.href,'_blank','noopener,noreferrer');});
}
