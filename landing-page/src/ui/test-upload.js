const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function inferTestType(file) {
 const ext=file.name.split('.').pop().toLowerCase();
 if(/^(mp4|mov|m4v|webm|mkv|avi)$/.test(ext))return 'Video';
 if(/^(wav|mp3|m4a|aac|flac|ogg)$/.test(ext))return 'Audio';
 if(/^(jpg|jpeg|png|gif|webp)$/.test(ext))return 'Image';
 if(/^(pcap|pcapng|json|csv|evtx|log)$/.test(ext))return 'Log / export';
 if(/^(pdf|txt|docx)$/.test(ext))return 'Document';
 return 'Other';
}

export function initializeTestUpload(repository,getCaseId,onUploaded) {
 document.addEventListener('click',event=>{
  if(!event.target.closest('[data-test-upload]'))return;
  const root=document.getElementById('modalRoot');
  root.innerHTML=`<div class="modal-backdrop"><section class="modal test-upload-modal" role="dialog" aria-modal="true" aria-label="Add test files"><div class="modal-head"><div><span class="eyebrow">LOCAL TEST INTAKE</span><h2>+ Add test files</h2></div><button type="button" class="icon-button" data-action="modal-close" aria-label="Close">×</button></div><form id="testUploadForm"><div class="modal-body"><p>Add media or other artifacts to <strong>${esc(getCaseId())}</strong>. Original bytes are preserved and hashed. Files stay in this local case.</p><label class="test-file-picker">Choose videos, audio, images or other files<input type="file" name="file" multiple required /><small>Up to 20 files · 512 MB each · 1 GB per batch</small></label><div class="form-field"><label>Artifact type<select name="media_type"><option value="auto">Auto-detect by extension</option><option>Video</option><option>Audio</option><option>Image</option><option>Document</option><option>Log / export</option><option>Disk image</option><option>Other</option></select></label></div><div class="form-field"><label>Source / test note<input name="source_label" value="User supplied functional test" maxlength="250" required /></label></div><label class="test-inspect-choice"><input type="checkbox" name="inspect" checked /> Inspect supported media after upload</label><p class="memory-recall-note">Metadata inspection: WAV, MP4/MOV, WebM/Matroska, JPEG and PNG. Other formats can be stored and hashed. Deepfake detection is not configured.</p><div id="testUploadResults" role="status" aria-live="polite">Choose your files to start.</div></div><div class="modal-footer"><a class="button" href="./cases.html">Public test cases</a><button type="submit" class="button primary">Upload &amp; test</button></div></form></section></div>`;
  root.querySelector('input[type=file]').focus();
 });
 document.addEventListener('change',event=>{
  if(!event.target.matches('#testUploadForm input[type=file]'))return;
  const files=[...event.target.files],results=document.getElementById('testUploadResults');
  results.innerHTML=files.map(f=>`<div class="test-file-row"><strong>${esc(f.name)}</strong><small>${esc(inferTestType(f))} · ${(f.size/1024/1024).toFixed(2)} MB</small></div>`).join('');
 });
 document.addEventListener('submit',async event=>{
  if(event.target.id!=='testUploadForm')return;event.preventDefault();
  const form=event.target;if(form.dataset.busy)return;
  const files=[...form.elements.file.files],caseId=getCaseId(),results=document.getElementById('testUploadResults');
  if(!files.length||files.length>20||files.some(f=>f.size>512*1024*1024)||files.reduce((n,f)=>n+f.size,0)>1024**3){results.textContent='Choose 1–20 files, at most 512 MB each and 1 GB in total.';return;}
  const choice=form.elements.media_type.value,inspect=form.elements.inspect.checked;
  form.dataset.busy='true';form.querySelectorAll('button,input,select').forEach(c=>c.disabled=true);results.textContent='';let uploaded=0;
  for(const file of files){
   const row=document.createElement('div');row.className='test-file-row';row.textContent=file.name+' · uploading and hashing…';results.append(row);
   try{
    const mediaType=choice==='auto'?inferTestType(file):choice;
    const response=await repository.uploadEvidence(caseId,form,{file,mediaType});uploaded++;
    let state='Stored · SHA-256 registered';
    if(inspect&&['Audio','Video','Image'].includes(mediaType)){
     try{const result=await repository.inspectArtifact(caseId,response.data.id,crypto.randomUUID());state+=' · inspection '+result.status;}catch(error){state+=' · inspection unavailable: '+error.message;}
    }
    row.innerHTML=`<strong>${esc(file.name)}</strong><small>${esc(response.data.id)} · ${esc(state)}</small>`;
   }catch(error){row.innerHTML=`<strong>${esc(file.name)}</strong><small>Upload failed: ${esc(error.message)}</small>`;}
  }
  const summary=document.createElement('p');summary.textContent=`${uploaded} of ${files.length} files stored. Open Media analysis for playback, metadata and WAV waveform testing.`;results.append(summary);
  if(uploaded){try{await onUploaded();}catch{summary.textContent+=' Refresh the page to load the new files.';}}
  form.elements.file.value='';
  delete form.dataset.busy;form.querySelectorAll('button,input,select').forEach(c=>c.disabled=false);
 });
}

// Playback metadata drives the source ruler; no sample duration is substituted.
document.addEventListener('loadedmetadata',event=>{
 const media=event.target;if(!media.matches?.('.deepfake-native-media')||!Number.isFinite(media.duration))return;
 const ruler=document.querySelector('.editor-timeline .time-ruler');if(ruler)ruler.innerHTML=[0,.25,.5,.75,1].map(f=>'<span>'+(media.duration*f).toFixed(2)+' s</span>').join('');
},true);
document.addEventListener('timeupdate',event=>{
 const media=event.target;if(!media.matches?.('.deepfake-native-media')||!media.duration)return;
 document.querySelectorAll('.editor-timeline .editor-playhead').forEach(line=>line.style.left=Math.min(100,media.currentTime/media.duration*100)+'%');
},true);
document.addEventListener('error',event=>{
 if(!event.target.matches?.('.deepfake-native-media'))return;
 const note=document.querySelector('.deepfake-preview-note');if(note)note.textContent='Preview unavailable: unsupported codec/format, missing bytes or failed integrity check. Open Media analysis and Inspect file for details.';
},true);
