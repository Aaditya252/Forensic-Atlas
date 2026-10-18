import { DEMO_WORKSPACE } from './demo-workspace.js';

// Public fictional fixture only. Never populate this from a local case database.
export function demoRelationshipPage() {
  const snapshot = DEMO_WORKSPACE;
  const nodes = [];
  const edges = [];
  const addNode = (id, name, kind, state, reason, sources = []) => {
    nodes.push({ id, name, kind, state, reason, sources,
      nextStep: 'Inspect the fictional source reference. Use the local application for saved case relationships.' });
  };
  const addEdge = (from, to, label, state, reason, sources = []) => {
    edges.push({ id: `demo-edge-${edges.length}`, from, to, label, state,
      reason: `Fictional demo: ${reason}`, sources,
      nextStep: 'Check the source record and alternative explanations; this link does not establish identity or causation.' });
  };
  addNode(snapshot.case.id, snapshot.case.title, 'Case', 'fictional demo',
    'Fictional Northstar case. This public map is not connected to your local database.');
  for (const item of snapshot.evidence) {
    addNode(item.id, item.name, 'Evidence', 'fictional demo',
      `Fictional ${item.type} source record: ${item.source}.`, [item.id]);
    addEdge(snapshot.case.id, item.id, 'contains', 'membership',
      'Case membership only; no causal relationship is implied.');
  }
  const entities = [
    { id: 'SES-0942', name: '09:42 sign-in', source: 'ART-028', label: 'Session' },
    { id: 'ACC-TEMP', name: 'analyst-temp', source: 'ART-028', label: 'Account' },
    { id: 'DEV-114', name: 'WS-114', source: 'ART-028', label: 'Device' },
    { id: 'FILE-Q4', name: 'Q4-planning.zip', source: 'ART-028', label: 'File' },
    { id: 'IP-1042', name: '10.42.8.19', source: 'ART-026', label: 'Network endpoint' }
  ];
  for (const item of entities) {
    addNode(item.id, item.name, 'Entity', 'fictional demo',
      `Fictional ${item.label.toLowerCase()} from the Northstar fixture.`, [item.source]);
    addEdge(item.id, item.source, 'source record', 'provenance',
      'This fixture entity references the indicated source artifact.', [item.source]);
  }
  for (const [from, to, label, source, state] of [
    ['SES-0942', 'ACC-TEMP', 'authenticated as', 'ART-028', 'observed'],
    ['SES-0942', 'DEV-114', 'observed on', 'ART-028', 'observed'],
    ['SES-0942', 'FILE-Q4', 'downloaded', 'ART-028', 'observed'],
    ['ACC-TEMP', 'DEV-114', 'used', 'ART-028', 'observed'],
    ['FILE-Q4', 'IP-1042', 'transferred from', 'ART-026', 'candidate']
  ]) {
    addEdge(from, to, label, state, `Fixture relationship: ${label}. Evidence state: ${state}.`, [source]);
  }
  return {
    schemaVersion: 1, demo: true, title: 'Evidence relationship graph',
    summary: 'Explore the fictional Northstar relationships. Your saved evidence graphs remain in the local application.',
    sectionTitle: 'Fictional source-linked entities',
    sectionDescription: 'These are public demo records, not a live database query.',
    metrics: [{ label: 'Demo map records', value: nodes.length, unit: 'nodes', foot: 'Fictional fixture', kind: 'teal', icon: 'entities' }],
    columns: [{ key: 'id', label: 'Entity ID' }, { key: 'label', label: 'Type' },
      { key: 'name', label: 'Name' }, { key: 'source', label: 'Evidence source' }],
    rows: entities, agentMemory: [],
    relationshipGraph: { demo: true, graphAvailable: false, nodes, edges,
      notice: 'Fictional demo relationships only. Live graph queries, saved episodes and reports remain in the local FalkorDB-backed application.' }
  };
}
