/** Fictional records used only by the offline design prototype. */
export const DEMO_WORKSPACE = Object.freeze({
  schemaVersion: 1,
  case: {
    id: 'DF-24-017',
    title: 'Northstar workspace access review',
    status: 'active_review',
    description: 'Investigation of a suspected unauthorized archive download across identity, endpoint, network, and collaboration sources.',
    leadExaminer: 'Alex Rivera',
    openedAt: '2026-10-16T09:00:00Z',
    authority: 'Scope v3 · approved',
    classification: 'CONFIDENTIAL'
  },
  overview: {
    evidenceItems: 28,
    evidenceAddedToday: 4,
    coveragePercent: 92.4,
    timelineEvents: 412,
    eventsAddedToday: 38,
    connectedSourceClasses: 6,
    reviewQueueItems: 5,
    reviewsDueToday: 2,
    verifiedArtifacts: 28,
    totalArtifacts: 28,
    sourceClassesAvailable: 6,
    sourceClassesExpected: 8,
    acquisitionsComplete: 23,
    acquisitionsExpected: 28,
    openGaps: 2,
    lastIntegrityCheck: '09:42 UTC'
  },
  evidence: [
    { name: 'auth-events-east.json', id: 'ART-028', type: 'Cloud audit', source: 'Entra ID · tenant north-02', date: 'Oct 18 · 09:42', size: '4.2 MB', status: 'verified', icon: 'cloud' },
    { name: 'browser-history.db', id: 'ART-027', type: 'Browser database', source: 'WS-114 · Chrome profile', date: 'Oct 18 · 09:36', size: '18.7 MB', status: 'verified', icon: 'database' },
    { name: 'incident-capture-04.pcapng', id: 'ART-026', type: 'Packet capture', source: 'Edge sensor · VLAN 12', date: 'Oct 18 · 09:21', size: '2.8 GB', status: 'partial', icon: 'file' },
    { name: 'meeting-clip-raw.mp4', id: 'ART-025', type: 'Video', source: 'SharePoint · case folder', date: 'Oct 18 · 08:58', size: '246 MB', status: 'review', icon: 'media' },
    { name: 'system.evtx', id: 'ART-024', type: 'Windows event log', source: 'WS-114 · Security', date: 'Oct 17 · 18:14', size: '72.1 MB', status: 'verified', icon: 'file' },
    { name: 'mailbox-export.pst', id: 'ART-023', type: 'Email archive', source: 'Exchange · user 84', date: 'Oct 17 · 17:52', size: '1.1 GB', status: 'verified', icon: 'file' },
    { name: 'memory-image.raw', id: 'ART-022', type: 'Memory image', source: 'WS-114 · live response', date: 'Oct 17 · 17:41', size: '16 GB', status: 'partial', icon: 'database' }
  ],
  reviewItems: [
    { id: 'REV-003', type: 'AI claim · speaker attribution', priority: 'HIGH REVIEW', title: '“I deleted the files” — speaker attribution is uncertain', copy: 'The transcript identifies the speaker as “Operator 2”; the draft summary attributes the action to the account owner.', evidence: 'ART-025 · 00:14:22–00:14:31', score: '74%' },
    { id: 'REV-002', type: 'Parser coverage · partial', priority: 'NEEDS CONTEXT', title: '27 message attachments were not parsed', copy: 'The export parser completed, but 27 attachment references point to unavailable payloads.', evidence: 'ART-023 · parser mail-v2.8', score: '—' },
    { id: 'REV-001', type: 'Correlation · candidate link', priority: 'REVIEW', title: 'Session and file transfer are close in time', copy: 'A sign-in is followed by a file copy 94 seconds later. Shared source clock; causality not established.', evidence: 'ART-028 + ART-024 · 09:12', score: '61%' },
    { id: 'REV-004', type: 'Timeline · clock offset', priority: 'NEEDS CONTEXT', title: 'Network sensor time offset is unknown', copy: 'The sensor records do not include a verified clock offset for this collection window.', evidence: 'ART-026 · sensor A', score: '—' },
    { id: 'REV-005', type: 'Media analysis · detector', priority: 'REVIEW', title: 'Synthetic media detector output is inconclusive', copy: 'Compression and a short clip reduce confidence. Treat this as a triage signal, not an authenticity finding.', evidence: 'ART-025 · 00:00:02–00:00:09', score: '52%' }
  ],
  sourceCoverage: [
    { id: 'SRC-IDENTITY', name: 'Identity & access', count: '6 / 6', pct: 100, icon: 'user', state: 'Complete' },
    { id: 'SRC-ENDPOINT', name: 'Endpoint & disk', count: '5 / 5', pct: 100, icon: 'database', state: 'Complete' },
    { id: 'SRC-NETWORK', name: 'Network telemetry', count: '3 / 4', pct: 75, icon: 'timeline', state: '1 source unavailable' },
    { id: 'SRC-CLOUD', name: 'Cloud workspace', count: '4 / 5', pct: 80, icon: 'cloud', state: 'Retention request pending' },
    { id: 'SRC-COMMS', name: 'Communications', count: '3 / 3', pct: 100, icon: 'evidence', state: 'Complete' },
    { id: 'SRC-MEDIA', name: 'Multimedia', count: '2 / 2', pct: 100, icon: 'media', state: 'Complete' }
  ],
  events: [
    { id: 'EVT-442', time: '09:42:18.204', timestamp: '2026-10-18T09:42:18.204Z', color: '', title: 'New sign-in session observed', desc: 'Account: analyst-temp · device: WS-114 · conditional access: satisfied', source: 'ART-028 · Entra ID' },
    { id: 'EVT-441', time: '09:40:51.000', timestamp: '2026-10-18T09:40:51Z', color: 'blue', title: 'Archive downloaded from team workspace', desc: 'Object: Q4-planning.zip · size: 18.4 MB · client address: 10.42.8.19', source: 'ART-028 · SharePoint audit' },
    { id: 'EVT-440', time: '09:38:09.677', timestamp: '2026-10-18T09:38:09.677Z', color: 'warn', title: 'Browser history record recovered', desc: 'Record references a shared session; local profile owner not established.', source: 'ART-027 · Chrome profile' },
    { id: 'EVT-439', time: '09:35:31.000', timestamp: '2026-10-18T09:35:31Z', color: '', title: 'Authentication token refresh', desc: 'Token refresh logged by identity provider. Source time precision: 1 second.', source: 'ART-028 · Entra ID' },
    { id: 'EVT-438', time: '09:31:02.520', timestamp: '2026-10-18T09:31:02.520Z', color: 'blue', title: 'Outbound TLS flow begins', desc: 'Destination metadata available; payload is encrypted. No content claim is made.', source: 'ART-026 · edge sensor' }
  ],
  updatedAt: '2026-10-18T09:42:00Z'
});
