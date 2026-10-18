# SUTRAM Agent Memory & Coordination — Part 3

**Status:** Small deterministic workflows implemented; no learned weights or training are involved.

## Review triage

`review-triage` uses the review item's typed `type` and `title` metadata to choose a fixed category and order: source/parser dependency, clock quality, attribution, candidate link, media screening, then general review. IDs break ties for stable output. It does not read confidence scores, infer factual importance, or change the examiner's queue state. It returns only artifact IDs that occur in the current case evidence list.

Endpoint: `GET /api/v1/cases/{caseId}/agents/review-triage`. The Hybrid Agent Hub also shows the result with a direct link to the review queue. Empty input returns an empty ordered list.

## Timeline normalization

`timeline-normalizer` accepts the case event rows already present in the local read model. If a timestamp parses as ISO-8601 and contains an explicit offset, it emits UTC and labels the representational precision from the source text. If the offset is absent, the value is invalid, or the fractional precision exceeds Python datetime's microsecond support, it retains the raw string and returns a null normalized value with an `unknown` state. It never assumes India time, browser time, or a case default.

Endpoint: `GET /api/v1/cases/{caseId}/agents/timeline-normalizer`. The Timeline page includes source time, normalized UTC, text precision, and offset status as separate columns. Timestamp normalization does not validate the source clock's accuracy.

## Parser coverage and transcript speaker-label readiness

`parser-coverage` consumes only an explicit `parserManifest` with parsed/reference counters and case-known source IDs. The current Northstar fixture has a parser-related review cue, but it has no manifest, so the agent returns an unknown gap and points to that review source. It does not parse the prose title to claim a count. A ready contract is provided for later ingestion of parser manifests.

`transcript-attribution` accepts only existing structured `transcriptSegments` that carry a diarization `speakerLabel` and case-known source ID. It exposes those supplied labels as a draft for examiner comparison. The current fixture has an attribution review item but no segments, so the live result is an explicit unknown gap; it generates no transcript, score, or person attribution.

Endpoints: `GET /api/v1/cases/{caseId}/agents/parser-coverage` and `GET /api/v1/cases/{caseId}/agents/transcript-attribution`. Both outputs appear as bounded workstreams in the case synthesis.

## Lightweight model decision for M1–M4

For the current slice, M1 salience, M2 extraction, and M3 entity resolution remain deterministic or unavailable; the current case read model does not contain enough validated labels to justify a trained classifier. M4 retrieval is the fixed, bounded FalkorDB graph path tool plus source-filtered episode reads. No embedding model is required for the pilot. Semantic search and any model slate remain conditional on a benchmark showing a real retrieval failure.

This choice keeps the first version small: one FastAPI process, existing SQLite tables for case and audit data, FalkorDB for graph/memory/handoffs, and no local model download. Deterministic rules are easier to inspect and do not acquire authority over human review. Temporal correlation remains a hypothesis workstream in the coordinator; unknown clock quality remains an explicit alternative and prevents causal conclusions.

## Verification state

The local unit suite uses the fictional Northstar fixture and fake graph adapters. It checks source allowlisting, explicit/missing offsets, review ordering, memory state validation, bounded graph reads, and optimistic handoff acknowledgement. No integration result against a live FalkorDB service is claimed in this part.

**Self-check:** no model/dataset/metric was invented; no timestamp timezone was guessed; no agent closes a review or promotes a candidate to fact.
