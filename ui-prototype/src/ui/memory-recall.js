const escape = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function renderMemoryRecall(data, evidence) {
  return `<section class="panel memory-recall-panel"><div class="panel-heading"><div><span class="eyebrow">PHASE 3 · PERSISTENT CASE MEMORY</span><h2>Recall earlier work</h2><p>Find saved runs and inspect their original source trail. Historical output remains unreviewed.</p></div></div><form id="memoryRecallForm" class="memory-recall-form"><label>Search saved text<input name="q" maxlength="160" placeholder="Source ID, relationship, or review topic" /></label><label>Agent<select name="agentId"><option value="">All agents</option>${(data?.roster||[]).map(a=>`<option value="${escape(a.id)}">${escape(a.name)}</option>`).join('')}</select></label><label>Evidence source<select name="sourceId"><option value="">All sources</option>${evidence.map(e=>`<option value="${escape(e.id)}">${escape(e.id)} · ${escape(e.name)}</option>`).join('')}</select></label><button class="button primary" type="submit">Search memory</button></form><p class="memory-recall-note">All search terms must match · latest 100 case or agent episodes · no model required</p><div id="memoryRecallResults" aria-live="polite"><p class="memory-recall-note">Leave search text empty to browse recent episodes.</p></div><div id="memoryRecallDetail"></div></section>`;
}

export function initializeMemoryRecall(repository, getCaseId) {
  let searchSequence = 0, detailSequence = 0;
  document.addEventListener('submit', async event => {
    if (event.target.id !== 'memoryRecallForm') return;
    event.preventDefault();
    const form = event.target, results = document.getElementById('memoryRecallResults');
    const detail = document.getElementById('memoryRecallDetail');
    const sequence = ++searchSequence;
    ++detailSequence;
    const submit = form.querySelector('button');
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    results.removeAttribute('role');
    results.innerHTML = '<p class="memory-recall-note" role="status">Reading saved episodes from FalkorDB…</p>';
    detail.innerHTML = '';
    try {
      const data = await repository.recallMemory(getCaseId(), Object.fromEntries(new FormData(form)));
      if (!results.isConnected || sequence !== searchSequence) return;
      results.innerHTML = `<p class="memory-recall-note">${data.matchedCount} matching episodes in ${data.scannedCount} scanned · showing ${data.items.length}${data.windowMayBeTruncated?' · older episodes may exist outside this window':''}</p>` + (data.items.length ? `<ol class="memory-recall-list">${data.items.map(row=>`<li><div><span class="agent-state">${escape(row.evidenceState)}</span><small>${escape(row.agentId)} · ${escape(row.createdAt)}</small></div><h3>${escape(row.summary)}</h3><p>${escape(row.excerpt)}</p><small>Sources: ${escape(row.sourceIds.join(' · ')||'none recorded')} · historical, unreviewed</small><button type="button" class="text-action" data-memory-episode="${escape(row.id)}">Inspect saved episode →</button></li>`).join('')}</ol>` : '<div class="summary-empty">No saved episode matches these filters in the bounded window. Try fewer search terms or another agent.</div>');
    } catch (error) {
      if (results.isConnected && sequence === searchSequence) { results.textContent = error.message || 'Memory could not be searched.'; results.setAttribute('role', 'alert'); }
    } finally {
      if (form.isConnected && sequence === searchSequence) { submit.disabled = false; form.setAttribute('aria-busy', 'false'); }
    }
  });
  document.addEventListener('click', async event => {
    const trigger = event.target.closest('[data-memory-episode]');
    if (!trigger) return;
    const detail = document.getElementById('memoryRecallDetail');
    const sequence = ++detailSequence;
    trigger.disabled = true;
    detail.removeAttribute('role');
    detail.textContent = 'Reading the selected saved episode…';
    try {
      const row = await repository.inspectMemory(getCaseId(), trigger.dataset.memoryEpisode);
      if (!detail.isConnected || sequence !== detailSequence) return;
      detail.innerHTML = `<article class="memory-episode-detail" tabindex="-1"><span class="eyebrow">SAVED EPISODE · ${escape(row.id)}</span><h3>${escape(row.summary)}</h3><p>${escape(row.answer || 'No answer text was recorded in this episode.')}</p><small>${escape(row.agentId)} · ${escape(row.createdAt)} · ${escape(row.evidenceState)}</small><p class="memory-recall-note">${escape(row.notice)}</p>${row.statements.length?`<ol>${row.statements.map(s=>`<li><strong>${escape(s.state)}</strong> ${escape(s.text)}<small>Sources: ${escape(s.sources.join(' · '))}</small></li>`).join('')}</ol>`:''}<details><summary>Saved tool trace and provenance</summary><pre>${escape(JSON.stringify({sourceIds:row.sourceIds,contextDigest:row.contextDigest,trace:row.trace},null,2))}</pre></details></article>`;
      detail.querySelector('article').focus({preventScroll:true});
      detail.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    } catch (error) {
      if (detail.isConnected && sequence === detailSequence) { detail.textContent = error.message || 'The episode could not be read.'; detail.setAttribute('role', 'alert'); }
    } finally { if (trigger.isConnected) trigger.disabled = false; }
  });
}
