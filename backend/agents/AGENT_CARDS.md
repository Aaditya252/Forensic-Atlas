# SUTRAM agent roster and cards

Version: **0.1.0**. “Built” means implemented in this development slice, not approved for real-case use. All future agents remain disabled until their inputs, tools, verifier, and audit path are implemented. Evidence strings are untrusted data. Agents never decide reviews or make identity, intent, motive, guilt, causation, or media authenticity findings.

## Roster

| Agent | Feature | Mode | Status |
|---|---|---|---|
| overview-metrics | Overview | Precise | Designed, not enabled |
| case-brief | Overview | Hybrid | Designed, not enabled |
| intake-integrity | Evidence | Precise | Partial primitives; agent designed |
| parser-coverage | Coverage | Precise | Built; returns explicit gap until manifest exists |
| timeline-normalizer | Timeline | Precise | Built conservative timestamp normalization |
| correlation-agent | Timeline | Hybrid | Designed, not enabled |
| entity-extractor | Entity graph | Hybrid | Designed, not enabled |
| evidence-path-agent | Entity graph | Precise | Built deterministic fallback |
| context-planner | Entity graph | Precise | Built |
| context-narrator | Entity graph | Precise | Built |
| context-verifier | Cross-cutting | Precise | Built |
| media-metadata | Media | Precise | Built; bounded real-file inspection plus historical source-verified agent context |
| transcript-attribution | Media / review | Precise | Built fail-closed speaker-label draft; no transcript segments configured |
| media-screening | Deepfake lab | Precise | Fail-closed wrapper built; no model |
| review-triage | Review queue | Precise | Built deterministic dependency ordering |
| review-recorder | Review queue | Precise | Existing append-only API primitive |
| scope-checker | Acquisitions | Precise | Designed; current endpoint only validates fields |
| acquisition-planner | Acquisitions | Hybrid | Designed, not enabled |
| report-drafter | Reports | Hybrid | Designed, not enabled |
| claim-verifier | Reports | Precise | Designed, not enabled |
| claim-judge | Reports | Hybrid | Designed, not enabled |
| service-health | Settings | Precise | Partial `/health` primitive |
| case-search | Search | Precise | Existing `/search` primitive |
| notification-router | Notifications | Precise | UI reads completed runs; no delivery service |
| orchestrator | Cross-cutting | Hybrid | Designed, not enabled |
| memory | Cross-cutting | Precise | Episodic query memory only; no semantic promotion |
| case-orchestrator | Cross-cutting | Hybrid | Built; coordinates case-scoped specialist outputs |
| case-summary | Case summary | Local LLM + precise verifier | Built; exact-source unreviewed extractive drafts |
| memory-recall | Cross-cutting | Precise lexical retrieval | Built; bounded case/agent/source search and saved episode inspection |
| timeline-correlation | Timeline | Hybrid | Built deterministic candidate links and alternatives |
| impact-assessment | Cross-cutting | Hybrid | Built; source-grounded uncertainty and next steps |
| research-mapper | Forensic research | Precise | Built; curated NIST and deepfake benchmark mappings |

## Built agent cards

### memory-recall / 0.1.0

- **Purpose:** Find and inspect earlier case-scoped agent work without another model dependency.
- **Inputs/tools:** Search text ≤160 characters/12 terms, optional agent and case-known artifact filters; fixed `list_episodes(limit=100)` and parameterized `get_episode(caseId,id)` queries.
- **Output:** Bounded matches with counts, historical state/source IDs, and original statements/tool trace on inspection.
- **Guardrails:** All terms must match; case and source allowlists apply; search scores mean text overlap only. Recalled output stays episodic/unverified, never becomes a semantic fact, and is not fed into the model as fresh evidence.
- **Endpoints:** `GET /agents/recall` and `/agents/recall/{episodeId}` under the case API prefix. Agent Hub provides search and detail UI.
- **Tests:** Scope, sources, input/output bounds, untrusted text, state preservation, fixed parameterized lookup; read-only live check script `scripts/verify_phase3.py`.

### Hybrid agent hub / 0.1.0

- **Purpose:** Cross-layer coordinator runs deterministic evidence, timeline, graph, media-status, impact, and research specialists against case-scoped tools.
- **Inputs:** Case read model, bounded FalkorDB entity list, media-provider configuration, and curated research references.
- **Allowed tools:** Case snapshot, `graph.list_entities(limit≤250)`, provider health, and case-scoped episodic memory/audit writes. No generated SQL/Cypher, external retrieval, or detector inference.
- **Output:** `{runId,caseId,mode,provider,workstreams:[{agentId,state,summary,sources,impact,alternatives,nextStep}],priorities,research,limits}`.
- **Evidence states:** Derived for computed counts/availability; hypothesis for temporal association; unknown when a dependency is unavailable.
- **Guardrails:** Source IDs are intersected with the current case allowlist. Cause and impact remain candidate explanations with alternatives; no identity, intent, guilt, authenticity, or examiner decision.
- **Memory/audit:** Successful run stored as episodic/unverified and audited; never promoted to semantic facts.
- **Endpoint/frontend:** `GET/POST /api/v1/cases/{caseId}/agents/hub[/run]`; Hybrid agent hub page.

### review-triage / 0.1.0

- **Feature/page; mode and why; purpose:** Review queue; precise because it applies fixed dependency categories to existing review type/title text and stable ID ordering. It suggests an attention sequence, never a decision.
- **Inputs:** Case `reviewItems` and `evidence` IDs from the read model.
- **Allowed tools:** None; no model, score, or external connector is used.
- **Output JSON:** `{agent,method,orderedItems:[{reviewId,title,category,priorityOrder,rank,state,rationale,nextStep,sourceIds}],limits}`.
- **Evidence states:** `derived` for the ordering rationale; citations are only artifact IDs present in the current case snapshot.
- **Guardrails:** Ignores review confidence scores; does not infer factual importance or close/approve/reject any item; type/title text is data, not instructions.
- **Failure:** Empty queue returns an empty list; unsupported item type uses stable general-review ordering.
- **Memory/audit:** Included in the case-synthesis episode and audited with the run; no decision or semantic fact write.
- **Endpoint/frontend:** `GET /api/v1/cases/{caseId}/agents/review-triage`; rendered as a review sequence on the Hybrid agent hub.
- **Tests:** Fixture order, empty result, unknown source IDs, and instruction-like title text.

### Graph-backed memory and handoff workflow / 0.2.0

- **Feature/page; mode and why; purpose:** Cross-cutting; precise fixed graph writes, source allowlists, bounded reads, stable idempotent IDs, and version-checked acknowledgement.
- **Inputs:** Case synthesis, verified context response, or bounded `{fromAgent,toAgent,task,state,sourceIds,context}` handoff.
- **Allowed tools:** `CaseGraph.remember_episode`, `list_episodes(limit≤100)`, `create_handoff`, `list_handoffs(limit≤100)`, `acknowledge_handoff(expectedVersion)`.
- **Output JSON:** Graph episode carries `caseId,agentId,kind,summary,evidenceState,sourceIds,payload,createdAt,version`; handoff carries `fromAgent,toAgent,task,state,sourceIds,context,status,version`.
- **Evidence states:** One of `observed|derived|candidate|hypothesis|unknown`; pending work itself may use only derived/candidate/hypothesis/unknown.
- **Guardrails:** One hashed graph per case; source IDs are case-filtered by API; no semantic fact promotion; no generated Cypher; runs require FalkorDB; acknowledgements use optimistic version checks.
- **Failure:** Graph unavailable or write/read failure returns explicit 503; stale handoff acknowledgement returns 409; retries reuse stable graph IDs.
- **Memory/audit:** FalkorDB is the primary memory; SQLite stores audit/idempotency only for new workflows. Historical SQLite memory migration is available via dry-run-first script.
- **Endpoint/frontend:** `/agents/memory`, `/agents/handoffs`, `/agents/handoffs/{id}/ack`, `/context/memory`, `/context/ask`, `/agents/hub[/run]`; hub shows recent episodes and pending/acknowledged handoffs.
- **Tests:** Case scope, ID filtering, evidence-state validation, bounded reads, JSON decoding, and optimistic acknowledgement.

### timeline-correlation / 0.1.0

- **Purpose:** Deterministic review-read-model scan surfaces temporal candidates and uncertainty.
- **Inputs/tools:** Open timeline/correlation review rows; case snapshot read only.
- **Output/state:** Candidate association with artifact IDs, clock/data-quality caveats, alternatives, and next step; hypothesis only.
- **Guardrails:** Timestamp proximity does not establish causation; no person-level narrative.
- **Endpoint:** Hybrid agent hub timeline workstream.

### research-mapper / 0.1.0

- **Purpose:** Deterministic curated references keep recommendations traceable to primary guidance and published benchmarks.
- **Inputs/tools:** Fixed NIST guidance and deepfake benchmark papers; no evidence payload or network retrieval during a run.
- **Output:** Reference ID, title, source link, and concrete evaluation/preservation use.
- **Guardrails:** Benchmark metrics do not establish field performance; recommend cross-domain and robustness evaluation.
- **Endpoint:** Hybrid agent hub research mapping panel.

### impact-assessment / 0.1.0

- **Purpose:** Maps known source, parser, clock, and media gaps to possible effects on interpretation.
- **Inputs/tools:** Open review rows and available case evidence IDs; case snapshot read only.
- **Output/state:** Possible impact, alternatives, source IDs, and examiner next step; derived or unknown.
- **Guardrails:** Never states definitive cause, actor, guilt, intent, or authenticity.
- **Endpoint:** Hybrid agent hub impact workstream.

### context-planner / 0.1.0

- **Feature/page; mode and why; purpose:** Entity graph; precise because request validation, policy routing, and tool selection are rule-computable. Chooses whether a bounded graph path request can proceed.
- **Inputs:** `caseId`, `entityId` (1–100 safe identifier characters), `question` (1–500 chars), `depth` (integer 1–3).
- **Allowed tools:** `graph.explain_entity(entityId, depth)` only; max depth 3 and 25 paths. The planner never creates Cypher or SQL.
- **Output JSON:** Ready plan with a fixed tool name and validated arguments; or a typed refusal/unsupported/invalid result.
- **Evidence states:** None; planning metadata is not an evidence claim.
- **Guardrails:** Refuses identity/responsibility, media verdict, intent, motive, and causation questions; unsupported parser, timestamp, transcript, speaker, and detector work returns a gap.
- **Failure:** Invalid argument → `422 INVALID_CONTEXT_QUERY` or `422 INVALID_DEPTH`; unsupported request → unknown gap; graph down → `503 FALKORDB_UNAVAILABLE`.
- **Memory/audit:** No direct memory write. Orchestrator records successful query as episodic/unverified only and audits every accepted query or unavailable dependency.
- **Endpoint/frontend:** `POST /api/v1/cases/{caseId}/context/ask`; response envelope `{data:{agent,question,answer,state,sources,statements,paths,gap,trace,...}}`, rendered in the Entity graph result panel.
- **Tests:** Depth bounds, fixture-based refusal, unsupported scope, service down, and idempotent repeat.

### context-narrator / 0.1.0

- **Feature/page; mode and why; purpose:** Entity graph; precise because wording is a fixed template over graph tool output. Emits examiner-readable, source-linked path statements.
- **Inputs:** Validated path rows from FalkorDB, case artifact ID allowlist, requested entity ID.
- **Allowed tools:** No tools. Receives only `graph.explain_entity` results; at most 25 paths.
- **Output JSON:** `{answer,state,sources,statements:[{text,state,sources}],observedNotes,paths,gap}`.
- **Evidence states:** `observed`, `candidate`, `derived`, `unknown` according to returned relationship states.
- **Guardrails:** Each statement must cite existing case artifact IDs. Untrusted instruction-like names are omitted and reported as observed content. Does not narrate person-level or causal conclusions.
- **Failure:** No verified source-linked path → unknown gap; any unknown artifact reference causes that path to be dropped.
- **Memory/audit:** No direct memory write; orchestrator may store the verified response as episodic/unverified. Query and source IDs are audited.
- **Endpoint/frontend:** Same `/context/ask` response; UI shows evidence-state labels, citations, sanitized paths, and gaps.
- **Tests:** Observed/candidate propagation, injection redaction, invented IDs, and empty graph result.

### context-verifier / 0.1.0

- **Feature/page; mode and why; purpose:** Cross-cutting; precise because schema, citation, source-allowlist, and forbidden-language checks are deterministic. Rejects unsafe narration.
- **Inputs:** Agent response JSON and case artifact ID allowlist.
- **Allowed tools:** None.
- **Output JSON:** `{ok:boolean,errors:string[]}`.
- **Evidence states:** Validates the five allowed states; it emits no evidence.
- **Guardrails:** Requires every factual statement to carry a state and real source citations; rejects invented source IDs and forbidden conclusions.
- **Failure:** Primary response fails verification → deterministic `evidence-path-agent` fallback; fallback failure → unknown gap and no answer retained.
- **Memory/audit:** No direct writes; verification result is in response and audit metadata.
- **Endpoint/frontend:** Same `/context/ask` envelope; frontend labels the evidence state and sources.
- **Tests:** Missing citation, invented ID, forbidden phrase, and fallback behavior.

### evidence-path-agent / 0.1.0

- **Feature/page; mode and why; purpose:** Entity graph; precise because it performs a fixed, bounded traversal and returns its source references. This is the existing deterministic fallback.
- **Inputs:** Case graph, entity ID, depth 1–3.
- **Allowed tools:** `graph.explain_entity(entityId, depth)`; fixed parameterized Cypher; max 25 paths.
- **Output JSON:** Source-filtered path rows plus evidence-state statements, or unknown gap.
- **Evidence states:** Observed/candidate/derived/unknown from stored edge metadata.
- **Guardrails:** No generated queries or identity/intent/causation claims; artifact references must belong to the case read model.
- **Failure:** FalkorDB unavailable → explicit 503; no fabricated paths.
- **Memory/audit:** Episodic/unverified only after successful query; audited.
- **Endpoint/frontend:** `/context/ask`; Entity graph path result panel.
- **Tests:** Bounded traversal, source filtering, empty path, and verifier fallback.

## Designed cards (not enabled)

The cards below are architecture contracts, not claims that the agent or connector exists. For every hybrid agent, the intended execution is **plan → validate fixed tool call → run tools → narrate only tool results → `verify_output()` → store**. A failed verification is retried once; then a deterministic result or explicit gap is returned. Model providers are not configured in this checkout.

### overview-metrics / 0.1.0

- **Feature/page; mode and why; purpose:** Case overview; precise counts and completeness from case rows.
- **Inputs:** `caseId`; read-model counts and timestamps.
- **Allowed tools:** `case.read_snapshot(caseId, limit≤250)`.
- **Output JSON:** Contract overview metrics object.
- **Evidence states:** Derived; each displayed metric includes source row IDs or metric provenance.
- **Guardrails:** No totals from absent pages; no fake live counts.
- **Failure:** Unknown metrics plus service gap.
- **Memory/audit:** None; read access audit only.
- **Endpoint/frontend:** `GET /cases/{caseId}/workspace`; `overview` fields and cards.
- **Tests:** Fixture counts, empty case, unavailable DB.

### case-brief / 0.1.0

- **Feature/page; mode and why; purpose:** Overview; hybrid for a short cited daily narrative.
- **Inputs:** Case overview and reviewed records only.
- **Allowed tools:** `case.read_snapshot(limit≤250)`, `review.list_approved(limit≤100)`.
- **Output JSON:** `{summary,statements:[{text,state,sources}],gaps[]}`.
- **Evidence states:** Observed/derived/unknown.
- **Guardrails:** No open hypothesis promoted to finding; no identity, intent, motive, guilt, or causation.
- **Failure:** Verified deterministic metric list or gap.
- **Memory/audit:** No semantic memory; audit prompt/version/output digest.
- **Endpoint/frontend:** Workspace read model; overview summary panel (contract extension required).
- **Tests:** Fixture citations, forbidden requests, injection, verifier, empty case.

### intake-integrity / 0.1.0

- **Feature/page; mode and why; purpose:** Evidence; precise streaming SHA-256, size, and re-verification.
- **Inputs:** Case ID, artifact ID, bytes/object version.
- **Allowed tools:** `artifact.read_chunks(size≤1MiB)`, `artifact.read_manifest()`.
- **Output JSON:** `{artifactId,sha256,size,status,verifiedAt}`.
- **Evidence states:** Derived integrity measurement, with artifact ID.
- **Guardrails:** Digest does not prove source authenticity; never overwrite originals.
- **Failure:** Integrity unknown or mismatch; quarantine and audit.
- **Memory/audit:** No agent memory; append-only integrity audit.
- **Endpoint/frontend:** Evidence rows with digest status; current upload computes a digest but re-verification agent is not implemented.
- **Tests:** Golden digest, changed bytes, zero-byte file, storage down.

### parser-coverage / 0.1.0

- **Feature/page; mode and why; purpose:** Source coverage; precise comparison only when explicit parser counters exist.
- **Inputs:** Optional case `parserManifest` rows with `sourceId`, `parsedCount`, and `referencedCount`; current fixture does not contain this manifest.
- **Allowed tools:** No external parser or connector; bounded in-memory manifest read (≤1000 rows).
- **Output JSON:** `{agent,state,items:[{sourceId,parsedCount,referencedCount,gapCount,state,gap}],gap,limits}`.
- **Evidence states:** Derived/unknown.
- **Guardrails:** No count is inferred from review prose; missing payload does not mean absent evidence; manifest source must exist in this case.
- **Failure:** Returns unknown and an explicit missing-manifest gap.
- **Memory/audit:** Included in case-synthesis episode; source manifest IDs remain attached.
- **Endpoint/frontend:** `GET /api/v1/cases/{caseId}/agents/parser-coverage`; status appears in the Hybrid Agent Hub.
- **Tests:** Missing manifest, valid/invalid counts, unknown source IDs.

### timeline-normalizer / 0.1.0

- **Feature/page; mode and why; purpose:** Timeline; precise conversion of explicit ISO-8601 offsets to UTC without timezone inference.
- **Inputs:** Existing case event rows (`id`, `timestamp` / `sourceTime` / `time`, `source`) and case evidence IDs.
- **Allowed tools:** Python ISO-8601 parser only; no external timezone database lookup or event connector.
- **Output JSON:** `{eventId,sourceTime,normalizedUtc,precision,offsetStatus,state,sources}`.
- **Evidence states:** Derived or unknown.
- **Guardrails:** Never infer a missing offset or increase precision; raw source time remains available; unsupported precision is an explicit unknown.
- **Failure:** Preserve raw value, normalized value null, explicit offset/parse gap.
- **Memory/audit:** None; parser version and source IDs audited.
- **Endpoint/frontend:** `GET /api/v1/cases/{caseId}/agents/timeline-normalizer`; Timeline page shows source time, normalized UTC, text precision, and offset status.
- **Tests:** Explicit UTC/offset conversion, missing offset, malformed timestamp, source-ID allowlist.

### correlation-agent / 0.1.0

- **Feature/page; mode and why; purpose:** Timeline; hybrid proposes candidate record links and alternatives.
- **Inputs:** Normalized events and source clock quality.
- **Allowed tools:** `timeline.query_window(hours≤24,limit≤500)`, `coverage.read_gaps(limit≤100)`.
- **Output JSON:** `{candidates:[{eventIds,state,sources,alternatives}],gaps[]}`.
- **Evidence states:** Candidate/hypothesis only.
- **Guardrails:** Temporal closeness never establishes causation.
- **Failure:** Deterministic time-ordered rows without correlations, or gap.
- **Memory/audit:** No semantic memory; candidate proposals audited.
- **Endpoint/frontend:** Timeline read model; columns/rows.
- **Tests:** REV-001 close-in-time pair, alternative explanation, offset unknown, injection.

### entity-extractor / 0.1.0

- **Feature/page; mode and why; purpose:** Entity graph; hybrid extracts candidate entities/edges from records.
- **Inputs:** Parsed records and parser provenance.
- **Allowed tools:** `artifact.read_derived_text(artifactId,limit≤20000)`, `entity.validate_schema()`.
- **Output JSON:** `{nodes,edges:[{state:"candidate",sourceIds}]}`.
- **Evidence states:** Candidate by default; observed only for deterministic source-record fields.
- **Guardrails:** No person identity resolution; evidence strings are untrusted; no generated Cypher.
- **Failure:** No graph write; explicit extraction gap.
- **Memory/audit:** Candidate graph projection only; audit model/version/source IDs.
- **Endpoint/frontend:** Entity page read model; graph projection rebuildable from source records.
- **Tests:** Shared account ambiguity, injection, malformed record, graph down.

### media-metadata / 0.1.0

- **Feature/page; mode and why; purpose:** Media; precise extraction of container/codec/duration metadata.
- **Inputs:** Artifact reference and immutable bytes.
- **Allowed tools:** `media.probe_sandboxed(timeout≤30s,bytes≤512MiB)`.
- **Output JSON:** Metadata fields with derived artifact and source ID.
- **Evidence states:** Derived/unknown.
- **Guardrails:** Metadata is not proof of authorship or authenticity; parser runs isolated.
- **Failure:** Explicit parse failure; preserve original.
- **Memory/audit:** No memory; tool and binary versions audited.
- **Endpoint/frontend:** Media page rows through page API.
- **Tests:** Valid/invalid container, oversized file, parser unavailable.

### transcript-attribution / 0.1.0

- **Feature/page; mode and why; purpose:** Media/review; precise draft of existing diarization labels, when supplied.
- **Inputs:** Optional case `transcriptSegments` with `segmentId`, `speakerLabel`, source ID, and optional start/end fields; current fixture does not contain these segments.
- **Allowed tools:** No speech model; bounded in-memory segment read (≤2000).
- **Output JSON:** `{agent,state,draftOnly,speakerLabels:[{segmentId,speakerLabel,start,end,state,sourceId}],sourceIds,gap,examinerNextStep,limits}`.
- **Evidence states:** Derived/candidate/unknown.
- **Guardrails:** Speaker label is not a person; never attribute an account owner; no identity or examiner decision; sources must be case-known.
- **Failure:** Returns unknown gap when segments are absent or fail schema checks.
- **Memory/audit:** Output included in synthesis episode; no semantic promotion.
- **Endpoint/frontend:** `GET /api/v1/cases/{caseId}/agents/transcript-attribution`; output is summarized in the Hybrid Agent Hub.
- **Tests:** No-segment gap, known/unknown source IDs, label-only output.

### media-screening / 0.1.0

- **Feature/page; mode and why; purpose:** Deepfake lab; precise wrapper around a separately validated detector.
- **Inputs:** Artifact ID, derived media, model manifest and calibration.
- **Allowed tools:** `detector.run_validated(profile,timeout≤300s)` only.
- **Output JSON:** Contract media-run record with model/version, signals, limitations, derived refs.
- **Evidence states:** Derived screening cue only.
- **Guardrails:** Never emit authentic/fake verdict; never alter score; do not run if model manifest invalid.
- **Failure:** `NO_VALIDATED_MODEL`; no score. This fail-closed branch exists today.
- **Memory/audit:** No semantic memory; run manifest and audit event.
- **Endpoint/frontend:** `POST/GET /media-runs`; current POST writes failed record because no model exists.
- **Tests:** No model, invalid manifest, calibrated golden file, connector down.

### review-recorder / 0.1.0

- **Feature/page; mode and why; purpose:** Review queue; precise append-only human decision recording.
- **Inputs:** Case/review IDs, examiner actor, decision enum, note, source refs.
- **Allowed tools:** `review.validate_open_item()`, `audit.append()`.
- **Output JSON:** `{decisionId,status,createdAt}`.
- **Evidence states:** None; decision is examiner-authored.
- **Guardrails:** Agent cannot call with an examiner identity; append only, no overwrite.
- **Failure:** Reject unknown/closed item or unavailable audit store.
- **Memory/audit:** No memory; current `/reviews/{reviewId}/decision` appends to SQLite with a development actor only.
- **Endpoint/frontend:** Existing write endpoint and review cards.
- **Tests:** Idempotency, unknown review, append-only history, audit failure.

### scope-checker / 0.1.0

- **Feature/page; mode and why; purpose:** Acquisitions; precise validation against approved scope.
- **Inputs:** Case scope version, connector, requested UTC range, reason, handling mode.
- **Allowed tools:** `scope.read_approved(caseId)`, `connector.describe(connectorId)`.
- **Output JSON:** `{allowed,scopeVersion,violations[]}`.
- **Evidence states:** Derived authorization check.
- **Guardrails:** Cannot expand scope or submit a request; examiner approval required.
- **Failure:** Deny/unknown; current service does not enforce real authorization.
- **Memory/audit:** None; all checks audited.
- **Endpoint/frontend:** Acquisition write contract; current endpoint only checks required fields.
- **Tests:** In-range, out-of-range, missing scope, connector unavailable.

### acquisition-planner / 0.1.0

- **Feature/page; mode and why; purpose:** Acquisitions; hybrid drafts source requests from documented gaps.
- **Inputs:** Approved scope, source coverage gaps, connector catalog.
- **Allowed tools:** `coverage.read_gaps(limit≤100)`, `scope.read_approved()`, `connector.catalog(limit≤100)`.
- **Output JSON:** Draft request fields plus source citations and `requiresExaminerApproval:true`.
- **Evidence states:** Hypothesis/derived.
- **Guardrails:** Never dispatch or widen authorization; no connector credential access.
- **Failure:** No draft, explicit dependency gap.
- **Memory/audit:** Draft-only episodic trace; audit source records.
- **Endpoint/frontend:** Acquisition request draft; current acquisition endpoint persists local request only.
- **Tests:** Source gap mapping, invalid scope, no connector, injection.

### report-drafter / 0.1.0

- **Feature/page; mode and why; purpose:** Reports; hybrid drafts a source-linked report from reviewed records.
- **Inputs:** Examiner-reviewed items, approved scope, open gaps.
- **Allowed tools:** `review.list_examiner_reviewed(limit≤500)`, `coverage.read_gaps(limit≤100)`, `case.read_manifest()`.
- **Output JSON:** Draft sections and statement citations; `draftOnly:true`.
- **Evidence states:** Observed/derived/candidate/hypothesis/unknown, copied from inputs.
- **Guardrails:** No unreviewed claims promoted; never publish or sign.
- **Failure:** Empty draft with missing-source gap.
- **Memory/audit:** No semantic memory; draft versions audited.
- **Endpoint/frontend:** Reports page; current `/reports` stores metadata only.
- **Tests:** Reviewed-only, missing citation, injected text, renderer unavailable.

### claim-verifier / 0.1.0

- **Feature/page; mode and why; purpose:** Reports; precise schema, source existence, and policy checks.
- **Inputs:** Draft statements and case source-ID allowlist.
- **Allowed tools:** `artifact.exists_in_case(artifactId)`; fixed local policy rules.
- **Output JSON:** `{valid,issues:[{claimId,code,sourceIds}]}`.
- **Evidence states:** Derived validation only.
- **Guardrails:** Cannot judge truth or examiner decision.
- **Failure:** Invalid/unknown; block export creation.
- **Memory/audit:** None; verification result audited.
- **Endpoint/frontend:** Report export gate; endpoint not implemented.
- **Tests:** Invented ID, missing citation, empty claim, artifact service down.

### claim-judge / 0.1.0

- **Feature/page; mode and why; purpose:** Reports; hybrid proposes source entailment checks where language understanding is required.
- **Inputs:** Draft claim and exact cited source excerpts.
- **Allowed tools:** `artifact.read_excerpt(artifactId,span≤4000chars)` only.
- **Output JSON:** `{supportLevel,quotedSourceRefs,alternatives,requiresExaminerReview:true}`.
- **Evidence states:** Hypothesis/unknown, never fact promotion.
- **Guardrails:** No uncited assertion, no generated SQL/Cypher, injected excerpts ignored as instructions.
- **Failure:** Unknown support, examiner review required.
- **Memory/audit:** No semantic memory; audit model/version and excerpt references.
- **Endpoint/frontend:** Report claim review; requires new endpoint and approved model.
- **Tests:** Supported/contradicted/ambiguous, injection, missing source, model down.

### service-health / 0.1.0

- **Feature/page; mode and why; purpose:** Settings; precise dependency status and capability probe.
- **Inputs:** Health status for DB, FalkorDB, model, object store, connectors.
- **Allowed tools:** `health.probe(component)` with a fixed allowlist and timeout≤2s.
- **Output JSON:** `{component,status,checkedAt,capabilities,gap}`.
- **Evidence states:** Observed operational status.
- **Guardrails:** Never reveal credentials or paths containing secrets.
- **Failure:** Degraded/unknown per component.
- **Memory/audit:** No memory; health request audit optional.
- **Endpoint/frontend:** `/health` and settings page. Current endpoint reports SQLite/FalkorDB/model only.
- **Tests:** Each dependency state and secret-free errors.

### case-search / 0.1.0

- **Feature/page; mode and why; purpose:** Search; precise case-scoped literal search.
- **Inputs:** Case ID, query≤120 chars, limit 1–25.
- **Allowed tools:** `case.search_index(query,limit≤25)`.
- **Output JSON:** `{data:{items:[{id,label,detail,route}]}}`.
- **Evidence states:** No conclusions; each item has a real record ID.
- **Guardrails:** Case isolation, escaped UI output, no cross-case results.
- **Failure:** Empty results or explicit API error.
- **Memory/audit:** None; query log policy is service-level.
- **Endpoint/frontend:** Existing `GET /search`; global search result list.
- **Tests:** Case isolation, empty query, limit, special characters.

### notification-router / 0.1.0

- **Feature/page; mode and why; purpose:** Notifications; precise routing of completed runs with review signals.
- **Inputs:** Completed media runs and open review IDs.
- **Allowed tools:** `media.list_completed(limit≤100)`, `review.exists(reviewId)`.
- **Output JSON:** `{items:[{runId,artifactId,route,sourceIds}]}`.
- **Evidence states:** Derived workflow status only.
- **Guardrails:** Queued/failed runs do not alert; no verdict language.
- **Failure:** No notifications and status gap.
- **Memory/audit:** Delivery receipt only, no semantic memory; audit deliveries.
- **Endpoint/frontend:** Existing notification drawer reads completed run rows client-side; backend router/delivery is not implemented.
- **Tests:** Completed-with-signals, queued, duplicate delivery, store down.

### orchestrator / 0.1.0

- **Feature/page; mode and why; purpose:** Cross-cutting; hybrid only when multi-tool language planning is enabled by an approved provider.
- **Inputs:** User task, case scope, agent registry.
- **Allowed tools:** Fixed registry names only; per-tool limits enforced in code.
- **Output JSON:** Typed plan, tool trace, verified statements, or gap.
- **Evidence states:** Inherits verified child outputs only.
- **Guardrails:** No direct SQL/Cypher; no decision writes; never trust evidence strings as instructions.
- **Failure:** Deterministic agent or explicit dependency gap.
- **Memory/audit:** Episodic trace separated from reviewed semantic memory; audit every tool call.
- **Endpoint/frontend:** Not implemented; current graph route directly invokes deterministic orchestrator.
- **Tests:** Tool allowlist, argument bounds, fallback, injection, all dependencies down.

### memory / 0.1.0

- **Feature/page; mode and why; purpose:** Cross-cutting; precise storage and retrieval of typed memory records.
- **Inputs:** Query/trace and examiner-reviewed item references.
- **Allowed tools:** `memory.append_episode(caseId,limit≤1)`, `memory.read_recent(caseId,limit≤100)`.
- **Output JSON:** `{memoryId,kind,sourceIds,reviewState}`.
- **Evidence states:** Episode is unverified; semantic memory only after examiner review.
- **Guardrails:** Candidate links never become facts; strict case scope; retention/erase policy applies.
- **Failure:** Do not store and return explicit storage gap.
- **Memory/audit:** New episodic graph queries are stored in FalkorDB as unverified episodes; no semantic promotion exists. Legacy SQLite rows can be copied with the migration script.
- **Endpoint/frontend:** `/context/memory` and Entity graph panel.
- **Tests:** Case isolation, unverified label, reviewed promotion gate, empty store.

## Contracts and implementation notes

- Existing v1 contract: `ui-prototype/BACKEND_CONTRACT.md`. Generic page rows are `{schemaVersion,title,summary,metrics,columns,rows,updatedAt}`; workspace and media-run shapes are documented there.
- Existing SQLite tables: `cases`, `review_decisions`, `case_records`, `media_runs`, `artifact_files`, `audit_events`, `idempotency_keys`, `agent_memory`.
- FalkorDB label/relation projection: `CaseEntity`; fixed relationship types `AUTHENTICATED_AS`, `OBSERVED_ON`, `DOWNLOADED`, `USED`, `TRANSFERRED_FROM`, with `state` and `artifactId` properties.
- The prompt said `agent_prompts.py` already exists; it did not exist in the inspected checkout. A provider-neutral compatible module was added without introducing an LLM dependency. It must be reviewed before connecting a model provider.
- The Northstar fixture and demo graph are fictional. Do not use them as evidence or load their graph into a real investigation.
