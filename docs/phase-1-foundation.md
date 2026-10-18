# Phase 1 — local foundation verification

Completed on 18 October 2026 against the installed local Docker/FalkorDB service. The machine-readable check results are in `output/phase1-verification.json`; `output/phase1-dashboard.png` records the browser result.

## Working behavior

- The FastAPI service and matching static dashboard run on `http://127.0.0.1:8100/`. The health endpoint identifies the service and checks both SQLite and FalkorDB.
- The existing FalkorDB container is reused. Its published ports are bound to loopback, and its data directory is already mounted on persistent storage. No unrelated graphs are replaced.
- Fixture graph setup now MERGEs nodes and relationships. It does not delete case memory or handoffs. Every fixture artifact has a reference node for memory provenance.
- Evidence-path traversal only follows the five allowlisted forensic relationship types. Memory/support/handoff edges cannot become intermediate investigative paths.
- The five older fictional case summaries were copied from SQLite into FalkorDB with stable IDs and migration audit records. The original SQLite rows were retained.
- The browser can run the coordinator, view its source-linked output, read five open review items, and see four persisted specialist handoffs. Missing media/transcript/parser providers remain explicit gaps.

## Verification performed

The live smoke script checks all page read models; verified graph context; run persistence and replay; four specialist handoffs; acknowledgement, replay and stale-version rejection; source validation; case isolation; explicit graph-outage responses; SQLite audit writes without new SQLite memory; preservation of memory and handoffs during fixture reseeding; and absence of duplicate fixture entities.

For the persistence check, the script issues a disk checkpoint, gracefully restarts the actual local FalkorDB container, reconnects, and verifies the run ID and acknowledged handoff version. A new API lifecycle then reads the same persisted run. The browser was refreshed against the updated API and a new coordinator run was visibly verified. The existing 18 unit tests also passed after the changes.

These checks establish local functional behavior. They do not measure production concurrency, tenant authorization, host power-loss recovery, or forensic model accuracy. The restart test explicitly uses a checkpoint and a graceful restart; it is not a crash-recovery result.

## Starting the app

From the repository root, run:

```powershell
.\scripts\start_forensic_atlas.ps1
```

The script starts the installed Docker Desktop engine when required, prefers an existing recognized FalkorDB container, and creates one with a pinned image and named persistent volume only when none exists. It enables AOF on every app startup. Newly created containers also receive AOF in their boot environment. Existing user containers are not recreated: their original boot configuration remains in place, so use this script after restarting them to reapply runtime AOF. The script refuses to replace an unrelated service already occupying the API port.

For live verification:

```powershell
python -m pip install -r backend\requirements-dev.txt
python scripts\verify_phase1.py
```

To explicitly include a graceful restart of the local database container:

```powershell
python scripts\verify_phase1.py --restart-container falkordb
```

The restart affects all graphs in that container. The smoke script deletes only its own randomly named test graphs, leaving the app's fictional demo and unrelated graphs intact.

## Next phase

Add one model-backed, cited case-summary workflow behind the existing structured output verifier. Models remain unconfigured in Phase 1; the downloaded memory benchmarks are separate evaluation data and are not loaded into case graphs.
