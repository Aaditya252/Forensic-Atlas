import { config } from '../config.js';
import { DEMO_WORKSPACE } from '../data/demo-workspace.js';
import { createApiClient } from './api-client.js';

const clone = (value) => globalThis.structuredClone ? structuredClone(value) : JSON.parse(JSON.stringify(value));
const casePath = (caseId, suffix = '') => `/api/v1/cases/${encodeURIComponent(caseId)}${suffix}`;
const idempotencyKey = () => globalThis.crypto?.randomUUID?.() ?? `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;

function assertWorkspace(value, expectedCaseId) {
  const overviewFields = ['evidenceItems','evidenceAddedToday','coveragePercent','timelineEvents','eventsAddedToday','connectedSourceClasses','reviewQueueItems','reviewsDueToday','verifiedArtifacts','totalArtifacts','sourceClassesAvailable','sourceClassesExpected','acquisitionsComplete','acquisitionsExpected','openGaps'];
  const valid = value && value.schemaVersion === 1 && value.case?.id === expectedCaseId &&
    typeof value.case.title === 'string' && typeof value.case.description === 'string' &&
    typeof value.case.leadExaminer === 'string' && typeof value.case.authority === 'string' &&
    typeof value.case.classification === 'string' && Number.isFinite(Date.parse(value.case.openedAt)) &&
    value.overview && overviewFields.every((key) => Number.isFinite(Number(value.overview[key]))) &&
    Array.isArray(value.evidence) && value.evidence.every((item) => item?.id && item?.name) &&
    Array.isArray(value.reviewItems) && value.reviewItems.every((item) => item?.id && item?.title) &&
    Array.isArray(value.sourceCoverage) && value.sourceCoverage.every((item) => item?.name && Number.isFinite(Number(item.pct))) &&
    Array.isArray(value.events) && value.events.every((item) => item?.id && item?.title);
  if (!valid) throw new Error('The workspace response does not match the SUTRAM v1 contract.');
  return value;
}

function assertPage(value) {
  const valid = value && value.schemaVersion === 1 && typeof value.title === 'string' &&
    typeof value.summary === 'string' && Array.isArray(value.metrics) &&
    value.metrics.every((item) => item && item.label != null && item.value != null) &&
    Array.isArray(value.columns) && value.columns.every((column) => column && typeof column.key === 'string' && typeof column.label === 'string') &&
    Array.isArray(value.rows) && value.rows.every((row) => row && typeof row === 'object' && !Array.isArray(row));
  if (!valid) throw new Error('The page response does not match the SUTRAM v1 page contract.');
  return value;
}

export function createWorkspaceRepository(settings = config) {
  let client = null;
  let clientError = null;
  if (settings.dataMode === 'api') {
    try { client = createApiClient({ baseUrl: settings.apiBaseUrl, timeoutMs: settings.apiTimeoutMs, getAccessToken: settings.getAccessToken }); }
    catch (error) { clientError = error; }
  }
  const requireClient = () => { if (clientError) throw clientError; if (!client) throw new Error('API service is not configured.'); return client; };

  return Object.freeze({
    mode: settings.dataMode,

    async loadAudioScreen(caseId,artifactId) {
      const response=await requireClient().request(casePath(caseId,'/artifacts/'+encodeURIComponent(artifactId)+'/audio-screen'));
      return response.data;
    },
    async runAudioScreen(caseId,artifactId,key) {
      const response=await requireClient().request(casePath(caseId,'/artifacts/'+encodeURIComponent(artifactId)+'/audio-screen'),{method:'POST',body:{acceptExperimental:true},idempotencyKey:key,timeoutMs:120000});
      return response.data;
    },

    async loadAudioWaveform(caseId,artifactId) {
      const response=await requireClient().request(casePath(caseId,'/artifacts/'+encodeURIComponent(artifactId)+'/waveform'),{timeoutMs:45000});
      return response.data;
    },

    async inspectArtifact(caseId, artifactId, requestKey) {
      const response = await requireClient().request(casePath(caseId,'/artifacts/'+encodeURIComponent(artifactId)+'/inspection'),{
        method:'POST',body:{},idempotencyKey:requestKey,timeoutMs:45000
      });
      return response.data;
    },

    async loadArtifactInspection(caseId, artifactId) {
      const response = await requireClient().request(casePath(caseId,'/artifacts/'+encodeURIComponent(artifactId)+'/inspection'));
      return response.data;
    },

    async createCitedReport(caseId, body, requestKey) {
      const response = await requireClient().request(casePath(caseId, '/reports/from-summary'), {
        method: 'POST', body, idempotencyKey: requestKey
      });
      return response.data;
    },

    async loadHandoffs(caseId) {
      const response = await requireClient().request(casePath(caseId, '/agents/handoffs?limit=100'));
      return response.data.items;
    },

    async acknowledgeHandoff(caseId, handoffId, expectedVersion, requestKey) {
      const response = await requireClient().request(casePath(caseId, '/agents/handoffs/' + encodeURIComponent(handoffId) + '/ack'), {
        method: 'POST', body: { expectedVersion }, headers: { 'Idempotency-Key': requestKey }
      });
      return response.data;
    },

    async recallMemory(caseId, filters = {}) {
      const params = new URLSearchParams({ limit: '10' });
      for (const key of ['q', 'agentId', 'sourceId']) if (filters[key]) params.set(key, filters[key]);
      const response = await requireClient().request(casePath(caseId, '/agents/recall') + '?' + params);
      return response.data;
    },

    async inspectMemory(caseId, episodeId) {
      const response = await requireClient().request(casePath(caseId, '/agents/recall/' + encodeURIComponent(episodeId)));
      return response.data;
    },

    async loadWorkspace(caseId = settings.caseId, { signal } = {}) {
      if (settings.dataMode === 'demo') return clone(DEMO_WORKSPACE);
      const response = await requireClient().request(`${casePath(caseId)}/workspace`, { signal });
      return assertWorkspace(response?.data ?? response, caseId);
    },

    async loadPage(caseId, page, { signal } = {}) {
      if (settings.dataMode === 'demo') return null;
      const response = await requireClient().request(`${casePath(caseId)}/pages/${encodeURIComponent(page)}`, { signal });
      return assertPage(response?.data ?? response);
    },

    async searchCase(caseId, query, { signal } = {}) {
      const term = String(query || '').trim();
      if (!term) return [];
      if (settings.dataMode === 'api') {
        const response = await requireClient().request(`${casePath(caseId)}/search?q=${encodeURIComponent(term)}&limit=8`, { signal });
        return Array.isArray(response?.data?.items) ? response.data.items : [];
      }
      const needle = term.toLocaleLowerCase();
      const records = [
        ...DEMO_WORKSPACE.evidence.map((item) => ({ label: item.name, detail: `${item.id} · ${item.type}`, route: 'evidence', id: item.id })),
        ...DEMO_WORKSPACE.reviewItems.map((item) => ({ label: item.title, detail: `${item.id} · ${item.type}`, route: 'review', id: item.id })),
        ...DEMO_WORKSPACE.events.map((item) => ({ label: item.title, detail: `${item.id} · ${item.source}`, route: 'timeline', id: item.id }))
      ];
      return records.filter((item) => `${item.label} ${item.detail}`.toLocaleLowerCase().includes(needle)).slice(0, 8);
    },

    async recordReviewDecision(caseId, reviewId, decision, note = '') {
      if (settings.dataMode === 'demo') return { demo: true, reviewId, decision };
      return requireClient().request(`${casePath(caseId)}/reviews/${encodeURIComponent(reviewId)}/decision`, {
        method: 'POST', body: { decision, note }, idempotencyKey: idempotencyKey()
      });
    },

    async createAcquisition(caseId, input) {
      if (settings.dataMode === 'demo') return { demo: true, jobId: 'DEMO-JOB-NEW', input };
      return requireClient().request(`${casePath(caseId)}/acquisitions`, { method: 'POST', body: input, idempotencyKey: idempotencyKey() });
    },

    async createReport(caseId, input) {
      if (settings.dataMode === 'demo') return { demo: true, reportId: 'DEMO-REPORT-NEW', input };
      return requireClient().request(`${casePath(caseId)}/reports`, { method: 'POST', body: input, idempotencyKey: idempotencyKey() });
    },

    async createExport(caseId, input) {
      if (settings.dataMode === 'demo') return { demo: true, exportId: 'DEMO-EXPORT-NEW', input };
      return requireClient().request(`${casePath(caseId)}/exports`, { method: 'POST', body: input, idempotencyKey: idempotencyKey() });
    },

    async queueMediaAnalysis(caseId, input) {
      if (settings.dataMode === 'demo') return { demo: true, runId: 'DEMO-RUN-NEW', input };
      return requireClient().request(`${casePath(caseId)}/media-runs`, { method: 'POST', body: input, idempotencyKey: idempotencyKey() });
    },

    async loadDeepfakeRuns(caseId, { signal } = {}) {
      if (settings.dataMode === 'demo') return [];
      const response = await requireClient().request(`${casePath(caseId)}/media-runs?profile=multimodal-screening&limit=50`, { signal });
      const items = response?.data?.items;
      if (!Array.isArray(items) || items.some((item) => !item?.id || !item?.artifactId || !['queued','running','completed','failed'].includes(item.status) || !Array.isArray(item.signals || []))) {
        throw new Error('The media-runs response does not match the SUTRAM deepfake-run contract.');
      }
      return items.map((item) => ({ ...item, signals: item.signals || [] }));
    },

    async queryGraphContext(caseId, { entityId, question, depth = 3 }) {
      if (settings.dataMode === 'demo') throw new Error('Graph context needs the API service and a connected FalkorDB graph.');
      return requireClient().request(`${casePath(caseId)}/context/ask`, {
        method: 'POST',
        body: { entityId, question, depth },
        idempotencyKey: idempotencyKey()
      });
    },

    async loadAgentHub(caseId, { signal } = {}) {
      if (settings.dataMode === 'demo') return { roster: [], latestRun: null, provider: { llm: 'not-configured', mediaDetector: 'not-configured', graph: 'not-connected' } };
      const response = await requireClient().request(`${casePath(caseId)}/agents/hub`, { signal });
      return response?.data ?? response;
    },

    async runAgentHub(caseId) {
      if (settings.dataMode === 'demo') throw new Error('The agent hub requires the case API and its scoped read models.');
      const response = await requireClient().request(`${casePath(caseId)}/agents/hub/run`, { method: 'POST', body: {}, idempotencyKey: idempotencyKey() });
      return response?.data ?? response;
    },

    async generateCaseSummary(caseId) {
      if (settings.dataMode !== 'api') throw new Error('Cited summaries require the case API and local model.');
      const response = await requireClient().request(`${casePath(caseId)}/summary`, { method: 'POST', body: {}, idempotencyKey: idempotencyKey(), timeoutMs: 120000 });
      return response?.data ?? response;
    },

    async uploadEvidence(caseId, form, options = {}) {
      if (settings.dataMode === 'demo') throw new Error('Evidence upload needs the local API service.');
      const file = options.file || form.querySelector('[name="file"]')?.files?.[0];
      if (!file) throw new Error('Choose a file to add to this case.');
      const body = new FormData();
      body.append('file', file, file.name);
      if (file.size > 512 * 1024 * 1024) throw new Error('Each file must be 512 MB or smaller.');
      body.append('media_type', options.mediaType || form.querySelector('[name="media_type"]')?.value || 'Other');
      body.append('source_label', form.querySelector('[name="source_label"]')?.value || 'Local examiner intake');
      return requireClient().request(`${casePath(caseId)}/artifacts`, {
        method: 'POST', body, idempotencyKey: idempotencyKey(), timeoutMs:120000
      });
    }
  });
}
