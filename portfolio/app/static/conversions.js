/* Explicit merger settings; original trades remain in the ledger. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let conversionReview=null,conversionRequest=0,conversionPreviewVersion=0;
async function loadConversions(){
 const request=++conversionRequest;
 try{
  const response=await apiFetch('api/portfolio/conversions'),data=await response.json();if(!response.ok)throw Error(data.error);
  if(request!==conversionRequest||accessSession?.user?.role!=='admin')return;
  const select=$('conversion-form').elements.account_id,previous=select.value;select.replaceChildren();
  for(const account of data.accounts){const option=document.createElement('option');option.value=account.id;option.textContent=account.name+' · '+account.broker;select.append(option);}
  if([...select.options].some(o=>o.value===previous))select.value=previous;
  $('conversion-open').disabled=!data.accounts.length;
  $('conversion-events').replaceChildren();
  for(const event of data.events){const row=document.createElement('tr');for(const value of [dayLabel(event.purchased_on),event.account_name,event.symbol,event.side==='SELL'?ui('Afgeboekt'):ui('Ontvangen'),quantityLabel(event.quantity),money(event.transfer_cost,event.currency)])cell(row,value);$('conversion-events').append(row);}
  $('conversion-feedback').textContent=data.accounts.length?'':ui('Geen TMX-transacties gevonden.');
 }catch(error){if(request===conversionRequest)$('conversion-feedback').textContent=error.message;}
}
function clearConversionReview(){conversionPreviewVersion++;conversionReview=null;$('conversion-review').textContent='';$('conversion-submit').disabled=true;}
function clearConversions(){conversionRequest++;clearConversionReview();$('conversion-form').reset();$('conversion-form').elements.account_id.replaceChildren();$('conversion-events').replaceChildren();$('conversion-feedback').textContent='';$('conversion-popup-feedback').textContent='';$('conversion-backup').hidden=true;$('conversion-backup').removeAttribute('href');closePopup('conversion-editor');}
$('conversion-open').addEventListener('click',()=>{clearConversionReview();$('conversion-popup-feedback').textContent='';$('conversion-form').elements.quantity.value='';$('conversion-form').elements.day.value='2025-10-02';$('conversion-form').elements.day.max=new Date().toISOString().slice(0,10);openPopup('conversion-editor');});
$('conversion-form').addEventListener('input',clearConversionReview);
$('conversion-form').addEventListener('change',clearConversionReview);
$('conversion-form').addEventListener('submit',async event=>{
 event.preventDefault();const button=$('conversion-preview');button.disabled=true;clearConversionReview();const version=conversionPreviewVersion;
 try{const result=await jsonAction('api/portfolio/conversion-preview',Object.fromEntries(new FormData(event.target)));if(version!==conversionPreviewVersion||accessSession?.user?.role!=='admin')return;conversionReview=result;
  $('conversion-review').textContent=result.account_name+' · '+dayLabel(result.day)+' · '+quantityLabel(result.old_quantity)+' TMX → '+quantityLabel(result.quantity)+' TDT · '+ui('Kostprijs behouden:')+' '+money(result.cost,'EUR')+' · '+ui('Inleg behouden:')+' '+money(result.invested,'EUR');$('conversion-submit').disabled=false;$('conversion-popup-feedback').textContent='';
 }catch(error){$('conversion-popup-feedback').textContent=error.message;}finally{button.disabled=false;}
});
$('conversion-submit').addEventListener('click',async()=>{
 if(!conversionReview)return;const review=conversionReview;$('conversion-submit').disabled=true;
 try{const result=await jsonAction('api/portfolio/conversion',review);closePopup('conversion-editor');clearConversionReview();stateETag=null;await load();await loadConversions();$('conversion-feedback').textContent=ui('TMX omgeboekt naar TDT. De oorspronkelijke transacties zijn behouden.');$('conversion-backup').href='api/portfolio/conversion-backup?name='+encodeURIComponent(result.backup_name);$('conversion-backup').hidden=false;
 }catch(error){clearConversionReview();$('conversion-popup-feedback').textContent=error.message;}
});
$('conversion-cancel').addEventListener('click',()=>closePopup('conversion-editor'));
