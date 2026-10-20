let fxState=null,fxBusy=false;
function clearCurrencies(){fxState=null;for(const id of ['fx-rates','fx-history','fx-audit'])$(id).replaceChildren();$('fx-result').textContent='';}
async function loadCurrencies(){
 if(fxBusy||!accessSession?.user)return;fxBusy=true;$('fx-feedback').textContent='Wisselkoersen laden…';
 try{
  const response=await apiFetch('api/fx?day='+encodeURIComponent($('fx-day').value));const result=await response.json();if(!response.ok)throw Error(result.error);
  if(!accessSession?.user)return;fxState=result;
  for(const [id,preferred] of [['fx-from','USD'],['fx-to','EUR'],['fx-history-currency','USD']]){const select=$(id),previous=select.value;select.replaceChildren();for(const item of result.currencies){const option=document.createElement('option');option.value=item.code;option.textContent=item.code+' · '+item.name;select.append(option);}select.value=result.currencies.some(c=>c.code===previous)?previous:preferred;}
  $('fx-rates').replaceChildren();for(const item of result.currencies){const row=document.createElement('tr');for(const value of [item.code,item.name,item.to_eur===null?'Geen koers op deze datum':Number(item.to_eur).toLocaleString('nl-NL',{maximumSignificantDigits:10}),item.rate_on??'—'])cell(row,value);$('fx-rates').append(row);}
  await loadFxHistory();
  $('fx-audit').replaceChildren();for(const item of result.conversions){const row=document.createElement('tr');for(const value of [item.requested_on,item.kind,item.original_amount+' '+item.source_currency,item.converted_amount+' '+item.target_currency,item.rate,item.rate_on,item.source])cell(row,value);$('fx-audit').append(row);}
  $('fx-feedback').textContent=result.error??result.currencies.length+' valuta / rekeneenheden · opgeslagen dagkoersen · 1 valuta-eenheid in EUR';
 }catch(error){$('fx-feedback').textContent=error.message;}finally{fxBusy=false;}
}
function bindCurrencies(){
 const today=new Date().toLocaleDateString('en-CA');$('fx-day').value=today;$('fx-convert-day').value=today;
 $('fx-history-currency').addEventListener('change',()=>loadFxHistory().catch(error=>{$('fx-history-note').textContent=error.message;}));
 $('fx-date-form').addEventListener('submit',event=>{event.preventDefault();loadCurrencies();});
 $('fx-convert-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{
  const result=await jsonAction('api/fx/convert',{amount:$('fx-amount').value,from:$('fx-from').value,to:$('fx-to').value,day:$('fx-convert-day').value});
  if(!accessSession?.user)return;
  $('fx-result').textContent=result.amount+' '+result.from+' = '+Number(result.converted).toLocaleString('nl-NL',{maximumSignificantDigits:12})+' '+result.to+' · factor '+result.rate+' · gevraagde datum '+result.requested_on+' · koersdatum '+result.rate_on+' · '+result.source;
  await loadCurrencies();
 }catch(error){$('fx-result').textContent=error.message;}finally{button.disabled=false;}});
}

async function loadFxHistory(){
 const response=await apiFetch('api/fx/history?currency='+encodeURIComponent($('fx-history-currency').value));const data=await response.json();if(!response.ok)throw Error(data.error);
 if(!accessSession?.user)return;
 $('fx-history').replaceChildren();for(const item of data.rates){const row=document.createElement('tr');for(const value of [item.day,item.base+' → '+item.quote,item.rate,item.source])cell(row,value);$('fx-history').append(row);}
 $('fx-history-note').textContent=data.rates.length?'Opgeslagen historie: '+data.rates[0].day+' tot '+data.rates[data.rates.length-1].day:'Nog geen opgeslagen dagkoersen voor deze valuta. Kies een datum in het overzicht of de rekenmachine.';
}
