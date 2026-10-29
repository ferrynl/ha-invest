/* Non-blocking, route-scoped feedback. No financial data or session storage. */
var ui=globalThis.HomeInvestTranslate||((value)=>value);
const pageLoadingRequests=new Map();let pageLoadingSequence=0,pageLoadingDelay=null,pageLoadingTick=null;
const loadingRoute=()=>location.hash.split('?')[0]||'#home';
function refreshPageLoading(){
 clearTimeout(pageLoadingTick);pageLoadingTick=null;
 const booting=document.body.classList.contains('booting'),locked=document.body.classList.contains('locked');
 const active=[...pageLoadingRequests.values()].filter(item=>item.route===loadingRoute());
 const busy=!locked&&(booting||active.length>0),indicator=document.getElementById('loading-indicator');
 const age=active.length?Date.now()-Math.min(...active.map(item=>item.started)):0;
 indicator.hidden=!busy||(!booting&&indicator.hidden&&age<180);document.getElementById('main-content').setAttribute('aria-busy',String(busy));
 if(!busy||indicator.hidden){if(busy&&pageLoadingDelay===null)pageLoadingDelay=setTimeout(()=>{pageLoadingDelay=null;refreshPageLoading();},Math.max(1,180-age));return;}
 document.getElementById('loading-description').textContent=age>=8000?ui('Dit duurt iets langer. Je gegevens worden verwerkt…'):ui('Je portefeuille wordt geladen…');
 if(age<8000&&active.length)pageLoadingTick=setTimeout(refreshPageLoading,8000-age);
}
function beginPageLoading(){
 const token=++pageLoadingSequence;pageLoadingRequests.set(token,{route:loadingRoute(),started:Date.now()});
 if(document.body.classList.contains('booting'))refreshPageLoading();
 else if(pageLoadingDelay===null)pageLoadingDelay=setTimeout(()=>{pageLoadingDelay=null;refreshPageLoading();},180);
 let done=false;return ()=>{if(done)return;done=true;pageLoadingRequests.delete(token);refreshPageLoading();};
}
window.addEventListener('hashchange',refreshPageLoading);
refreshPageLoading();
