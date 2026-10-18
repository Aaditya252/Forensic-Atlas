# Phase 4: cited report snapshots and exports

## Workflow

Saved cited summary in FalkorDB → exact statement/context/citation checks → immutable report snapshot in SQLite → printable HTML and JSON exports.

Reports preserve the historical summary's wording and evidence states. The source register records artifact names, types, and SHA-256 values only when those values actually exist. Model metadata, the summary episode ID, summary time, context digest, and bounded tool trace accompany every report.

All generated reports carry **UNREVIEWED DRAFT**. No report approval, digital signature, evidence authenticity finding, or task completion is inferred.

## Use

1. Start `.\scripts\start_forensic_atlas.ps1` from the repository root.
2. Open `http://127.0.0.1:8100/#reports`.
3. Choose **Load saved summaries**, select a cited summary, and enter a report title.
4. Choose **Save report snapshot**.
5. Use **Open printable report** for the standalone HTML document or **Download JSON** for the content and digest. Browser Print → Save as PDF is available for the HTML; this phase does not add a server PDF renderer.

Existing metadata-only report requests remain visible in the Reports read model. They do not acquire exports automatically. Creating a report from a summary does not invoke the model or train anything.

## Data and API

`report_snapshots` stores the report ID, case ID, title, summary episode ID, complete detached JSON envelope, content digest, and creation time. There is no update or delete endpoint for snapshots.

- `POST /api/v1/cases/{caseId}/reports/from-summary`: `{title,summaryEpisodeId}`, with `Idempotency-Key`.
- `GET /api/v1/cases/{caseId}/reports/{reportId}`: saved envelope.
- `GET /api/v1/cases/{caseId}/reports/{reportId}/export/html`: standalone printable HTML.
- `GET /api/v1/cases/{caseId}/reports/{reportId}/export/json`: downloadable JSON envelope.

Creation reads the exact case-scoped episode from FalkorDB, compares selected statements against its saved fact cards, checks the context digest and current case source IDs, and reruns the citation/state verifier. SQLite stores the report, audit event, and idempotent response in one transaction. A conflicting retry returns 409. Later reads and exports need only SQLite; graph or model availability is not required.

Each export rechecks the stored content digest. The SHA-256 covers the `report` object serialized using sorted keys, UTF-8, `ensure_ascii=False`, and compact separators. It does not cover the HTML bytes and is not a signature or an independently trusted tamper-proof record. HTML escapes stored strings, contains no external assets or scripts, and sets a restrictive Content Security Policy.

## Verification

- 40 unit tests passed, including six report tests: detached snapshots, exact-content validation, cross-case rejection, HTML escaping, save/replay/offline export/integrity failure, and missing report handling.
- Nine live API checks passed for report creation, idempotency, conflicts, persistence, JSON hash verification, printable HTML content, unsupported format rejection, Reports-page listing, and missing reports.
- JavaScript and Python syntax checks passed.

Measured live results: `output/phase4-verification.json`. A real export from the fictional demo case is saved as `output/phase4-demo-report.html` and `output/phase4-demo-report.json`.

## Remaining scope

The report is a historical snapshot. Review needs or graph records may have changed since the source summary was created. Original evidence files are not embedded, and source authenticity is not validated. Examiner approval/signing, report templates beyond the cited summary, server PDF generation, and production identity/authorisation remain later work. The media detector is still unconfigured.
