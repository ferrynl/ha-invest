/* JavaScript drives the form; the dated rate and exact conversion use the shared FX service. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
let purchaseFxGeneration=0,purchaseFxTimer=null,purchaseFxController=null,purchaseFxPromise=null,purchaseFxRequestKey='',purchaseFxKey='',purchaseFxValue='';
function purchaseFxInput(){const form=$('purchase');return {currency:form.elements.namedItem('currency').value,day:form.elements.namedItem('purchased_on').value,amount:$('purchase-eur-price').disabled?'':$('purchase-eur-price').value};}
function purchaseFxScope(){return JSON.stringify(purchaseFxInput());}
function invalidatePurchaseFx(){purchaseFxGeneration++;clearTimeout(purchaseFxTimer);purchaseFxTimer=null;purchaseFxController?.abort();purchaseFxController=null;purchaseFxPromise=null;purchaseFxRequestKey='';purchaseFxKey='';purchaseFxValue='';$('purchase-eur-tools').setAttribute('aria-busy','false');}
function updatePurchaseFxButton(){const value=purchaseFxInput();$('purchase-eur-convert').disabled=$('purchase-eur-tools').hidden||!value.day||!value.amount||!Number.isFinite(Number(value.amount))||Number(value.amount)<=0;}
function clearPurchaseFx(){const generated=!!purchaseFxKey;invalidatePurchaseFx();if(generated)$('purchase').elements.namedItem('price').value='';$('purchase-eur-price').value='';$('purchase-eur-price').disabled=true;$('purchase-eur-tools').hidden=true;$('purchase-eur-status').textContent='';updatePurchaseFxButton();}
function syncPurchaseFx(){const value=purchaseFxInput();if(!value.currency||value.currency==='EUR'){clearPurchaseFx();return;}$('purchase-eur-tools').hidden=false;$('purchase-eur-price').disabled=false;updatePurchaseFxButton();if($('purchase-eur-price').value)schedulePurchaseFx();}
function schedulePurchaseFx(){
 invalidatePurchaseFx();const value=purchaseFxInput();updatePurchaseFxButton();$('purchase-eur-status').textContent='';
 if(!value.amount)return;
 $('purchase').elements.namedItem('price').value='';
 if(!value.day){$('purchase-eur-status').textContent=ui('Kies eerst de transactiedatum.');return;}
 purchaseFxTimer=setTimeout(()=>{convertPurchaseEur();},350);
}
async function convertPurchaseEur(force=false){
 clearTimeout(purchaseFxTimer);purchaseFxTimer=null;
 const value=purchaseFxInput(),key=purchaseFxScope(),price=$('purchase').elements.namedItem('price');
 if(!value.currency||value.currency==='EUR'||!value.amount)return false;
 if(!value.day){$('purchase-eur-status').textContent=ui('Kies eerst de transactiedatum.');return false;}
 if(!Number.isFinite(Number(value.amount))||Number(value.amount)<=0){$('purchase-eur-status').textContent=ui('Vul een positieve EUR-prijs in.');return false;}
 if(!force&&purchaseFxKey===key&&price.value===purchaseFxValue)return true;
 if(!force&&purchaseFxPromise&&purchaseFxRequestKey===key)return purchaseFxPromise;
 invalidatePurchaseFx();const generation=purchaseFxGeneration;purchaseFxRequestKey=key;
 const controller=purchaseFxController=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
 price.value='';$('purchase-eur-tools').setAttribute('aria-busy','true');$('purchase-eur-convert').disabled=true;$('purchase-eur-status').textContent=ui('Omrekenen…');
 const pending=(async()=>{
  try{
   const result=await jsonAction('api/fx/convert',{amount:value.amount,from:'EUR',to:value.currency,day:value.day},{signal:controller.signal});
   if(generation!==purchaseFxGeneration||key!==purchaseFxScope())return false;
   if(result.from!=='EUR'||result.to!==value.currency||result.requested_on!==value.day||!result.rate_on||result.rate_on>value.day||typeof result.rate!=='string'||!Number.isFinite(Number(result.rate))||Number(result.rate)<=0||typeof result.converted!=='string'||!Number.isFinite(Number(result.converted))||Number(result.converted)<=0)throw Error(ui('Omrekening mislukt. Probeer opnieuw.'));
   price.value=result.converted;purchaseFxKey=key;purchaseFxValue=result.converted;
   $('purchase-eur-status').textContent=ui('Omgerekend naar handelsvaluta.')+' '+value.currency+ui(' · factor ')+new Intl.NumberFormat(appLocale(),{maximumSignificantDigits:12}).format(Number(result.rate))+ui(' · koersdatum ')+dayLabel(result.rate_on);
   return true;
  }catch(error){if(generation===purchaseFxGeneration&&key===purchaseFxScope()){price.value='';$('purchase-eur-status').textContent=error.name==='AbortError'?ui('Omrekening mislukt. Probeer opnieuw.'):error.message;}return false;}
  finally{clearTimeout(timeout);if(generation===purchaseFxGeneration){purchaseFxController=null;purchaseFxPromise=null;purchaseFxRequestKey='';$('purchase-eur-tools').setAttribute('aria-busy','false');updatePurchaseFxButton();}}
 })();purchaseFxPromise=pending;return pending;
}
async function preparePurchaseFx(){const value=purchaseFxInput();if(!value.amount)return;const key=purchaseFxScope();if(!await convertPurchaseEur()||key!==purchaseFxScope()||purchaseFxKey!==key)throw Error(ui('De omrekening is niet actueel. Reken de EUR-prijs opnieuw om.'));}
function bindPurchaseFx(){
 $('purchase-eur-price').addEventListener('input',schedulePurchaseFx);
 $('purchase').elements.namedItem('purchased_on').addEventListener('change',schedulePurchaseFx);
 $('purchase-eur-convert').addEventListener('click',()=>convertPurchaseEur(true));
 $('purchase').elements.namedItem('price').addEventListener('input',()=>{invalidatePurchaseFx();$('purchase-eur-price').value='';$('purchase-eur-status').textContent='';updatePurchaseFxButton();});
 $('purchase').addEventListener('reset',clearPurchaseFx);syncPurchaseFx();
}
bindPurchaseFx();
