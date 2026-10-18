const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const exportBase = (caseId, id) => `/api/v1/cases/${encodeURIComponent(caseId)}/reports/${encodeURIComponent(id)}/export`;

function reportCard(row, caseId) {
  const base = exportBase(caseId, row.id);
  return `<article class="cited-report-card"><span class="agent-state candidate">UNREVIEWED DRAFT</span><h3>${escape(row.title)}</h3><small>${escape(row.id)} · ${escape(row.createdAt||row.created_at)}</small><small>Summary episode: ${escape(row.summaryEpisodeId||row.summary_episode_id)}</small><p class="report-digest">SHA-256 ${escape(row.contentSha256||row.content_sha256)}</p><div class="report-export-actions"><a class="button" href="${base}/html" target="_blank" rel="noopener">Open printable report ↗</a><a class="button" href="${base}/json" download>Download JSON</a></div></article>`;
}

export function renderCitedReports(data, caseId) {
  const reports = data.rows.filter(row=>row.renderable);
  return `<section class="panel cited-report-builder"><div class="panel-heading"><div><span class="eyebrow">PHASE 4 · SOURCE-LINKED REPORTING</span><h2>Create a cited report snapshot</h2><p>Copy a saved summary into a durable draft with statements, source register, model provenance, and a content hash.</p></div><button class="button" type="button" data-report-load-summaries>Load saved summaries</button></div><form id="citedReportForm" class="cited-report-form"><label>Report title<input name="title" value="Case evidence summary" maxlength="160" required /></label><label>Saved cited summary<select name="summaryEpisodeId" required disabled><option value="">Load saved summaries to select a draft</option></select></label><button class="button primary" type="submit" disabled>Save report snapshot</button></form><p id="citedReportStatus" class="memory-recall-note" role="status">No model is run for report creation. Statements keep the wording and state from the selected historical summary.</p><p class="memory-recall-note">HTML opens a printable document; use the browser’s Print → Save as PDF if needed. JSON contains the canonical report content and digest. No evidence bytes or attachments are included.</p></section><section class="panel cited-report-library"><div class="panel-heading"><div><h2>Saved cited reports</h2><p>Independent snapshots remain readable without the model or graph service.</p></div></div><div id="citedReportCards" class="cited-report-grid">${reports.map(row=>reportCard(row,caseId)).join('')||'<p class="memory-recall-note" data-no-cited-reports>No cited snapshots yet. Generate a summary in the Agent Hub, then load it here.</p>'}</div></section>`;
}

export function initializeCitedReports(repository, getCaseId, onSaved) {
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-report-load-summaries]');
    if (!button || button.disabled) return;
    const panel = button.closest('.cited-report-builder'), form = panel.querySelector('form'), status = panel.querySelector('#citedReportStatus');
    button.disabled = true; status.textContent = 'Reading saved cited summaries from FalkorDB…';
    try {
      const data = await repository.recallMemory(getCaseId(), {agentId:'case-summary'});
      if (!panel.isConnected) return;
      const select = form.elements.summaryEpisodeId;
      select.innerHTML = '<option value="">Choose a saved summary</option>' + data.items.map(row=>`<option value="${escape(row.id)}">${escape(row.createdAt)} · ${escape(row.sourceIds.join(', '))} · ${escape(row.id)}</option>`).join('');
      select.disabled = !data.items.length;
      form.querySelector('button').disabled = !data.items.length;
      status.textContent = data.items.length ? `${data.items.length} recent summaries available. Select one to preserve as a report snapshot.` : 'No cited summary is saved yet. Generate one in the Agent Hub first.';
    } catch(error) { if (status.isConnected) status.textContent = error.message || 'Saved summaries could not be loaded.'; }
    finally { if (button.isConnected) button.disabled = false; }
  });
  document.addEventListener('submit', async event => {
    if (event.target.id !== 'citedReportForm') return;
    event.preventDefault();
    const form = event.target, button = form.querySelector('button'), panel = form.closest('.cited-report-builder');
    if (form.getAttribute('aria-busy') === 'true') return;
    const status = panel.querySelector('#citedReportStatus');
    const body = Object.fromEntries(new FormData(form)), fingerprint = JSON.stringify(body);
    if (form.dataset.requestBody !== fingerprint) { form.dataset.requestBody = fingerprint; form.dataset.requestKey = crypto.randomUUID(); }
    form.setAttribute('aria-busy','true'); button.disabled = true;
    panel.querySelector('[data-report-load-summaries]').disabled = true;
    status.textContent = 'Checking saved statements and citations, then saving the report snapshot…';
    try {
      const row = await repository.createCitedReport(getCaseId(), body, form.dataset.requestKey);
      if (!panel.isConnected) return;
      status.textContent = `Report ${row.id} saved as an unreviewed draft. Open the printable report or download JSON below.`;
      const cards = document.getElementById('citedReportCards');
      cards.querySelector('[data-no-cited-reports]')?.remove();
      if (![...cards.querySelectorAll('small')].some(element=>element.textContent.includes(row.id))) cards.insertAdjacentHTML('afterbegin', reportCard(row,getCaseId()));
      if (onSaved) {
        await onSaved();
        const refreshedStatus = document.getElementById('citedReportStatus');
        if (refreshedStatus) refreshedStatus.textContent = `Report ${row.id} saved as an unreviewed draft. Exports are available below.`;
      }
    } catch(error) { if (status.isConnected) status.textContent = error.message || 'The report could not be saved. Retry retains the request key.'; }
    finally { if (form.isConnected) { form.setAttribute('aria-busy','false'); button.disabled = false; panel.querySelector('[data-report-load-summaries]').disabled = false; } }
  });
}
