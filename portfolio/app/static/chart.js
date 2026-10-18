/* Pure period calculations shared by the dashboard and its tests. */
function chartPeriodStart(endDay, range) {
 const end = new Date(endDay+'T00:00:00Z');
 if(range==='ALL')return '0001-01-01';
 if(range==='YTD')return end.getUTCFullYear()+'-01-01';
 if(range==='1W'){end.setUTCDate(end.getUTCDate()-6);return end.toISOString().slice(0,10);}
 const months={'1M':1,'3M':3,'6M':6,'1Y':12}[range]??1;
 const day=end.getUTCDate();end.setUTCDate(1);end.setUTCMonth(end.getUTCMonth()-months);
 const last=new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()+1,0)).getUTCDate();
 end.setUTCDate(Math.min(day,last));return end.toISOString().slice(0,10);
}
function chartPeriodPoints(history, range) {
 if(!history.length)return [];
 const start=chartPeriodStart(history.at(-1).day,range);
 return history.filter(point=>point.day>=start);
}
if(typeof module!=='undefined')module.exports={chartPeriodStart,chartPeriodPoints};
