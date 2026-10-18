const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors={elevated:'#f16b75',lower:'#53c8a3',uncertain:'#e9b65f',unassessed:'#8092a5'};
export function renderAudioScreen(active,media){
 return `<section id="audioScreenWorkbench" class="audio-screen-workbench" data-screen-artifact="${esc(active?.id||'')}"><div class="screen-source-bar"><label>Source file<select data-screen-source>${media.map(m=>`<option value="${esc(m.id)}" ${m.hasStoredBytes===false?'disabled':''} ${m.id===active?.id?'selected':''}>${esc(m.name)}${m.hasStoredBytes===false?' · bytes unavailable':''}</option>`).join('')}</select></label><button class="button" data-screen-play>▶ Play / pause</button><button class="button" data-test-upload>+ Add media</button></div><div class="screen-research-warning"><strong>Research audio screen · not a reliable authenticity verdict</strong><p>AASIST-L examines speech audio only, including audio extracted from video. An initial local test over-flagged known natural speech. Visual manipulation is not assessed; music and other domains can produce misleading scores.</p></div><label class="screen-ack"><input type="checkbox" data-screen-ack /> I understand this is experimental audio-only screening with false positives.</label><div class="screen-analysis-actions"><button class="button primary" data-screen-run>Analyze audio &amp; show timed waveform</button><span data-screen-status role="status">Select a source and run analysis to produce a measured waveform and research cues.</span></div><div data-screen-result></div></section>`;
}

export function initializeAudioScreen(repository,getCaseId){
 let generation=0;
 function render(root,data){
  root._audioScreen=data;
  const duration=data.durationSeconds,bins=data.bins,peak=Math.max(.001,...bins.flatMap(b=>[Math.abs(b.min),Math.abs(b.max)]));
  const windows=data.segments;
  const marks=bins.map((b,i)=>{
   const t=(i+.5)/bins.length*duration;
   const window=windows.filter(w=>t>=w.startSeconds&&t<=w.endSeconds).sort((a,b)=>Math.abs(t-(a.startSeconds+a.endSeconds)/2)-Math.abs(t-(b.startSeconds+b.endSeconds)/2))[0];
   const color=colors[window?.level||'unassessed'],x=(i+.5)/bins.length*1000;
   return `<g><path d="M${x} ${135-b.max/peak*72}V${135-b.min/peak*72}" stroke="#70daef" stroke-width="1.2"/><path d="M${x} 48v${-Math.max(2,Math.min(28,b.rms/peak*100))}M${x} 222v${Math.max(2,Math.min(28,b.rms/peak*100))}" stroke="${color}" stroke-width="1.2"/></g>`;
  }).join('');
  const result=root.querySelector('[data-screen-result]');
  result.innerHTML=`<div class="screen-signal-head"><strong>MEASURED AUDIO / TIMED MODEL CUES</strong><span>${duration.toFixed(3)} s · 16 kHz mono · AASIST-L</span></div><div class="screen-signal-legend"><span style="color:${colors.elevated}">● Red: elevated model cue</span><span style="color:${colors.lower}">● Green: lower cue, not verified real</span><span style="color:${colors.uncertain}">● Amber: uncertain / short input</span><span>● Gray: quiet / unassessed</span></div><div class="screen-wave-stage" role="group" aria-label="Measured audio waveform with experimental window colors"><svg viewBox="0 0 1000 270" preserveAspectRatio="none" aria-label="Cyan waveform is measured amplitude; colored bands show uncalibrated model cues"><path d="M0 135H1000M0 48H1000M0 222H1000" stroke="#284051" stroke-width="1"/>${marks}<path data-screen-playhead d="M0 0V270" stroke="#f7d392" stroke-width="2"/></svg><div class="screen-wave-tooltip" hidden></div></div><label class="screen-seek-label">Playback position <output data-screen-time>0.00 s</output><input type="range" data-screen-seek min="0" max="${duration}" value="0" step="0.01" /></label><p class="screen-signal-note">Click or hover the signal to inspect a time. Cyan is actual amplitude; upper/lower bands are measured RMS colored by model output. Display gain ${(1/peak).toFixed(2)}×. Colors are screening cues, not ground truth.</p><div class="screen-window-list">${windows.map((w,i)=>`<button type="button" data-screen-window="${i}" style="--window-color:${colors[w.level]}"><strong>${w.startSeconds.toFixed(2)}–${w.endSeconds.toFixed(2)} s</strong><span>${esc(w.level)} · ${w.score===null?'not scored':(w.score*100).toFixed(1)+' model score /100'}</span><small>${w.shortInputRepeated?'Short input repeated for model; no exact edit localization.':'Overlapping 4.04 s context; not exact manipulation boundaries.'}</small></button>`).join('')}</div><details><summary>Model provenance, thresholds and limitations</summary><p>${esc(data.model.name)} · revision ${esc(data.model.revision)} · weights SHA-256 ${esc(data.model.weightsSha256)}</p><p>Source SHA-256 ${esc(data.sha256)}</p><p>${esc(data.scoreMeaning)} Display thresholds 0.35 / 0.75 are not calibrated.</p><ul>${data.limitations.map(l=>`<li>${esc(l)}</li>`).join('')}</ul></details>`;
  root.querySelector('[data-screen-status]').textContent=`Saved ${data.id} · ${windows.length} research windows · ${data.elapsedSeconds}s processing. Not locally validated.`;
 }
 async function load(root){
  const id=root.dataset.screenArtifact,current=++generation;if(!id)return;
  try{const data=await repository.loadAudioScreen(getCaseId(),id);if(data&&root.isConnected&&current===generation)render(root,data);}catch{/* No saved result is not a detector verdict. */}
 }
 new MutationObserver(()=>{const root=document.querySelector('[data-screen-artifact]');if(root&&!root.dataset.screenMounted){root.dataset.screenMounted='true';load(root);}}).observe(document.body,{childList:true,subtree:true});
 document.addEventListener('change',e=>{
  if(!e.target.matches('[data-screen-source]'))return;
  document.querySelector(`[data-action="deepfake-select"][data-id="${CSS.escape(e.target.value)}"]`)?.click();
 });
 document.addEventListener('click',async e=>{
  if(e.target.closest('[data-screen-scroll]')){document.getElementById('audioScreenWorkbench')?.scrollIntoView({block:'start'});return;}
  const root=e.target.closest('[data-screen-artifact]');if(!root)return;
  const media=document.querySelector('audio.deepfake-native-media,video.deepfake-native-media');
  if(e.target.closest('[data-screen-play]')){const status=root.querySelector('[data-screen-status]');if(!media){status.textContent='Choose a video or audio file with uploaded bytes.';return;}try{if(media.paused){await media.play();status.textContent='Playing source media.';}else{media.pause();status.textContent='Playback paused.';}}catch(error){status.textContent='Playback failed: '+error.message+' Choose an uploaded MP4/WebM/WAV file.';}return;}
  if(e.target.closest('[data-screen-run]')){
   const button=e.target.closest('[data-screen-run]'),status=root.querySelector('[data-screen-status]');
   if(!root.querySelector('[data-screen-ack]').checked){status.textContent='Acknowledge the experimental audio-only scope before running.';return;}
   button.disabled=true;status.textContent='Verifying bytes, decoding audio and running AASIST-L windows locally…';
   try{const data=await repository.runAudioScreen(getCaseId(),root.dataset.screenArtifact,crypto.randomUUID());if(root.isConnected)render(root,data);}catch(error){if(root.isConnected)status.textContent=error.message;}
   finally{if(button.isConnected)button.disabled=false;}return;
  }
  const windowButton=e.target.closest('[data-screen-window]');
  if(windowButton&&media){media.currentTime=root._audioScreen.segments[Number(windowButton.dataset.screenWindow)].startSeconds;return;}
  const stage=e.target.closest('.screen-wave-stage');if(stage&&media&&root._audioScreen){const rect=stage.getBoundingClientRect();media.currentTime=Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width))*root._audioScreen.durationSeconds;}
 });
 document.addEventListener('input',e=>{if(e.target.matches('[data-screen-seek]')){const media=document.querySelector('audio.deepfake-native-media,video.deepfake-native-media');if(media)media.currentTime=Number(e.target.value);}});
 document.addEventListener('timeupdate',e=>{
  if(!e.target.matches?.('.deepfake-native-media'))return;const root=document.querySelector('[data-screen-artifact]');if(!root?._audioScreen)return;
  const t=e.target.currentTime,d=root._audioScreen.durationSeconds;
  root.querySelector('[data-screen-time]').textContent=t.toFixed(2)+' s';root.querySelector('[data-screen-seek]').value=t;
  root.querySelector('[data-screen-playhead]').setAttribute('d',`M${t/d*1000} 0V270`);
 },true);
 document.addEventListener('pointermove',e=>{
  const stage=e.target.closest('.screen-wave-stage');if(!stage)return;const root=stage.closest('[data-screen-artifact]'),data=root._audioScreen;
  const rect=stage.getBoundingClientRect(),t=Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width))*data.durationSeconds;
  const window=data.segments.filter(w=>t>=w.startSeconds&&t<=w.endSeconds).sort((a,b)=>Math.abs(t-(a.startSeconds+a.endSeconds)/2)-Math.abs(t-(b.startSeconds+b.endSeconds)/2))[0];
  const tip=stage.querySelector('.screen-wave-tooltip');tip.hidden=false;tip.style.left=Math.min(rect.width-220,Math.max(0,e.clientX-rect.left+8))+'px';
  tip.textContent=t.toFixed(2)+' s · '+(window?.level||'unassessed')+' · '+(window?.score==null?'No score':(window.score*100).toFixed(1)+'/100 uncalibrated');
 });
 document.addEventListener('pointerout',e=>{const stage=e.target.closest('.screen-wave-stage');if(stage&&!stage.contains(e.relatedTarget))stage.querySelector('.screen-wave-tooltip').hidden=true;});
}
