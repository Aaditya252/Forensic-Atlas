# Interactive entity and provenance explorer

Open `http://127.0.0.1:8100/?case=DF-24-017#entities` or choose Entity graph in any case.

The API page read model now includes a bounded `relationshipGraph` with explicit node IDs,
typed edges, evidence states, supporting sources, explanations and suggested review steps.
FalkorDB supplies recorded CaseEntity relationships and memory episodes; SQLite supplies
case membership, saved inspections and report snapshots. This is a read-only projection,
not a new reasoning model. Case membership is labeled separately from evidence relationships.

## Interaction

- Investigation view emphasizes original evidence, recorded entities and inspections.
- Full provenance also displays recent agent episodes and draft reports.
- Layer filters and search retain immediate neighbors to preserve relationship context.
- Hover shows a quick explanation; keyboard focus previews the explanation panel.
- Click or Enter pins a node/edge explanation and highlights its adjacent connections.
- The inspector shows state, source IDs, recorded basis, limitations and next review step.
- Use in path agent transfers a traversable entity ID to the existing bounded graph agent.
- Zoom, fit, scroll, clear selection, dark mode and reduced-motion styles are supported.

No link implies causation, identity or authenticity. Candidate edges remain dashed.
Agent citations are not independent corroboration. Missing nodes/links in a bounded view
must not be interpreted as proof of absence. Layout distance does not measure confidence.

## Bounds

100 evidence artifacts, 100 CaseEntity records, 200 relationships, 20 inspections,
20 episodes and 20 reports. The browser displays up to 80 matching nodes; search narrows
the view. Existing entity tables and graph-agent controls remain available below the map.

Validation: 59 unit tests passed, including membership semantics, candidate state/source
preservation and suppression of edges with missing endpoints. Live checks on all four
cases verified graph availability and endpoint consistency. Browser checks cover layer
controls, node selection, explanation text and transfer into the path agent.
