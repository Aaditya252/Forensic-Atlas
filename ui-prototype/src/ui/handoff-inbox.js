const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function handoffRows(items) {
  if (!items.length) return '<p class="memory-recall-note">No handoffs were returned for this case.</p>';
  return items.map(item => `<article class="handoff-card" data-handoff-status="${escape(item.status)}"><div class="handoff-card-top"><strong>${escape(item.fromAgent)} → ${escape(item.toAgent)}</strong><span class="agent-state" data-handoff-badge>${escape(item.status)}</span></div><p>${escape(item.task)}</p><small>Evidence state: ${escape(item.state)} · Sources: ${escape((item.sourceIds||[]).join(' · ')||'none recorded')}</small><details><summary>Inspect assignment and receipt</summary><small>${escape(item.id)} · version <span data-handoff-version>${escape(item.version)}</span> · created ${escape(item.createdAt)}</small><pre>${escape(JSON.stringify(item.context||{},null,2))}</pre><p class="memory-recall-note">Acknowledgement records receipt for this assignment. It does not run the specialist, complete the task, or approve evidence.</p><button class="button" type="button" data-handoff-ack="${escape(item.id)}" data-version="${escape(item.version)}" ${item.status!=='pending'?'disabled':''}>${item.status==='acknowledged'?'Receipt acknowledged':'Acknowledge receipt'}</button><p class="handoff-receipt-status" role="status">${item.acknowledgedAt?'Receipt saved '+escape(item.acknowledgedAt):''}</p></details></article>`).join('');
}

export function renderHandoffInbox(items = []) {
  return `<section id="handoffInbox" class="panel handoff-inbox"><div class="panel-heading"><div><span class="eyebrow">PHASE 3 · SHARED WORK</span><h2>Agent handoff inbox</h2><p>Inspect source-linked assignments and record receipt for the receiving specialist.</p></div><button class="button" type="button" data-handoff-refresh>Refresh handoffs</button></div><div class="handoff-toolbar"><label>Show<select id="handoffStatusFilter"><option value="all">All statuses</option><option value="pending">Pending</option><option value="acknowledged">Acknowledged</option></select></label><span id="handoffWindowNote" class="memory-recall-note">${items.length} recent assignments · refresh reads up to 100</span></div><p id="handoffInboxStatus" class="memory-recall-note" role="status"></p><div id="handoffInboxRows" class="handoff-grid">${handoffRows(items)}</div><p id="handoffFilterEmpty" class="memory-recall-note" hidden>No assignments match this status in the loaded window.</p></section>`;
}

export function initializeHandoffInbox(repository, getCaseId) {
  const filterRows = () => {
    const panel = document.getElementById('handoffInbox');
    if (!panel) return;
    const selected = panel.querySelector('#handoffStatusFilter').value;
    let visible = 0;
    panel.querySelectorAll('[data-handoff-status]').forEach(row => { row.hidden = selected !== 'all' && row.dataset.handoffStatus !== selected; if (!row.hidden) visible++; });
    panel.querySelector('#handoffFilterEmpty').hidden = visible > 0 || !panel.querySelector('[data-handoff-status]');
  };
  document.addEventListener('change', event => { if (event.target.id === 'handoffStatusFilter') filterRows(); });
  document.addEventListener('click', async event => {
    const refresh = event.target.closest('[data-handoff-refresh]');
    if (refresh) {
      const panel = refresh.closest('#handoffInbox'), status = panel.querySelector('#handoffInboxStatus');
      if (panel.getAttribute('aria-busy') === 'true') return;
      panel.setAttribute('aria-busy','true'); refresh.disabled = true;
      status.textContent = 'Reading current assignment states from FalkorDB…';
      try {
        const rows = await repository.loadHandoffs(getCaseId());
        if (!panel.isConnected) return;
        panel.querySelector('#handoffInboxRows').innerHTML = handoffRows(rows);
        panel.querySelector('#handoffWindowNote').textContent = `${rows.length} assignments loaded · window limit 100${rows.length>=100?' · older assignments may exist':''}`;
        status.textContent = 'Assignment states refreshed.';
        filterRows();
      } catch(error) { if (panel.isConnected) status.textContent = error.message || 'Handoffs could not be loaded.'; }
      finally { if (panel.isConnected) { panel.setAttribute('aria-busy','false'); refresh.disabled = false; } }
      return;
    }
    const button = event.target.closest('[data-handoff-ack]');
    if (!button || button.disabled) return;
    const row = button.closest('.handoff-card'), panel = button.closest('#handoffInbox');
    if (panel.getAttribute('aria-busy') === 'true') return;
    const status = row.querySelector('.handoff-receipt-status');
    button.disabled = true;
    button.dataset.requestKey ||= crypto.randomUUID();
    status.textContent = 'Saving receipt with the inspected version…';
    // Keep refresh from replacing the inspected row during its write.
    const refreshButton = panel.querySelector('[data-handoff-refresh]');
    refreshButton.disabled = true;
    panel.setAttribute('aria-busy','true');
    try {
      const result = await repository.acknowledgeHandoff(getCaseId(), button.dataset.handoffAck, Number(button.dataset.version), button.dataset.requestKey);
      if (!row.isConnected) return;
      row.dataset.handoffStatus = result.status;
      row.querySelector('[data-handoff-badge]').textContent = result.status;
      row.querySelector('[data-handoff-version]').textContent = result.version;
      button.textContent = 'Receipt acknowledged';
      status.textContent = `Receipt saved ${result.acknowledgedAt}. Work remains subject to specialist and examiner review.`;
      filterRows();
    } catch (error) {
      if (!row.isConnected) return;
      if (error.status === 409) {
        status.textContent = 'This assignment changed. Refresh handoffs and inspect the current version before acknowledging.';
        button.textContent = 'Refresh required';
      } else {
        status.textContent = error.message || 'Receipt could not be saved. Retry uses the same request key.';
        button.disabled = false;
      }
    } finally { if (panel.isConnected) { panel.setAttribute('aria-busy','false'); refreshButton.disabled = false; } }
  });
}
