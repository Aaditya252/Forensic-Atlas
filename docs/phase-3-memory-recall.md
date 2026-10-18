# Phase 3: persistent case-memory recall

## What this adds

The Agent Hub now has **Recall earlier work**. Examiners can search saved text, filter by agent or evidence source, and open an earlier episode's original statement list, evidence states, citations, context digest, and tool trace. The workflow reads persistent FalkorDB episodes, including the local model summaries from Phase 2. It requires no additional model, download, embedding index, or training.

## Retrieval contract

`GET /api/v1/cases/{caseId}/agents/recall?q=&agentId=&sourceId=&limit=10`

- Reads at most the newest 100 case episodes, or 100 episodes for the selected agent.
- Search accepts at most 160 characters and 12 terms. Every term must match the stored summary, answer/headline, question, source IDs, agent ID, or episode kind.
- Results use deterministic text overlap ordering, then existing recency order for ties. This is lexical retrieval, not semantic search. Overlap is not forensic confidence.
- Source filters must belong to the selected case. Episodes referencing unavailable sources are excluded.
- Returns up to 20 results, scanned/matched counts, window size, and a warning when the bounded window may omit older episodes.

`GET /api/v1/cases/{caseId}/agents/recall/{episodeId}`

- Uses a fixed, parameterized case-and-ID FalkorDB query. Direct lookup can inspect an episode outside the search window if its ID is known.
- Returns a bounded projection of saved output and provenance. Statement sources are checked against current case IDs. Stored strings remain untrusted and are escaped by the UI.
- Unknown episodes return 404; invalid filters return 422; graph unavailability returns an explicit 503. No fixture or fabricated result is substituted.

The existing `/agents/memory` API remains compatible. Recall does not write episodes, alter reviews, promote facts, or feed historical generated text into the summary model.

## Use

Start with `.\scripts\start_forensic_atlas.ps1` from the repository root, then open `http://127.0.0.1:8100/#agents`.

1. Scroll to **Recall earlier work**.
2. Search a topic or artifact ID, optionally selecting an agent and evidence source. Empty search text browses recent episodes.
3. Select **Inspect saved episode** to view the saved statements and expand **Saved tool trace and provenance**.

The UI has loading, empty, error, and stale-request handling, labelled form controls, keyboard-accessible inspection, theme variables, responsive layouts, and reduced-motion-aware scrolling.

## Verification

- All 28 unit tests passed, including six recall-specific checks for all-term search, case/source exclusion, bounds, untrusted query handling, state preservation, and parameterized case-scoped lookup.
- Ten read-only live API checks passed against the real FalkorDB service and previously generated fictional demo summaries. Results: `output/phase3-verification.json`.
- Dashboard and new module JavaScript syntax checks passed.

## Phase 3 continuation: handoff inbox

The Agent Hub also has an **Agent handoff inbox**. It initially shows the recent assignments returned by the hub; **Refresh handoffs** loads up to 100 assignments. Filter by pending or acknowledged status, expand **Inspect assignment and receipt**, check the task/context/source IDs and version, then choose **Acknowledge receipt**.

Acknowledgement is an operator-recorded receipt for the receiving specialist. It does not run an agent, mark the task complete, resolve evidence reviews, or approve a finding. No authenticated examiner identity is recorded by this local development UI.

Receipt state and timestamp persist in FalkorDB. SQLite retains the acknowledgement audit and idempotent response. A stale inspected version returns 409 and the UI requires refresh. A request key is scoped to acknowledgement operations, bound to the handoff ID and expected version, and retained for network-error retries. Reusing a key with another request returns 409. The local audit/cache commit is serialized to avoid duplicate audit entries on concurrent replay.

Continuation verification: 34 unit tests passed (six new receipt endpoint tests), and the live foundation verifier passed 26 checks, including acknowledgement/replay, stale-version rejection, graph persistence across API lifecycles, case isolation, and graph-outage handling. This continuation run did not restart Docker. `output/phase1-verification.json` contains the latest live result.

The browser receipt check acknowledged one fictional Northstar assignment, displayed its saved timestamp and version 2, and retained the source/evidence-state details. Screenshot: `output/phase3-handoff-inbox.png`.

## Remaining limits

This is a local development workflow. Graph separation enforces case selection in these tools; it does not provide organisational authentication or authorisation. Search intentionally covers a bounded recent window and does not yet provide embeddings, pagination, or full-history semantic retrieval. Historical output can be stale; the displayed episode is not a refreshed finding. No deepfake detector was enabled in this phase.
