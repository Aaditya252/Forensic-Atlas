# Phase 6: connect media observations to agents, memory, and reports

## Implemented flow

Saved media inspection in SQLite → bounded case-scoped reader → deterministic historical fact cards → case coordinator and constrained local model → source-linked FalkorDB episode → cited report snapshot.

The Agent Hub now includes **Saved media observations**, a media-metadata specialist in the roster, and a saved-inspection workstream in coordinated synthesis. The panel displays inspection IDs, record times, source artifact IDs, observations, and suggested next steps. Files with saved integrity discrepancies receive an explicit investigation step. Empty or unusable context remains an unknown gap.

## Bounds and trust

- The reader scans at most the latest 100 inspection rows for the selected case, retaining up to 20 distinct artifacts. The assessor returns up to three usable, source-linked observations.
- Source IDs must belong to the case. Inspection IDs, timestamps, status types, and container strings are validated before text is formed. Instruction-like container strings are rejected.
- Stored inspection output is labelled historical. No file is rehashed or reparsed during synthesis or summary generation.
- Fact cards say what a saved inspection recorded. They do not establish media authenticity or convert a parser observation into an examiner finding.
- When media observations exist, summary context reserves space for them within its 12-card budget. Structured model output must select a media observation alongside graph/review categories when those are present. Exact source wording and evidence states remain verified.
- The trace names the bounded inspection reader and lists selected inspection IDs. Reports preserve those trace entries and selected statements.

FalkorDB memory writes now merge an artifact reference when a cited uploaded artifact does not yet have a case graph node, then link the episode through `SUPPORTED_BY`. Existing nodes are preserved. Newly created reference nodes carry a derived registration/reference state; no semantic fact or authenticity claim is promoted.

## Use

1. Inspect uploaded media on the Media analysis page.
2. Open the Agent Hub and run **Run agents again** to refresh its inspection context.
3. Choose **Generate cited draft** to include available saved media context in the local-model summary.
4. On Reports, select the new summary to preserve it as a cited report snapshot.

No new model, training, embeddings, or service dependency was added. Deepfake detection remains unconfigured.

## Verification

- 51 unit tests passed, including six new media-context tests for historical citations, case/source filtering, malformed/instruction-like values, integrity-discrepancy guidance, empty context, bounded summary coverage, and rejection of selections that omit required media context.
- Ten live checks passed across the actual saved synthetic-WAV inspection, coordinator, local Qwen model, FalkorDB memory/provenance edge, and report export. The exported media statement matched the selected fact card exactly.
- Results and measured generation time: `output/phase6-verification.json`.

The fixture remains labelled synthetic development data. This is not a detector evaluation or a quality benchmark. Inspection-window limits can omit older records. Authentication, tenant authorisation, isolated parsing, and validated media detector models remain later work.
