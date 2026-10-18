"""Read-only provenance map. Membership and citations never imply causation."""


def build_relationship_view(snapshot, entities, relations, inspections, episodes, reports, graph_available):
    nodes, edges = {}, []
    case_id = snapshot['case']['id']

    def node(ident, name, kind, state, reason, sources=None, next_step=None):
        nodes[ident] = {'id': ident, 'name': name, 'kind': kind, 'state': state or 'unknown',
                        'reason': reason, 'sources': sources or [],
                        'nextStep': next_step or 'Inspect the cited original and its collection context.'}

    def edge(start, end, label, state, reason, sources=None):
        if start in nodes and end in nodes:
            edges.append({'id': 'edge-' + str(len(edges)), 'from': start, 'to': end, 'label': label,
                          'state': state, 'reason': reason, 'sources': sources or [],
                          'nextStep': 'Check the source record and alternative explanations before drawing conclusions.'})

    node(case_id, snapshot['case']['title'], 'Case', 'recorded',
         'Selected case record. Connections from this node show membership only.', next_step='Choose evidence or a relationship to inspect its basis.')
    for item in snapshot.get('evidence', [])[:100]:
        node(item['id'], item['name'], 'Evidence', item.get('status', 'recorded'),
             'Registered ' + str(item.get('type', 'artifact')) + '. Source: ' + str(item.get('source', 'not recorded')) +
             '. Integrity state does not establish authenticity.', [item['id']])
        edge(case_id, item['id'], 'contains', 'membership', 'The artifact is registered in this case; this is not a causal relationship.')
    for item in entities:
        if item['id'] not in nodes:
            node(item['id'], item.get('name') or item['id'], 'Entity', item.get('claim'),
                 str(item.get('label') or 'Entity') + ' recorded in the case-scoped FalkorDB projection.',
                 [item['source']] if item.get('source') else [])
        if item.get('source') != item['id']:
            edge(item['id'], item.get('source'), 'source record', 'provenance', 'This entity cites the indicated source artifact.', [item['source']] if item.get('source') else [])
    for item in relations:
        edge(item['from'], item['to'], item['label'].replace('_', ' ').lower(), item.get('state') or 'unknown',
             'Stored FalkorDB relationship: ' + item['label'] + '. The evidence state is ' + str(item.get('state') or 'unknown') +
             '. A relationship does not identify a person or establish causation.', [item['source']] if item.get('source') else [])
    for item in inspections:
        node(item['id'], 'Inspection · ' + item['artifactId'], 'Inspection', item['status'],
             'Saved metadata inspection: ' + str(item.get('format', 'unavailable')) + '; matching registered digest: ' + str(item.get('integrityMatch')) +
             '. Historical result; no authenticity determination.', [item['artifactId']])
        edge(item['id'], item['artifactId'], 'inspected bytes', 'derived', 'This saved inspection was produced from this artifact.', [item['artifactId']])
    for item in episodes:
        node(item['id'], item.get('agentId', 'Agent') + ' · ' + item.get('kind', 'episode'), 'Agent memory', item.get('evidenceState', 'unknown'),
             str(item.get('summary', 'Saved agent episode'))[:1200] + ' Saved agent output is not an examiner finding.', item.get('sourceIds', []))
        for source in item.get('sourceIds', []):
            edge(item['id'], source, 'cites source', 'derived', 'The saved episode explicitly cites this artifact; citations are not independent corroboration.', [source])
    for item in reports:
        node(item['id'], item['title'], 'Report', 'unreviewed draft',
             'Saved cited report snapshot. SHA-256: ' + item['content_sha256'] + '. Requires examiner review.', next_step='Open Reports to inspect the complete cited draft.')
        edge(item['id'], item['summary_episode_id'], 'built from summary', 'derived', 'The report stores this exact summary episode identifier.')
    return {'nodes': list(nodes.values()), 'edges': edges, 'graphAvailable': graph_available,
            'notice': 'Bounded read-only view: up to 100 evidence artifacts, 100 graph entities, 200 recorded relationships, 20 inspections, 20 memory episodes and 20 reports. Missing links are coverage gaps; no causal inference is performed.'}
