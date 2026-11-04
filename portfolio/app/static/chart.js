/* Pure period calculations shared by the dashboard and its tests. */
function chartPeriodStart(endDay, range) {
 const end = new Date(endDay+'T00:00:00Z');
 if(range==='ALL')return '0001-01-01';
 if(range==='YTD')return end.getUTCFullYear()+'-01-01';
 if(range==='1D')return endDay;
 if(range==='5D'){end.setUTCDate(end.getUTCDate()-4);return end.toISOString().slice(0,10);}
 if(range==='1W'){end.setUTCDate(end.getUTCDate()-6);return end.toISOString().slice(0,10);}
 const months={'1M':1,'3M':3,'6M':6,'1Y':12,'5Y':60}[range]??1;
 const day=end.getUTCDate();end.setUTCDate(1);end.setUTCMonth(end.getUTCMonth()-months);
 const last=new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()+1,0)).getUTCDate();
 end.setUTCDate(Math.min(day,last));return end.toISOString().slice(0,10);
}
function chartPointsSince(history,start){
 let first=0,last=history.length;
 while(first<last){
  const middle=(first+last)>>1;
  if(history[middle].day<start)first=middle+1;
  else last=middle;
 }
 return history.slice(first);
}
function chartPeriodPoints(history, range) {
 return history.length?chartPointsSince(history,chartPeriodStart(history.at(-1).day,range)):[];
}
function chartProfitValue(point){const scoped=point?.return_gain!=null&&point?.return_invested!=null,raw=scoped?point.return_gain:point?.total_gain,basis=Number(scoped?point.return_invested:point?.invested),gain=Number(raw);return raw==null||point?.missing>0&&!scoped||!Number.isFinite(basis)||!Number.isFinite(gain)||basis<=0?null:gain/basis*100;}
function chartRuns(values){const runs=[];let run=[];values.forEach((v,i)=>{if(v==null||!Number.isFinite(v)){if(run.length)runs.push(run);run=[];}else run.push({i,value:v});});if(run.length)runs.push(run);return runs;}
if(typeof module!=='undefined')module.exports={chartPeriodStart,chartPeriodPoints,chartProfitValue,chartRuns};
