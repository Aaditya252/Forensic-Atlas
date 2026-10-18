# Phase 5: real media metadata and integrity inspection

## Implemented

The Media analysis page now offers **Media metadata & integrity** for uploaded Audio, Video, and Image evidence. It reads actual stored bytes, recomputes SHA-256, compares the registered digest, and uses the installed ffprobe executable to extract container, stream codecs, dimensions, duration, sample rate, and channel count when available. Saved inspection results persist in SQLite with an audit event and source artifact reference.

This is a deterministic metadata primitive. It is not a deepfake detector, authenticity verifier, face recogniser, or transcription model. Existing detector requests continue to fail closed without a validated provider.

## Use

1. Start `.\scripts\start_forensic_atlas.ps1` and open `http://127.0.0.1:8100/#media`.
2. Upload media through **Upload evidence**, choosing Audio, Video, or Image, then refresh the page.
3. Select an uploaded file and choose **Inspect file**.
4. **Load last inspection** retrieves the saved result without rerunning the parser.

Fixture filenames without uploaded bytes are not eligible for inspection. The pilot accepts WAV, MP4/MOV files with an `ftyp` header, Matroska/WebM, PNG, and JPEG signatures. Other formats return an explicit unsupported result.

The installed ffprobe was reused. No additional model, training dataset, or runtime download was needed.

## API and bounds

`POST /api/v1/cases/{caseId}/artifacts/{artifactId}/inspection` takes `{}` and requires `Idempotency-Key`. Parser paths and arguments cannot be supplied by the caller.

`GET` at the same URL returns the last saved result or null. An artifact with no uploaded byte record returns 404.

- Case-scoped stored file lookup and resolved path containment in that case's evidence directory.
- Streaming hashes, 512 MB file limit, and one active inspection per API process.
- Metadata parsing skipped on initial digest mismatch.
- Signature-selected demuxer, file-only protocol whitelist, 5 MB probe size, two-second analysis budget, and 12-second subprocess timeout.
- Disk-backed parser output; returned JSON limited to 128 KB and 16 streams.
- Post-parse hash comparison detects file changes and discards metadata when detected.
- Explicit missing dependency, unsupported signature, parser failure, and integrity-mismatch states; no substitute metadata or scores.
- Stable retry keys and atomic SQLite result/audit/idempotency commit.

The result records metadata as parser observations. Hash equality only means the checked bytes match registration; it does not establish source authenticity or chain of custody.

## Measured verification

45 unit tests passed, including five focused checks for mismatch blocking, playlist rejection, case-directory containment, missing ffprobe, and parser failure.

Ten live API checks passed using a **clearly labelled synthetic one-second 440 Hz mono WAV**, generated locally at 16 kHz with signed 16-bit PCM. The real parser returned `wav`, `pcm_s16le`, 1.000000 seconds, 16,000 Hz, and one channel. Upload and recomputed hashes matched. The fixture is development data, not evidence or training data.

Results: `output/phase5-verification.json`. Fixture: `output/phase5-synthetic-tone.wav`. Reproduce using `python scripts/verify_phase5.py`; it uploads a new labelled synthetic artifact to the fictional demo case.

## Remaining scope

The ffprobe subprocess has timeout/protocol/input/output bounds but is not isolated in a dedicated low-privilege container and has no operating-system memory cap. A single-process lock is not a distributed job queue. Historical inspection results do not imply that the file has remained unchanged since that inspection; run a new inspection to check current bytes. Integration of metadata into model context, detector evaluation, waveform decoding, transcription, and multimedia authenticity screening are later work.
