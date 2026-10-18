# Case library and test guide

Open http://127.0.0.1:8100/cases.html after starting Forensic Atlas.
`index.json` lists the four local cases. Each imported collection has its source manifest,
SHA-256 digests, retained reuse terms and an import manifest with artifact IDs.

| Case | Material | What to exercise |
| --- | --- | --- |
| DF-24-017 | Fictional Northstar fixture | Graph pivots, timeline, review, agent handoffs and memory |
| PUBLIC-NITROBA-2008 | DigitalCorpora scenario, PCAP, three screenshots | Evidence intake, hashes, source context and image metadata |
| PUBLIC-MEDIA-TESTS | Four video files (MP4/WebM), JPEG, six natural-speech WAV files | Video/audio metadata, measured speech waveform, playback, agents and reports |
| PUBLIC-DEEPFAKE-AUDIO | Three publisher generated-speech WAVs and three PCM derivatives | Preserved originals, explicit derivation, waveform, metadata, case isolation, summaries and report exports |

## Suggested walkthrough

1. Open evidence and compare filename, source URL and SHA-256 against the case manifest.
2. Inspect a video, image or audio file. Confirm codecs/duration and saved inspection source IDs.
3. In media analysis choose a speech WAV. For generated speech choose a `_pcm16.wav` file.
   Hover the measured waveform, scrub time and use native audio playback. Original generated
   float WAVs intentionally return unsupported from the bounded PCM waveform endpoint.
4. Run the hybrid agent hub. Inspect metadata context and coverage gaps.
5. Generate a local summary and open its evidence citations. Recall its saved episode.
6. Send a source-linked handoff and acknowledge its receipt. This does not execute a task.
7. Create a cited draft report; download JSON or print HTML and check provenance/digest.
8. Request a media detector run: expect a failed/unconfigured result with no invented scores.
9. Open another case and confirm sources are isolated. Public media packs have no invented
   timeline events, examiner review decisions or person identities.

## Deepfake video datasets requiring access

These official sources provide relevant benchmarks, but no access forms or agreements were
submitted. No restricted clips have been copied from mirrors:

- FaceForensics++: https://github.com/ondyari/FaceForensics/tree/master/dataset
- Celeb-DF: https://github.com/yuezunli/celeb-deepfakeforensics
- FakeAVCeleb (paired synthetic video/audio): https://github.com/DASH-Lab/FakeAVCeleb

The downloaded Big Buck Bunny files are animation and container tests, not deepfake video
ground truth. Three short generated speech examples cannot validate detection accuracy.
Memory evaluation corpora remain separately under datasets/evaluation with their own licenses.

## Storage and provenance

`public/` holds source downloads; `storage/evidence/` holds separately registered originals.
This intentional second copy distinguishes download provenance from application intake.
PCM conversions are labeled derivatives with original SHA-256 and conversion command recorded.
`storage/sutram.sqlite3` is the case record store; `graph-data/` holds its derived graph/memory
projection. `backups/` preserves the migration checkpoint. Do not edit original bytes in place.

Use the topbar **+ Add test files** to test your own files in the current case. See docs/phase-9-media-testing.md for limits and playback details.
