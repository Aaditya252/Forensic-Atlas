# SUTRAM forensic case workspace

Standalone multi-page frontend for a digital forensics case workspace. The UI can run from a fictional local snapshot or read a versioned workspace response from a backend. It does not acquire evidence or run models itself.

## Run the connected local workspace

The dashboard now defaults to the local API at `http://127.0.0.1:8100`. Start the API with its fictional seed data:

```powershell
python -m backend.app --seed-demo
```

Open `http://127.0.0.1:8100/`. Every seeded record is fictional. Case decisions and request records persist in a local SQLite database.

## Deepfake Lab

Open **Deepfake lab** from the case sidebar to review image, audio, and video screening signals. Demo scores, alert examples, and frame spans are illustrative only; the prototype does not inspect media or run a detector. In API mode, it reads case artifacts and media runs, queues a run through `POST /api/v1/cases/{caseId}/media-runs`, refreshes run state while the page is open, and notifies the examiner when a completed run returns review signals. The backend contract describes the result shape.

Automatic screening on media intake is shown as the intended workflow. The case service still needs to implement the intake trigger, scope and hash checks, isolated model workers, evidence-linked result persistence, and notification delivery.

## Connect a backend

1. Implement the version 1 routes and response shape in [BACKEND_CONTRACT.md](./BACKEND_CONTRACT.md).
2. Edit `runtime-config.js`: set `dataMode` to `api`, set `apiBaseUrl`, and configure `caseId`.
3. Provide authentication through `globalThis.SUTRAM_AUTH.getAccessToken`. The frontend does not persist credentials.
4. Serve the frontend and API from an approved origin and configure CORS for that origin.

The API mode fails closed: if the service is unavailable or the response does not match the contract, the UI shows an error and does not replace API data with browser fixtures. See [the backend setup and current implementation limits](../backend/README.md).

## Structure

- `app.js` — page rendering, navigation, dialogs, search, and user interactions.
- `runtime-config.js` — deployment mode, API origin, timeout, and case selection.
- `src/config.js` — validated runtime configuration.
- `src/data/demo-workspace.js` — the fictional offline snapshot.
- `src/services/workspace-repository.js` — UI-facing read and write boundary, including the graph context agent.
- `src/services/api-client.js` — bounded HTTP requests, request IDs, bearer token injection, and normalized errors.
- `styles.css` — responsive design system and page components.
- `../backend/` — local API, SQLite persistence, audit trail, and FalkorDB graph tools.

## Safety and product limits

- Original evidence bytes, derived outputs, and analyst conclusions must remain distinct in the backend.
- A digest confirms byte consistency after capture; it does not prove where the bytes came from.
- AI and parser outputs are advisory and need examiner review.
- API mode sends requests only to the configured `apiBaseUrl`. It does not fall back to demo mode.
- This frontend is an integration shell, not a validated forensic tool or production security boundary.
