/* Housekeeping is explicit, previewed and protected by admin/CSRF on the server. */
let cleanupReview=null,cleanupGeneration=0,cleanupBusy=false;
function resetCleanupReview(){cleanupGeneration++;cleanupReview=null;$('cleanup-review').replaceChildren();$('cleanup-submit').disabled=true;}
function cleanupOptions(){return Object.fromEntries(['caches','quotes','backups','compact'].map(key=>[key,$('cleanup-form').elements.namedItem(key).checked]));}
$('cleanup-open').addEventListener('click',()=>{resetCleanupReview();$('cleanup-popup-feedback').textContent='';openPopup('cleanup-editor');});
$('cleanup-form').addEventListener('change',resetCleanupReview);
$('cleanup-form').addEventListener('submit',async event=>{
 event.preventDefault();if(cleanupBusy)return;resetCleanupReview();const request=cleanupGeneration;$('cleanup-preview').disabled=true;
 try{
  const result=await jsonAction('api/portfolio/cleanup-preview',cleanupOptions());if(request!==cleanupGeneration||accessSession?.user?.role!=='admin')return;cleanupReview=result;
  const number=value=>new Intl.NumberFormat(appLocale()).format(value);
  for(const text of [ui('Tijdelijke cache-items')+': '+number(result.cache_count)+' · '+resourceBytes(result.cache_bytes),ui('Overtollige koerswaarnemingen')+': '+number(result.quote_count),ui('Te verwijderen oude back-ups')+': '+number(result.backup_count)+' · '+resourceBytes(result.backup_bytes),ui('Herbruikbare databaseruimte')+': '+resourceBytes(result.reusable_bytes),ui('Vooraf wordt een nieuwe herstelback-up gemaakt. Je boekingen en dagelijkse koershistorie blijven behouden.')])$('cleanup-review').append(homeNode('p',text));
  $('cleanup-submit').disabled=false;$('cleanup-popup-feedback').textContent='';
 }catch(error){$('cleanup-popup-feedback').textContent=error.message;}finally{$('cleanup-preview').disabled=false;}
});
$('cleanup-submit').addEventListener('click',async()=>{
 if(!cleanupReview||cleanupBusy)return;cleanupBusy=true;const review=cleanupReview;for(const field of $('cleanup-form').querySelectorAll('input,button'))field.disabled=true;
 try{
  const result=await jsonAction('api/portfolio/cleanup',{options:review.options,review:review.review,confirmation:'OPSCHONEN'});
  if(accessSession?.user?.role!=='admin')return;
  closePopup('cleanup-editor');resetCleanupReview();stateETag=null;
  $('cleanup-feedback').textContent=ui('Opschonen voltooid. Herstelback-up opgeslagen:')+' '+result.backup_name+' · '+ui('Database')+': '+resourceBytes(result.database_before)+' → '+resourceBytes(result.database_after);
  if(review.options.compact&&!result.compacted)$('cleanup-feedback').textContent+=' '+ui('Database verkleinen kon nu niet worden afgerond.');
  await load();
 }catch(error){resetCleanupReview();$('cleanup-popup-feedback').textContent=error.message;}
 finally{cleanupBusy=false;for(const field of $('cleanup-form').querySelectorAll('input,button'))field.disabled=false;$('cleanup-submit').disabled=!cleanupReview;}
});
$('cleanup-cancel').addEventListener('click',()=>closePopup('cleanup-editor'));
