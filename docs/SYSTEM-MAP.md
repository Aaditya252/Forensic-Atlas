# Forensic Atlas — consolidated system map

Everything needed to run, understand, and verify this system now lives in
`D:\projects\Forensics`. This document lists the files that make it work, the
data models they read and write, and the connections between them.

Last consolidation: 2026-10-18. Verified after the move: 69 unit tests, live
phase checks 1–7, audio screen, and both public-media workflow packs.

## 1. Where everything lives

| Path | Role |
| --- | --- |
| `backend/` | FastAPI service, deterministic agents, graph/report/media modules |
| `ui-prototype/` | Served dashboard (`index.html`) and case library (`cases.html`) |
| `models/phase2/` | Pinned Qwen3.5-2B Q4_K_M weights (1.28 GB) + license/checksum manifest |
| `models/aasist-l/` | Pinned AASIST-L audio screening weights (research only) |
| `local-runtime/` | Portable llama.cpp server (`llama-b11718`) |
| `cases/storage/` | SQLite case store + immutable uploaded originals |
| `cases/graph-data/` | FalkorDB persistence mounted into the app's container |
| `cases/public/` | Downloaded research samples with per-pack import manifests |
| `cases/backups/` | Pre-migration DB snapshots and selected graph dumps |
| `datasets/evaluation/` | Memory evaluation corpora (not evidence, not training) |
| `scripts/` | Startup, downloads/imports, and every `verify_*.py` tool |
| `docs/` | Phase notes plus this map |
| `output/` | API/model logs, PIDs, verification JSON, screenshots, fixtures |
| `tools/falkordb-orchestrator/` | Standalone FalkorDB + OpenAI orchestrator CLI (independent of the app) |

Archived originals (not needed to run; kept for comparison):
`D:\projects\.archive\Forensics-pre-consolidation-20261018-2048` (older slice),
`D:\projects\.archive\digital-forensics-source-20261018` (the copy previously in
`C:\Users\adive\Downloads\rf-dashboard\digital-forensics`).

## 2. Files that make it work

### Entry points

| File | What it does |
| --- | --- |
| `scripts/start_forensic_atlas.ps1` | Ensures Docker, starts the graph container, exports `FALKORDB_URL`, starts the local model then the API, waits for `/health` |
| `backend/app.py` | FastAPI app, 39 routes, SQLite helpers, upload/stream/report logic (`python -m backend.app --seed-demo --sync-demo-graph`) |
| `ui-prototype/index.html` + `app.js` | Dashboard shell; loads modules from `ui-prototype/src/` |
| `ui-prototype/cases.html` | Case library listing `cases/index.json` |
| `ui-prototype/runtime-config.js` | `dataMode: 'api'`, `apiBaseUrl: http://127.0.0.1:8100`, case `DF-24-017` |

### Backend modules

| File | Role |
| --- | --- |
| `backend/graph_store.py` | `CaseGraph`: per-case graph naming, demo projection, entity/path queries, episodes, handoffs |
| `backend/agents/hybrid_hub.py` | 14-agent roster + deterministic case brief synthesis |
| `backend/agents/context_orchestrator.py`, `context_planner.py`, `context_narrator.py` | Bounded graph-question pipeline (plan → narrate → verify) |
| `backend/agents/case_summary.py` | Selects and orders verified fact IDs for a cited draft |
| `backend/agents/memory_recall.py` | Bounded recall over saved FalkorDB episodes |
| `backend/agents/review_triage.py`, `timeline_normalizer.py`, `parser_coverage.py`, `transcript_attribution.py`, `media_context.py` | Specialist rules |
| `backend/agent_prompts.py` | Prompt text for the local model path |
| `backend/local_llm.py` | Client for the llama.cpp server on 8111; status/provenance |
| `backend/media_inspection.py` | Bounded ffprobe metadata inspection |
| `backend/waveform.py` | Measured min/max/RMS PCM waveform extraction |
| `backend/audio_screen.py` | Experimental, windowed AASIST-L screening (never a verdict) |
| `backend/relationship_view.py` | Graph view model for the entity explorer |
| `backend/reporting.py` | Cited report envelope, content SHA-256, printable HTML |
| `backend/demo-workspace.json` | Fictional Northstar fixture (case `DF-24-017`) |
| `backend/schema.sql` | SQLite DDL (applied idempotently at startup) |
| `backend/tests/` | 13 files, 69 tests; fake graph adapters, no live services needed |

### Frontend modules (`ui-prototype/src/`)

`services/api-client.js` (bounded fetch, request IDs, idempotency keys),
`services/workspace-repository.js` (API boundary for pages and graph agent),
`config.js`, `data/demo-workspace.js`, and `ui/`: `audio-screen.js`,
`audio-waveform.js`, `cited-reports.js`, `deepfake-page.js`, `entity-map.js`,
`handoff-inbox.js`, `media-inspection.js`, `memory-recall.js`, `test-upload.js`.
Styles in `ui-prototype/styles.css` (~116 KB).

## 3. Data models

### 3.1 SQLite — `cases/storage/sutram.sqlite3`

Case record store (append-only decisions, idempotency, audit). 11 tables:

| Table | Purpose | Key columns |
| --- | --- | --- |
| `cases` | Case read model | `case_id` PK, `snapshot_json`, `created_at`, `updated_at` |
| `artifact_files` | Registered originals + digest | `artifact_id` PK, `case_id`, `original_name`, `media_type`, `source_label`, `byte_size`, `sha256`, `stored_path`, `created_at` |
| `artifact_inspections` | Saved ffprobe inspections | `id` PK, `case_id`, `artifact_id`, `result_json`, `created_at` |
| `audio_screenings` | Saved research audio screens | `id` PK, `case_id`, `artifact_id`, `result_json`, `created_at` |
| `media_runs` | Detector run records (fail closed) | `id` PK, `case_id`, `artifact_id`, `status`, `request_json`, `result_json`, timestamps |
| `review_decisions` | Examiner decisions | `id` PK, `case_id`, `review_id`, `decision`, `note`, `actor`, `created_at` |
| `case_records` | Acquisition/report/export requests | `id` PK, `case_id`, `kind`, `status`, `payload_json`, `created_at` |
| `report_snapshots` | Immutable cited reports | `id` PK, `case_id`, `title`, `summary_episode_id`, `envelope_json`, `content_sha256`, `created_at` |
| `audit_events` | Append-only audit trail | `id` PK, `case_id`, `actor`, `action`, `entity_type`, `entity_id`, `details_json`, `created_at` |
| `idempotency_keys` | Replay-safe responses | PK (`case_id`, `key`), `response_json`, `created_at` |
| `agent_memory` | Legacy SQLite memory (no longer written; migrated to FalkorDB) | `id` PK, `case_id`, `agent_id`, `entity_id`, `question`, `answer`, `sources_json`, `result_json`, `created_at` |

Indexes exist on `(case_id, created_at)` for audit, records, runs, memory,
artifacts, reports, inspections and screenings. Current contents: 4 cases,
25 artifacts, 150 audit events, 7 report snapshots.

Uploaded bytes: `cases/storage/evidence/<sha256(caseId)[:20]>/ART-xxxxxxxx.ext`.
`stored_path` is absolute; after this move all 25 rows were rewritten to the
new root. A pre-rewrite backup is at
`cases/backups/pre-consolidation-path-rewrite.sqlite3`.

### 3.2 FalkorDB — one graph per case

Graph name: `sutram_case_` + `sha256(case_id)[:16]` (`graph_store.graph_name`).
Current app graphs: `sutram_case_eb5d0eed170c4828` (DF-24-017),
`…92399886924b2a6b`, `…0e519638d0375fd1`, `…91c78ab9d2316bec`,
`…164cd2eb42e569e3`.

| Node label | Properties |
| --- | --- |
| `CaseEntity` | `caseId, id, label, name, source, claim` (`claim` = observed/candidate) |
| `AgentEpisode` | `caseId, id, agentId, kind, summary, evidenceState, sourceIdsJson, payloadJson, idempotencyKey, createdAt, version` |
| `AgentRun` | `caseId, id, agentId, createdAt` |
| `AgentHandoff` | `caseId, id, state, sourceIdsJson, idempotencyKey, createdAt, version, fromAgent, toAgent, task, contextJson, status` |
| `AgentIdentity` | `caseId, id` |

| Relationship | Props | Meaning |
| --- | --- | --- |
| `AUTHENTICATED_AS` | `caseId, state, artifactId` | Session → account |
| `OBSERVED_ON` | `caseId, state, artifactId` | Session → device |
| `DOWNLOADED` | `caseId, state, artifactId` | Session → file |
| `USED` | `caseId, state, artifactId` | Account → device |
| `TRANSFERRED_FROM` | `caseId, state, artifactId` | File → network endpoint |
| `RECORDED_AS` | `caseId` | Episode → saved artifact/run |
| `SUPPORTED_BY` | `caseId` | Episode/handoff → source IDs |
| `ASSIGNED_TO` | `caseId` | Run/episode → agent identity |
| `HANDED_OFF_TO` | `caseId` | Handoff routing between specialists |

### 3.3 Workspace snapshot (`snapshot_json` / `demo-workspace.json`)

`schemaVersion`, `case` (id, title, status, description, leadExaminer,
openedAt, authority, classification), `overview` (counters, coverage,
lastIntegrityCheck), `evidence[]` (id, name, type, source, date, size, status,
icon), `reviewItems[]`, `sourceCoverage[]`, `events[]` (id, time, timestamp,
color, title, desc, source), `updatedAt`. The API enriches `evidence` at read
time from `artifact_files` and adds `sha256`, `hasStoredBytes`, `hasAudioTrack`.

### 3.4 Local model provenance

`models/phase2/manifest.json` pins model ID `forensic-atlas-qwen35-2B`,
upstream `Qwen/Qwen3.5-2B`, Q4_K_M, revision and SHA-256. `/health` reports
`trainedByUs: false`; the model only selects fact IDs for extractive summaries.

## 4. Connections and configuration

| Service | Address | Notes |
| --- | --- | --- |
| API + dashboard | `http://127.0.0.1:8100` | `/health`, `/cases.html` |
| Local model (llama.cpp) | `http://127.0.0.1:8111` | started by `start_phase2_model.ps1` |
| App FalkorDB (RESP) | `127.0.0.1:6380` | container `forensic-atlas-local-graph` |
| App FalkorDB browser | `http://127.0.0.1:3001` | same container |
| Legacy shared FalkorDB | `127.0.0.1:6379`, browser `3000` | container `falkordb`; used only by `tools/falkordb-orchestrator` |

Environment variables: `FALKORDB_URL` (default `redis://127.0.0.1:6380`),
`SUTRAM_DB_PATH`, `SUTRAM_UI_PATH`, `SUTRAM_API_HOST`, `SUTRAM_API_PORT`,
`SUTRAM_CORS_ORIGINS`, `SUTRAM_SEED_DEMO`.

The graph container bind-mounts an absolute path:

```
D:\projects\Forensics\cases\graph-data  ->  /var/lib/falkordb/data
```

Because the bind path is absolute, the container was recreated after the move
(`docker rm` + `docker run` with the pinned image). All five case graphs were
confirmed present afterwards. If this folder is relocated again, repeat that
step; do not copy the AOF files while the container is running.

## 5. Run and verify

```powershell
cd D:\projects\Forensics
powershell -ExecutionPolicy Bypass -File scripts\start_forensic_atlas.ps1
```

Open `http://127.0.0.1:8100/cases.html`. The launcher is idempotent: it reuses
the running API if the health check reports the same database path.

Verification commands (all from the project root, with the stack running):

```powershell
python -m unittest discover -s backend/tests -q
python scripts/verify_phase1.py   # …verify_phase7.py
python scripts/verify_audio_screen.py
python scripts/verify_public_media_workflows.py
python scripts/verify_public_media_workflows.py --pack deepfake-audio
```

## 6. Verification results recorded on 2026-10-18

- `unittest`: 69 tests, OK.
- `verify_phase1`–`verify_phase7`: every check PASS, including graph outage
  fail-closed, idempotent replay, digest verification, and both local-model
  summary paths.
- `verify_audio_screen`: 22 checks PASS (see fix below); result written to
  `output/research-audio-screen-verification.json`.
- `verify_public_media_workflows`: 12 checks PASS for the default pack and 12
  for `--pack deepfake-audio`.
- `/health`: `status: ok`, SQLite connected, FalkorDB connected, local LLM
  `local-ready`, validated media detector `false`.
- `tools/falkordb-orchestrator/orchestrator.py`: HEALTHY, connected to
  `127.0.0.1:6379`, sample evidence written and persisted.

## 7. Changes made during consolidation

1. Copied the complete application tree into `D:\projects\Forensics`
   (341 files, 1.42 GB) and archived the older slice that was there.
2. Rewrote 25 absolute `stored_path` values in SQLite after taking a backup;
   verified every path resolves on disk.
3. Recreated the graph container against the new bind path and confirmed all
   five case graphs survived.
4. Fixed `scripts/verify_audio_screen.py`: it assumed `flower.mp4` was silent,
   but that file has an AAC track. The verifier now generates a genuinely
   silent MP4, registers it through the normal intake API (reused on repeat
   runs), and asserts the 422 "no audio" response on it.
5. Fixed `tools/falkordb-orchestrator/orchestrator.py`: `link_evidence()`
   built its Cypher and parameters but never ran the query and returned
   `None`. It now executes the query and returns whether the link was made.
6. Archived the previous `C:\Users\adive\Downloads\rf-dashboard\digital-forensics`
   copy to `D:\projects\.archive` (no data deleted; frees space on C:).

## 8. Known limits

- Local development only; loopback-bound, no authentication provider.
- No validated deepfake detector: those runs fail closed with no scores.
- Audio screening is an experimental research baseline, not accuracy validation.
- `agent_memory` in SQLite is legacy; active memory is in FalkorDB.
- Do not expose this service beyond loopback or use it on real case data
  without the custody, encryption, and authorization work described in the
  backend README.
