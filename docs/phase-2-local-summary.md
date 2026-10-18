# Phase 2: local cited case summary

## Implemented workflow

Case snapshot (SQLite) → bounded entity/path retrieval (FalkorDB) → validated fact cards → local Qwen selection → exact statement and citation verification → unreviewed draft in FalkorDB → audit and idempotency record in SQLite → Agent Hub.

The model selects and orders existing fact IDs. It does not generate new evidence wording. Required category fields constrain selection to include a graph fact and unresolved review fact when available. The remaining fields choose additional fact IDs. Rendering preserves each selected statement's text, evidence state, source IDs, and origin.

The deterministic coordinator remains available as a separate action. Its run records mark the LLM as `not-invoked`. The hub reports current model readiness independently of older saved run records.

## Local components

| Component | Choice |
| --- | --- |
| Model | Qwen3.5-2B, Q4_K_M GGUF, approximately 1.28 GB |
| Conversion | unsloth/Qwen3.5-2B-GGUF, pinned revision in manifest |
| Runtime | Official llama.cpp b11718 Windows CPU binary |
| Inference | Four CPU threads, one slot, 4,096 context tokens, no GPU requirement |
| Model endpoint | http://127.0.0.1:8111/v1 |
| Application | http://127.0.0.1:8100/#agents |
| Training | None; existing evaluation datasets are not used for training |

Both downloaded archives/weights have pinned SHA-256 digests. Sources, revision, license, and paths are recorded in `models/phase2/manifest.json`. The runtime and model licenses are stored beside the downloads.

## Run

From the repository root in PowerShell:

```powershell
# Only needed when the model/runtime have not been downloaded:
python scripts/setup_phase2_model.py

# Starts/reuses FalkorDB, model server, and API:
.\scripts\start_forensic_atlas.ps1
```

Open the Agent Hub and choose **Generate cited draft**. A retained draft remains readable when the model is unavailable, provided FalkorDB is available. Logs and process IDs are in `output/`.

`GET /api/v1/cases/{caseId}/summary` reads the latest graph-backed draft and model status.

`POST /api/v1/cases/{caseId}/summary` accepts `{}` or an optional `entityId`. It requires an `Idempotency-Key`. Replaying a completed key returns the saved result; changing its body returns 409. A process-level lock allows one summary at a time (429 for another active request). Model calls are bounded to 45 seconds each, with at most two selection attempts. A failed verification does not substitute a fabricated draft.

## Verification completed

- 22 unit tests passed, including four focused summary tests.
- Seven live API checks passed using the fictional demo case and the actual local model: generation, required fact coverage, model provenance, idempotency, conflicting request rejection, FalkorDB persistence, and exact context statement preservation.
- The standalone model smoke run completed in 7.6 seconds. This is a single measured local run, not a performance guarantee.
- JavaScript syntax checks passed for the dashboard and API client.

See `output/phase2-verification.json` and `output/phase2-model-smoke.json` for measured results.

## Boundaries and next phase

This feature summarizes case metadata and source-linked graph statements. It does not examine original evidence bytes, validate the accuracy of graph records, decide authenticity, identify people, or establish causation. Drafts require examiner review. The media detector remains unconfigured.

This remains a local development service. The in-process summary lock assumes one API worker; multi-worker deployments need a shared job queue/lease. Graph and SQLite writes are not a distributed transaction; deterministic IDs and graph recovery cover retries, but recovery currently searches the latest 100 summary episodes. Evaluation on the downloaded memory datasets, production access controls, model quality benchmarking, and validated media detection are later phases.
