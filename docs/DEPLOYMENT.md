# Full-system deployment

The current launcher and pinned llama.cpp binary target Windows x64. The full
stack needs FastAPI, persistent SQLite and originals, FalkorDB, Qwen, AASIST-L,
and ffmpeg/ffprobe. A static host only serves the presentation website.

## Closest match to the laptop

1. Prepare a persistent Windows x64 host with Docker Desktop Linux containers,
   Python 3.11+, Git, ffmpeg and ffprobe. Verify virtualization support first.
2. Follow the full setup commands in the root README.
3. Start the stack with `scripts/start_forensic_atlas.ps1`.
4. Run unit tests and `python scripts/deployment_preflight.py`.
5. With existing remote SSH access, forward the loopback API:

   ```text
   ssh -N -L 8100:127.0.0.1:8100 USER@HOST
   ```

   Browse `http://127.0.0.1:8100/` on the client. API calls, artifact previews
   and case links follow the forwarded endpoint using the frontend origin.

The launcher starts background processes, not Windows services. Configure and
test unattended startup, monitoring and recovery on the selected host. Creating
the repository does not complete a remote deployment.

## Preserve existing cases

A fresh clone contains the fictional demo only. Exact laptop parity requires
an explicit data migration as well as source deployment:

- Back up SQLite with its backup API; preserve originals and their hashes.
- Quiesce writes and use a consistent FalkorDB backup or graceful shutdown
  before copying persistence. Preserve every case graph, episode and handoff.
- Artifact paths are absolute. Preserve the root on Windows or perform a
  backed-up, verified path migration before serving cases.
- Recreate Docker bind mounts for the destination. Retain source data.
- Compare case IDs, artifact counts, SHA-256 values, report digests and graph
  counts; verify summary generation, previews and audio screening.
- Test restoration and retain the source system until verification succeeds.

## Public or Linux deployment

The API rejects non-loopback binding. Public access needs a reviewed
authentication and case-authorization boundary and data handling configuration.
Linux requires a compatible llama.cpp runtime and path migration; the pinned
Windows executable cannot run in a Linux container.

## Release checks

- Unit suite and target-host preflight pass.
- Qwen generates a cited summary from a target case.
- Upload, metadata inspection, waveform, audio screening and reports work.
- Case data and graph memory survive controlled service restarts.
- Backups restore at a separate test location.

Target access and hosting configuration must be available before reporting a
deployed URL or verified target behavior.
