import { config } from '../config.js';
const escape = value => String(value ?? 'Not returned').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function renderMediaInspection(data) {
  const artifacts = data.storedArtifacts||[];
  return `<section class="panel media-inspection-panel"><div class="panel-heading"><div><span class="eyebrow">PHASE 5 · REAL FILE INSPECTION</span><h2>Media metadata & integrity</h2><p>Inspect uploaded bytes for container, codecs, dimensions, audio properties, and SHA-256 consistency.</p></div><button type="button" class="button" data-test-upload>+ Add test files</button></div><form id="mediaInspectionForm" class="media-inspection-form"><label>Uploaded media<select name="artifactId" ${!artifacts.length?'disabled':''}>${artifacts.map(row=>`<option value="${escape(row.artifact_id)}">${escape(row.original_name)} · ${escape(row.media_type)} · ${escape(row.artifact_id)}</option>`).join('')||'<option>No uploaded media bytes available</option>'}</select></label><button class="button primary" type="submit" ${!artifacts.length?'disabled':''}>Inspect file</button><button class="button" type="button" data-inspection-load ${!artifacts.length?'disabled':''}>Load last inspection</button><button class="button" type="button" data-media-preview>Play / preview</button><button class="button" type="button" data-audio-waveform ${!artifacts.length?'disabled':''}>Open WAV waveform</button></form><p class="memory-recall-note">Supports WAV, MP4/MOV with ftyp, Matroska/WebM, PNG, and JPEG signatures. This does not run deepfake detection.</p><div id="mediaInspectionResult" aria-live="polite"><p class="memory-recall-note">${artifacts.length?'Choose a file to inspect its stored bytes or load a saved result.':'Upload audio, video, or an image, then refresh this page. Fixture filenames do not contain real evidence bytes.'}</p></div><div id="mediaPreviewRoot" aria-live="polite"></div><div id="audioWaveformRoot" aria-live="polite"></div></section>`;
}

function renderResult(result) {
  if(!result)return '<div class="summary-empty">No inspection has been saved for this file.</div>';
  return `<article class="media-inspection-result"><span class="agent-state ${result.status==='completed'?'derived':'candidate'}">${escape(result.status)}</span><h3>${result.integrityMatch?'Registered digest matches':'Digest mismatch · parsing blocked'}</h3><small>${escape(result.artifactId)} · ${escape(result.createdAt)} · ${escape(result.byteSize)} bytes</small><p class="report-digest">SHA-256 ${escape(result.sha256)}</p>${result.error?`<p>${escape(result.error.message)}</p>`:''}<div class="inspection-facts"><div><small>Container</small><strong>${escape(result.format)}</strong></div><div><small>Duration (seconds)</small><strong>${escape(result.durationSeconds)}</strong></div><div><small>Deepfake detector</small><strong>Not run</strong></div></div>${result.streams.length?`<div class="table-wrap"><table class="data-table"><thead><tr><th>Stream</th><th>Codec</th><th>Dimensions</th><th>Audio</th></tr></thead><tbody>${result.streams.map(row=>`<tr><td>${escape(row.index)} · ${escape(row.codec_type)}</td><td>${escape(row.codec_name)}</td><td>${row.width&&row.height?escape(row.width)+' × '+escape(row.height):'—'}</td><td>${row.sample_rate?escape(row.sample_rate)+' Hz · '+escape(row.channels)+' channels':'—'}</td></tr>`).join('')}</tbody></table></div>`:''}<p class="memory-recall-note">Metadata is a parser observation. It does not determine whether media is authentic or manipulated.</p></article>`;
}

export function initializeMediaInspection(repository,getCaseId) {
  let sequence = 0;
  async function run(form,readOnly) {
    const result = document.getElementById('mediaInspectionResult');
    if(form.getAttribute('aria-busy')==='true')return;
    const current = ++sequence, artifactId = form.elements.artifactId.value;
    if(!artifactId)return;
    form.setAttribute('aria-busy','true');
    form.querySelectorAll('button,select').forEach(control=>control.disabled=true);
    result.textContent = readOnly?'Reading the saved inspection…':'Hashing stored bytes and running bounded metadata inspection…';
    if(form.dataset.artifact !== artifactId){form.dataset.artifact=artifactId;delete form.dataset.requestKey;}
    form.dataset.requestKey ||= crypto.randomUUID();
    try {
      const data = readOnly?await repository.loadArtifactInspection(getCaseId(),artifactId):await repository.inspectArtifact(getCaseId(),artifactId,form.dataset.requestKey);
      if(result.isConnected&&current===sequence)result.innerHTML=renderResult(data);
      if(!readOnly)delete form.dataset.requestKey;
    }catch(error){if(result.isConnected&&current===sequence)result.textContent=error.message||'Inspection could not be completed.';}
    finally{if(form.isConnected){form.setAttribute('aria-busy','false');form.querySelectorAll('button,select').forEach(control=>control.disabled=false);}}
  }
  document.addEventListener('click',event=>{
    const trigger=event.target.closest('[data-media-preview]');if(!trigger)return;
    const id=trigger.closest('form').elements.artifactId.value,select=trigger.closest('form').elements.artifactId;
    const label=select.selectedOptions[0]?.textContent||'',root=document.getElementById('mediaPreviewRoot');
    const url=String(config.apiBaseUrl||'').replace(/\/$/,'')+'/api/v1/cases/'+encodeURIComponent(getCaseId())+'/artifacts/'+encodeURIComponent(id)+'/preview';
    root.querySelectorAll('audio,video').forEach(p=>p.pause());
    const tag=label.includes(' · Video · ')?'video':label.includes(' · Audio · ')?'audio':label.includes(' · Image · ')?'img':null;
    if(!tag){root.textContent='Select an uploaded video, audio or image.';return;}
    root.innerHTML=`<section class="test-media-preview"><h3>${escape(label)}</h3><${tag} ${tag==='img'?'alt="Uploaded image preview"':'controls preload="metadata"'} src="${escape(url)}"></${tag}><p>Original stored bytes. No detector or authenticity verdict. Browser codec support may vary.</p></section>`;
    const media=root.querySelector(tag);media.addEventListener('error',()=>{root.querySelector('p').textContent='Preview unavailable: unsupported format/codec, missing bytes or failed integrity check. Try Inspect file for details.';});
  });
  document.addEventListener('change',event=>{if(event.target.matches('#mediaInspectionForm select')){const root=document.getElementById('mediaPreviewRoot');root?.querySelectorAll('audio,video').forEach(p=>p.pause());if(root)root.innerHTML='';}});
  window.addEventListener('hashchange',()=>document.querySelectorAll('#mediaPreviewRoot audio,#mediaPreviewRoot video').forEach(p=>p.pause()));
  document.addEventListener('submit',event=>{if(event.target.id==='mediaInspectionForm'){event.preventDefault();run(event.target,false);}});
  document.addEventListener('click',event=>{if(event.target.closest('[data-inspection-load]'))run(event.target.closest('form'),true);});
}
