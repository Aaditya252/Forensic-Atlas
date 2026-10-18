# SUTRAM frontend API contract · v1

This contract lets the UI connect to a backend without changing page components. The current repository expects JSON over HTTPS (localhost is allowed for development) and a case scoped API.

## Runtime

Configure `runtime-config.js`:

```js
globalThis.SUTRAM_CONFIG = Object.freeze({
  dataMode: 'api',
  apiBaseUrl: 'https://forensics-api.example.test',
  apiTimeoutMs: 12000,
  caseId: 'DF-24-017'
});
```

If authentication is needed, the host app may inject:

```js
globalThis.SUTRAM_AUTH = {
  async getAccessToken() {
    return await acquireTokenFromYourIdentityProvider();
  }
};
```

The callback should return a short lived access token or `null`. Do not place secrets in `runtime-config.js`, browser storage, query strings, or logs. API requests include `Accept: application/json` and an `X-Request-Id`; writes also include `Idempotency-Key`.

## Read routes

### `GET /api/v1/cases/{caseId}/workspace`

Returns one compact case read model for first paint. The response may be wrapped in `{ "data": ... }`.

```json
{
  "schemaVersion": 1,
  "case": {
    "id": "DF-24-017",
    "title": "Northstar workspace access review",
    "status": "active_review",
    "description": "Case summary",
    "leadExaminer": "Examiner name",
    "openedAt": "2026-10-16T09:00:00Z",
    "authority": "Scope v3 · approved",
    "classification": "CONFIDENTIAL"
  },
  "overview": {
    "evidenceItems": 28,
    "evidenceAddedToday": 4,
    "coveragePercent": 92.4,
    "timelineEvents": 412,
    "eventsAddedToday": 38,
    "connectedSourceClasses": 6,
    "reviewQueueItems": 5,
    "reviewsDueToday": 2,
    "verifiedArtifacts": 28,
    "totalArtifacts": 28,
    "sourceClassesAvailable": 6,
    "sourceClassesExpected": 8,
    "acquisitionsComplete": 23,
    "acquisitionsExpected": 28,
    "openGaps": 2,
    "lastIntegrityCheck": "09:42 UTC"
  },
  "evidence": [
    {
      "id": "ART-028",
      "name": "auth-events-east.json",
      "type": "Cloud audit",
      "source": "Identity provider · tenant reference",
      "date": "Oct 18 · 09:42",
      "size": "4.2 MB",
      "status": "verified",
      "icon": "cloud"
    }
  ],
  "reviewItems": [
    {
      "id": "REV-003",
      "type": "AI claim · speaker attribution",
      "priority": "HIGH REVIEW",
      "title": "Attribution requires examiner review",
      "copy": "Reason the result is uncertain.",
      "evidence": "ART-025 · 00:14:22–00:14:31",
      "score": "74%"
    }
  ],
  "sourceCoverage": [
    {
      "id": "SRC-NETWORK",
      "name": "Network telemetry",
      "count": "3 / 4",
      "pct": 75,
      "icon": "timeline",
      "state": "1 source unavailable"
    }
  ],
  "events": [
    {
      "id": "EVT-442",
      "time": "09:42:18.204",
      "timestamp": "2026-10-18T09:42:18.204Z",
      "color": "",
      "title": "New sign-in session observed",
      "desc": "Source backed event description.",
      "source": "ART-028 · Identity audit"
    }
  ],
  "updatedAt": "2026-10-18T09:42:00Z"
}
```

The UI validates the schema version, case ID, overview object, and collection types before rendering. Use UTC ISO 8601 timestamps for machine values. Keep source supplied time and normalized time separately in the backend, and include precision and timezone interpretation in detailed event APIs.

### `GET /api/v1/cases/{caseId}/pages/{page}`

Supporting views load their read model only when opened. Valid page keys are `evidence`, `coverage`, `timeline`, `entities`, `media`, `deepfake`, `review`, `acquisitions`, `reports`, and `settings`. The UI keeps the result for 30 seconds and offers a refresh action. The response can use the same optional `{ "data": ... }` envelope:

```json
{
  "schemaVersion": 1,
  "title": "Evidence library",
  "summary": "Case scoped evidence records and processing status.",
  "sectionTitle": "Artifacts",
  "sectionDescription": "Originals and derived records are identified separately.",
  "metrics": [
    { "label": "Registered artifacts", "value": 28, "unit": "items", "foot": "Case scoped", "kind": "teal", "icon": "evidence" }
  ],
  "columns": [
    { "key": "id", "label": "Artifact ID" },
    { "key": "name", "label": "Name" },
    { "key": "status", "label": "Integrity status" }
  ],
  "rows": [
    { "id": "ART-028", "name": "auth-events-east.json", "status": "verified" }
  ],
  "updatedAt": "2026-10-18T09:42:00Z"
}
```

Metrics may be empty. `columns` and `rows` may be empty when there are no records. Return values as JSON primitives or compact objects; the UI renders object values as JSON text. The view is a tabular read model today, so graph and media backends can begin with evidence-linked node, edge, or run rows while dedicated visualizations are added later.

### `GET /api/v1/cases/{caseId}/search?q={query}&limit=8`

Returns `{ "data": { "items": [...] } }`. Each item has `id`, `label`, `detail`, and `route`; routes accepted by the UI are `evidence`, `review`, `timeline`, `overview`, `coverage`, `entities`, `media`, `deepfake`, `acquisitions`, `reports`, and `settings`.

### `GET /api/v1/cases/{caseId}/media-runs?profile=multimodal-screening&limit=50`

The Deepfake Lab reads case-scoped detector runs separately from the generic page table. Return `{ "data": { "items": [...] } }`. Each run includes `id`, `artifactId`, `status` (`queued`, `running`, `completed`, or `failed`), and `signals` (an array, empty when none were returned). Completed runs may include `summary`, `screeningScore` (0–1 triage score, not a probability of manipulation), `limitations` (string array), and `model` (`id` and `version`). Each signal may include `id`, `modality`, `kind`, `label`, `score`, `startMs`, `endMs`, `explanation`, and a derived-artifact reference. Keep every interval linked to a source artifact and a reproducible run record.

The notification panel should surface completed runs that contain review signals and link back to the selected artifact. A queued write is not a completed analysis or a user-facing manipulation finding. The service owns detector execution, scoring, status transitions, and notification delivery; the browser prototype does not run a model or poll for new results continuously.

### `POST /api/v1/cases/{caseId}/context/ask`

Requires `Idempotency-Key`. This is a deterministic, case-scoped graph retrieval aid; it does not call an LLM or make a forensic finding. Request: `{ "entityId": "ART-028", "question": "What entities connect to this record?", "depth": 2 }`. Depth is an integer from 1–3. Only a fixed parameterized FalkorDB path tool is callable; maximum 25 returned paths.

Success is `{ "data": { "agent", "question", "answer", "state", "sources", "statements", "paths", "gap", "trace", "verification" } }`. Each statement is `{ "text", "state", "sources" }`; state is `observed`, `derived`, `candidate`, `hypothesis`, or `unknown`, and each factual statement must cite source artifact IDs from this case. `gap` is null when a verified source-linked path is returned, otherwise it has `state: "unknown"` and a message that does not infer nonexistence. Disallowed identity, intent, motive, guilt, causation, and media-verdict requests return an explicit refusal and safe reframe. Parser, timestamp, transcript, speaker, and detector questions remain unsupported until their tools are configured.

If FalkorDB is unavailable, return `503 FALKORDB_UNAVAILABLE`; do not synthesize a path. Accepted queries are stored only as `episodic_unverified` in `/context/memory` and audited. They are never promoted to semantic facts without examiner review. Failed narration verification invokes the deterministic `evidence-path-agent`; if that fallback also fails, the endpoint returns an unknown gap.

## Write routes

All write routes are case scoped, accept JSON, require authorization checks in the backend, and should be idempotent using the request `Idempotency-Key` header.

| Method and path | Purpose | Expected body |
|---|---|---|
| `POST /api/v1/cases/{caseId}/reviews/{reviewId}/decision` | Record a human review decision | `{ "decision": "reviewed", "note": "optional" }` |
| `POST /api/v1/cases/{caseId}/acquisitions` | Queue an authorized source acquisition | `{ "sourceConnector", "fromUtc", "toUtc", "reason", "handling" }` |
| `POST /api/v1/cases/{caseId}/reports` | Create a report draft | `{ "title", "template", "scope" }` |
| `POST /api/v1/cases/{caseId}/media-runs` | Queue a derived media analysis | `{ "artifactId", "profile": "multimodal-screening", "modelRoute": "local-validated" }` |
| `POST /api/v1/cases/{caseId}/exports` | Prepare an authorized export package | `{ "contents", "format" }` |

Successful writes may return `{ "data": { "id": "...", "message": "..." } }` or HTTP 204. A write should only appear complete after the service accepts it. The UI does not transfer source evidence bytes; upload or cloud acquisition needs a separate authenticated, resumable transfer design.

## Error shape

Return a meaningful HTTP status with a stable code and a safe user facing message:

```json
{
  "error": {
    "code": "SCOPE_NOT_AUTHORIZED",
    "message": "The requested source is outside the approved case scope."
  }
}
```

Do not return source credentials, provider tokens, sensitive payload fragments, or stack traces in error bodies. The UI surfaces the service message and does not substitute demo data; use the `X-Request-Id` header value to correlate the failed request with service logs. The UI does not automatically retry writes.

## Data ownership boundaries

- The case service owns authorization, scope versions, audit events, retention, source connector secrets, and final status.
- Evidence storage owns immutable originals and derived object versions. The UI only displays references and digest status.
- A graph database should hold a rebuildable projection with source artifact references; it is not the authority for evidence bytes.
- Model services should return model/version, preprocessing, dataset scope, calibration, output, and limitations as provenance. A score is not a probability of guilt or identity by itself.
- Examiner decisions should be append only and include actor, timestamp, decision, note, evidence references, and prior state.

## Hybrid agent hub

`GET /api/v1/cases/{caseId}/agents/hub` returns the specialist roster, latest run, provider status, recent FalkorDB episodes, and handoffs. `POST /api/v1/cases/{caseId}/agents/hub/run` requires an `Idempotency-Key`; FalkorDB is required for a successful run. It writes a case-synthesis episode and creates bounded pending handoffs for enabled specialists. The current implementation is a deterministic tool/rule hybrid. The response states when LLM or validated media-detector providers are unavailable. Candidate cause/impact explanations include alternatives and never become findings automatically.

### Lightweight memory and handoffs

`GET /api/v1/cases/{caseId}/agents/memory?limit=20&agentId=case-orchestrator` reads case-scoped episodic memory from FalkorDB. Limits are 1–100. Episode states are `observed`, `derived`, `candidate`, `hypothesis`, or `unknown`; each episode keeps source IDs, payload, timestamp, and version. New writes do not use SQLite `agent_memory` as a memory store. SQLite remains the audit/idempotency store.

`GET /api/v1/cases/{caseId}/agents/handoffs?limit=20` returns graph-backed pending or acknowledged work items. `POST /api/v1/cases/{caseId}/agents/handoffs` requires `Idempotency-Key` and accepts `{ "fromAgent":"case-orchestrator", "toAgent":"timeline-correlation", "task":"Check source clock quality", "state":"hypothesis", "sourceIds":["ART-028"], "context":{} }`. The API checks each source against the case evidence list; state must be `candidate`, `hypothesis`, `unknown`, or `derived`. Creating a handoff does not execute or decide it.

The receiver acknowledges with `POST /api/v1/cases/{caseId}/agents/handoffs/{handoffId}/ack`, an `Idempotency-Key`, and `{ "expectedVersion": 1 }`. FalkorDB changes `pending` to `acknowledged` only if the supplied version matches; stale updates return `409 HANDOFF_VERSION_CONFLICT`. Graph writes use stable IDs derived from case and idempotency key, so retries do not create duplicate episodes/handoffs. This local build has case graph isolation but no authentication or tenant identity provider yet; it is not production tenant authorization.

`GET /api/v1/cases/{caseId}/agents/review-triage` returns fixed-rule review ordering. It uses visible review type/title metadata, ignores score/confidence, filters citations against case evidence, and never records an examiner decision.

`GET /api/v1/cases/{caseId}/agents/timeline-normalizer` returns conservative normalization for existing event rows: `{ "eventId", "sourceTime", "normalizedUtc", "precision", "offsetStatus", "state", "sources" }`. A missing timezone offset, invalid timestamp, or unsupported fractional precision returns `normalizedUtc: null` and `state: "unknown"`; the service never infers the workstation timezone. The Timeline page renders source time alongside normalized UTC and offset/precision fields.

`GET /api/v1/cases/{caseId}/agents/parser-coverage` computes counts only from an explicit optional `parserManifest` in the case read model. Without it, the response is `state: "unknown"` with a missing-manifest gap; the service does not extract numbers from review text. `GET /api/v1/cases/{caseId}/agents/transcript-attribution` consumes only optional structured `transcriptSegments` and returns existing speaker labels as `draftOnly: true`. Without source-linked segments it returns an unknown gap and no labels. A speaker label is never a person identity.
