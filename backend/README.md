# Forensic Atlas backend

This local service gives the dashboard a persistent API boundary. SQLite stores the case read model, append-only review decisions, queued case records, detector run records, idempotency responses, and audit events. FalkorDB is the case relationship and agent-memory store; evidence paths, episodic memory, and handoff state are read from and written to each case graph.

The included Northstar records are fictional development fixtures. They are never evidence and must not be used for a real investigation.

## Start the local API

From the repository root in PowerShell:

```powershell
.\scripts\start_forensic_atlas.ps1
```

This starts Docker Desktop when necessary, reuses the existing local FalkorDB container, enables append-only persistence, and starts the API in the background. New containers use a pinned image and a named data volume. The dashboard in `ui-prototype` is static HTML/CSS/JS served by FastAPI; it does not require the repository root's Vite build. Logs and the API PID are written under `output/`.

For a fresh Python environment, install dependencies first:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m backend.app --seed-demo
```

The service also hosts the matching frontend on `127.0.0.1:8100`. Open `http://127.0.0.1:8100/`. Its API mode never substitutes browser fixtures when the service is unavailable.

## FalkorDB graph context

The hackathon page calls FalkorDB mandatory and expects the graph to shape agent behavior. This app uses one isolated graph name per case and provides a bounded graph path tool at `POST /api/v1/cases/{caseId}/context/ask`. `context-planner` chooses only the fixed graph tool; `context-narrator` renders evidence-state statements from its source-filtered results; `context-verifier` rejects unsupported claims and IDs. A verifier failure falls back to `evidence-path-agent`. The request depth is 1–3 hops and output is capped at 25 paths. Identity, intent, motive, guilt, causation, and media-verdict questions are refused; parser/time/transcript tasks remain unsupported. Accepted query results and case synthesis are retained as episodic, unverified FalkorDB nodes; SQLite holds audit and idempotency records. No semantic facts are promoted without examiner review.

Start the official local container when Docker is available:

```powershell
docker run --name sutram-falkordb -p 6379:6379 -p 3000:3000 -d falkordb/falkordb:latest
python -m backend.app --sync-demo-graph
```

The demo graph command merges fixture nodes and relationships without deleting the graph, agent episodes, or handoffs. It is restricted to the fictional Northstar case. Set `FALKORDB_URL` to a different RESP URL for an existing service. `/health` reports a degraded state if either SQLite or FalkorDB is unavailable. The API returns an explicit unavailable response when graph reasoning cannot reach FalkorDB; it does not fall back to fabricated paths.

## Hybrid agent hub

Open **Hybrid agent hub** and run the case synthesis. The coordinator combines case-scoped evidence/coverage, timeline review candidates, FalkorDB availability, detector configuration, impact alternatives, deterministic review triage, and curated research links. A run stores an episode and routes bounded pending tasks to enabled specialists in FalkorDB. Each handoff keeps case-known source IDs and an evidence state; a receiver can acknowledge it with an optimistic version check. `GET /api/v1/cases/{caseId}/agents/hub` returns the roster, latest run, recent memory, and handoffs; `POST /api/v1/cases/{caseId}/agents/hub/run` performs an audited, idempotent run. The coordination run uses deterministic tools and rules. The separate cited summary action uses the local LLM; no validated deepfake detector is configured. Cause and impact are candidate explanations, not findings.

## Phase 2 local model

The Agent Hub now includes **Cited case summary**, an explicit local Qwen3.5-2B action. It selects and orders validated fact IDs from the case snapshot and bounded FalkorDB paths. Rendering copies the exact statements, citations, and evidence states into an unreviewed draft. It performs no training and no media authenticity detection. Run `python scripts/setup_phase2_model.py` for the pinned model/runtime downloads; the normal startup script then starts the model service too. See [Phase 2 details](../docs/phase-2-local-summary.md).

## What is live in this slice

Phase 7 adds measured min/max/RMS waveform inspection and seekable playback for uploaded PCM WAV audio. See [Phase 7 details](../docs/phase-7-pcm-waveform.md). Read-only verification: `python scripts/verify_phase7.py`.

Phase 6 connects saved media inspections to the coordinator, local cited summary, FalkorDB provenance, and report snapshots. The Agent Hub displays historical observations with source IDs and next steps. See [Phase 6 details](../docs/phase-6-media-agent-context.md). Live verification: `python scripts/verify_phase6.py` after Phase 5 verification.

Phase 5 adds real byte hashing and bounded ffprobe metadata inspection for uploaded media on the Media analysis page. Results and source references persist in SQLite; no detector score is generated. See [Phase 5 details](../docs/phase-5-media-inspection.md). Live verification: `python scripts/verify_phase5.py`.

Phase 4 connects Reports to saved cited summaries with immutable SQLite snapshots, exact-source verification, printable standalone HTML, and JSON content hashes. See [Phase 4 details](../docs/phase-4-cited-reports.md). Live verification: `python scripts/verify_phase4.py`.

Phase 3 adds **Recall earlier work** in the Agent Hub: bounded text/source/agent search over saved FalkorDB episodes and direct inspection of source-linked statements and traces. See [Phase 3 details](../docs/phase-3-memory-recall.md). Read-only live verification: `python scripts/verify_phase3.py`.

- Case overview and page read models, case search, and media-run history
- Local-development artifact intake with streamed size checks, SHA-256 registration, scoped byte retrieval, and audit events
- SQLite persistence for examiner decisions, report drafts, acquisition requests, and export requests
- Idempotency keys and request-correlated append-only audit events
- FalkorDB case graph projection, entity retrieval, and explainable bounded path queries
- A media-run record that explicitly fails closed while no validated detector is configured
- Deterministic context planner, evidence-only narrator, output verifier, and safe graph fallback
- FalkorDB-backed episodic memory, deterministic review triage, and versioned specialist handoffs
- Conservative timeline normalization that preserves source time and refuses to infer missing offsets
- Local LLM fact selection, exact-source summary verification, model provenance, persistent drafts, and audited idempotent summary endpoints

## Agent tests

From the repository root run `python -m unittest discover -s backend/tests -v`. The tests use the fictional fixture plus fake graph adapters; they do not require FalkorDB or an LLM provider.

For live verification, install `backend/requirements-dev.txt` and run `python scripts/verify_phase1.py`. This uses disposable fictional case data and removes only the random graphs it created. `python scripts/verify_phase1.py --restart-container falkordb` also checkpoints and gracefully restarts the named container, briefly affecting all graphs in that container. Results are written to `output/phase1-verification.json`. The completed Phase 1 checks and durability limits are documented in `docs/phase-1-foundation.md`.

## Not yet enabled

No cloud acquisition is implemented. A local-development file upload stores bytes under the backend data directory and records a digest, but this is not a validated chain-of-custody process. There is no validated deepfake model, source connector, authentication provider, or server PDF renderer yet. The local LLM provider is enabled for extractive summary selection only. Additional feature agents are specified in `backend/agents/AGENT_CARDS.md` and remain disabled until their data contracts and tools exist. These are separate build slices; the API does not fabricate detector outputs or represent local development storage as a certified evidence vault.

Legacy SQLite `agent_memory` rows are no longer read or written by active workflows. Review `scripts/migrate_agent_memory_to_falkordb.py` in dry-run mode, then run it with `--apply` to copy historical rows into case graphs. The script filters sources against each case snapshot and uses stable graph IDs for safe retries; FalkorDB must be available for every case being migrated.

Before using real case data, add reviewed identity and case-scope authorization, encrypted immutable object storage, upload resumption, malware and parser isolation, custody verification, retention controls, backups, and security review. Do not expose this development service beyond loopback.
