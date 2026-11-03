/* Local backup inventory and explicit file actions in the shared modal. */
let backupFilesGeneration=0,backupFileSelection=null,backupFileBusy=false;
function clearBackupFiles(){backupFilesGeneration++;backupFileSelection=null;$('backup-files').replaceChildren();$('backup-files-summary').textContent='';$('backup-files-feedback').textContent='';}
async function loadBackupFiles(){
 const generation=++backupFilesGeneration;if(accessSession?.user?.role!=='admin')return;
 $('backup-files-feedback').textContent=ui('Bestanden laden…');
 try{
  const response=await apiFetch('api/portfolio/files');const data=await response.json();if(!response.ok)throw Error(data.error);
  if(generation!==backupFilesGeneration||accessSession?.user?.role!=='admin')return;
  $('backup-files').replaceChildren();$('backup-files-feedback').textContent='';
  $('backup-files-summary').textContent=new Intl.NumberFormat(appLocale()).format(data.files.length)+' · '+ui('Back-ups')+': '+resourceBytes(data.backup_bytes)+' · '+ui('Updatebestanden')+': '+resourceBytes(data.update_bytes)+' · '+ui('Totaal')+': '+resourceBytes(data.total_bytes);
  const kinds={backup:ui('Back-up'),migration:ui('Vóór database-update'),restore:ui('Vóór herstel'),deletion:ui('Vóór verwijderen'),conversion:ui('Vóór omboeking'),update:ui('Updatebestand')};
  for(const file of data.files){
   const row=document.createElement('tr');const name=cell(row,file.name);name.className='backup-file-name';cell(row,kinds[file.kind]);cell(row,new Date(file.modified*1000).toLocaleString(appLocale()));cell(row,resourceBytes(file.bytes));
   const actionCell=cell(row,''),actions=document.createElement('div');actions.className='backup-file-actions';actionCell.append(actions);
   const download=document.createElement('a');download.textContent=ui('Downloaden');download.href='api/portfolio/file?name='+encodeURIComponent(file.name);actions.append(download);
   if(file.restorable){const restore=document.createElement('button');restore.type='button';restore.textContent=ui('Herstellen');restore.addEventListener('click',()=>reviewBackupFile(file,true));actions.append(restore);}
   const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent=ui('Verwijderen');remove.addEventListener('click',()=>reviewBackupFile(file,false));actions.append(remove);[ui('Bestand'),ui('Soort'),ui('Gewijzigd'),ui('Grootte'),ui('Acties')].forEach((label,i)=>{row.cells[i].dataset.label=label;});$('backup-files').append(row);
  }
  if(!data.files.length)$('backup-files-feedback').textContent=ui('Geen opgeslagen back-ups of updatebestanden.');
 }catch(error){if(generation===backupFilesGeneration)$('backup-files-feedback').textContent=error.message;}
}
function reviewBackupFile(file,restoring){
 if(backupFileBusy)return;backupFileSelection={...file,restoring};$('backup-file-name').textContent=file.name+' · '+resourceBytes(file.bytes);$('backup-file-explanation').textContent=restoring?ui('Je huidige portefeuille wordt vervangen. Vooraf wordt een veiligheidsback-up gemaakt. Gebruikers en beveiliging blijven behouden.'):ui('Dit bestand wordt definitief verwijderd. Je huidige portefeuille blijft behouden.');
 $('backup-file-confirm').checked=false;$('backup-file-submit').disabled=true;$('backup-file-submit').textContent=restoring?ui('Herstellen'):ui('Verwijderen');$('backup-file-feedback').textContent='';openPopup('backup-file-editor');
}
$('backup-files-refresh').addEventListener('click',loadBackupFiles);
$('backup-file-confirm').addEventListener('change',()=>{$('backup-file-submit').disabled=!$('backup-file-confirm').checked||backupFileBusy;});
$('backup-file-cancel').addEventListener('click',()=>closePopup('backup-file-editor'));
$('backup-file-form').addEventListener('submit',async event=>{
 event.preventDefault();if(backupFileBusy||!backupFileSelection||!$('backup-file-confirm').checked)return;
 const file=backupFileSelection;backupFileBusy=true;$('backup-file-submit').disabled=true;
 try{
  await jsonAction(file.restoring?'api/portfolio/file-restore':'api/portfolio/file-delete',{name:file.name,revision:file.revision,confirmation:file.restoring?'RESTORE':'DELETE'});
  closePopup('backup-file-editor');
  if(file.restoring){stateETag=null;await startSession();if(accessSession)$('backup-files-feedback').textContent=ui('Portefeuille hersteld. Gebruikers en rollen zijn behouden.');else $('login-feedback').textContent=ui('Portefeuille hersteld. Meld je opnieuw aan.');}
  else {await loadBackupFiles();$('backup-files-feedback').textContent=ui('Bestand verwijderd.');}
 }catch(error){$('backup-file-feedback').textContent=error.message;}finally{backupFileBusy=false;$('backup-file-submit').disabled=!$('backup-file-confirm').checked;}
});
