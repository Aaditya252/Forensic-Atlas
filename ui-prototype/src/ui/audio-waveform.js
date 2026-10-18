const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function initializeAudioWaveform(repository,getCaseId) {
  let sequence=0;
  window.addEventListener('hashchange',()=>document.querySelector('#audioWaveformRoot audio')?.pause());
  document.addEventListener('change',event=>{
    if(event.target.matches('#mediaInspectionForm select')){
      sequence++;
      const root=document.getElementById('audioWaveformRoot');
      root?.querySelector('audio')?.pause();
      if(root)root.textContent='Audio selection changed. Open the selected file’s waveform to continue.';
    }
  });
  document.addEventListener('click',async event=>{
    const trigger=event.target.closest('[data-audio-waveform]');
    if(!trigger||trigger.disabled)return;
    const form=trigger.closest('form'),artifactId=form.elements.artifactId.value;
    const root=document.getElementById('audioWaveformRoot'),current=++sequence;
    root.querySelector('audio')?.pause();
    trigger.disabled=true;root.setAttribute('aria-busy','true');root.textContent='Reading PCM samples and checking the registered digest…';
    try{
      const data=await repository.loadAudioWaveform(getCaseId(),artifactId);
      if(!root.isConnected||current!==sequence)return;
      const bins=data.bins,gain=data.peakAmplitude>0?1/data.peakAmplitude:1;
      const bars=bins.map((bin,index)=>{const x=(index+.5)/bins.length*1000;return `M${x.toFixed(2)},${(110-bin.max*gain*90).toFixed(2)}V${(110-bin.min*gain*90).toFixed(2)}`;}).join(' ');
      const rms=bins.map((bin,index)=>`${index?'L':'M'}${((index+.5)/bins.length*1000).toFixed(2)},${(110-bin.rms*gain*90).toFixed(2)}`).join(' ');
      const preview=`/api/v1/cases/${encodeURIComponent(getCaseId())}/artifacts/${encodeURIComponent(artifactId)}/audio-preview`;
      root.innerHTML=`<section class="pcm-waveform"><div class="panel-heading"><div><span class="eyebrow">PHASE 7 · MEASURED PCM SIGNAL</span><h3>Audio signal workspace</h3><p>${escape(artifactId)} · ${data.sampleRate} Hz · ${data.channels} channel(s) · ${data.bitsPerSample}-bit PCM · ${data.durationSeconds.toFixed(3)} s</p></div></div><div class="pcm-wave-legend"><span>● Cyan: measured min/max</span><span>● Purple: RMS envelope</span><span>Display gain ${gain.toFixed(2)}× · audio unchanged</span></div><div class="pcm-wave-stage"><svg class="pcm-wave-svg" viewBox="0 0 1000 220" preserveAspectRatio="none" aria-label="Measured waveform. Use the time slider below for keyboard seeking." role="img"><path d="M0 110H1000" stroke="#284353"/><path d="${bars}" stroke="#56d9e8" stroke-width="2" fill="none"/><path d="${rms}" stroke="#c5a3ff" stroke-width="1.5" fill="none"/><path data-wave-playhead d="M0 0V220" stroke="#f4bf69" stroke-width="1.5"/></svg><div class="pcm-wave-tooltip" hidden></div></div><div class="pcm-wave-times"><span>0.000 s</span><span>${(data.durationSeconds/2).toFixed(3)} s</span><span>${data.durationSeconds.toFixed(3)} s</span></div><label class="pcm-time-label">Playback position <output data-wave-position>0.000 s</output><input data-wave-seek type="range" min="0" max="${data.durationSeconds}" step="0.001" value="0" aria-label="Audio playback position in seconds" /></label><audio controls preload="metadata" src="${preview}">Audio playback is unavailable in this browser.</audio><div class="inspection-facts"><div><small>Measured peak amplitude</small><strong>${data.peakAmplitude.toFixed(5)}</strong></div><div><small>Measured RMS amplitude</small><strong>${data.rmsAmplitude.toFixed(5)}</strong></div><div><small>Full-scale sample count</small><strong>${data.fullScaleSampleCount}</strong></div></div><p class="memory-recall-note">Amplitude ranges combine all channels in ${bins.length} time bins. This is not a spectrogram or detector confidence. No authenticity flags are generated.</p><small class="report-digest">Source SHA-256 ${escape(data.sha256)}</small></section>`;
      const audio=root.querySelector('audio'),svg=root.querySelector('svg'),stage=root.querySelector('.pcm-wave-stage');
      const tooltip=root.querySelector('.pcm-wave-tooltip'),slider=root.querySelector('[data-wave-seek]');
      const showTime=time=>{root.querySelector('[data-wave-position]').textContent=time.toFixed(3)+' s';slider.value=time;root.querySelector('[data-wave-playhead]').setAttribute('d',`M${time/data.durationSeconds*1000} 0V220`);};
      const fraction=event=>{const bounds=svg.getBoundingClientRect();return Math.max(0,Math.min(1,(event.clientX-bounds.left)/bounds.width));};
      svg.addEventListener('pointermove',event=>{const point=fraction(event),bin=bins[Math.min(bins.length-1,Math.floor(point*bins.length))];tooltip.hidden=false;tooltip.textContent=`${bin.startSeconds.toFixed(3)}–${bin.endSeconds.toFixed(3)} s · min ${bin.min.toFixed(4)} · max ${bin.max.toFixed(4)} · RMS ${bin.rms.toFixed(4)}`;tooltip.style.left=Math.max(0,Math.min(55,point*100))+'%';});
      stage.addEventListener('pointerleave',()=>tooltip.hidden=true);
      const seek=time=>{if(Number.isFinite(audio.duration)){audio.currentTime=Math.min(time,audio.duration);showTime(audio.currentTime);}};
      svg.addEventListener('click',event=>seek(fraction(event)*data.durationSeconds));
      slider.addEventListener('input',()=>seek(Number(slider.value)));
      audio.addEventListener('timeupdate',()=>showTime(audio.currentTime));
      audio.addEventListener('error',()=>{root.querySelector('.pcm-wave-times').textContent='The waveform loaded, but the audio preview could not be decoded.';});
    }catch(error){if(root.isConnected&&current===sequence)root.textContent=error.message||'A measured waveform could not be loaded. No synthetic signal was substituted.';}
    finally{if(trigger.isConnected)trigger.disabled=false;if(root.isConnected)root.setAttribute('aria-busy','false');}
  });
}
