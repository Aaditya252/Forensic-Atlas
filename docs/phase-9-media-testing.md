# Public media and personal test intake

Open http://127.0.0.1:8100/?case=PUBLIC-MEDIA-TESTS#media.

The public media case now contains four video files (Big Buck Bunny and Mozilla MDN flower,
each in MP4/WebM), six Yesno speech recordings and one JPEG. These are functional samples,
not deepfake video benchmark labels. The separate PUBLIC-DEEPFAKE-AUDIO case retains three
publisher-labeled generated speech originals plus three labeled PCM derivatives.

Reproduce additions with `python scripts/extend_public_media_pack.py`, then
`python scripts/import_public_case_samples.py --pack media-functional-pack`.
The extension reads the retained Yesno archive and pins MDN revision
13024db581b08fae11a0ca229497198b9b0534e7, checking Git blob IDs and sizes.
Sources, reuse terms and SHA-256 digests are in the per-case manifests.

## Add your own files

The topbar **+ Add test files** button is available on every page; Media analysis also
offers the same control. Select up to 20 files (512 MB each, 1 GB per batch), keep extension
type detection or select a type, and record a source note. Files are uploaded sequentially
to the current case with per-file status. Optional inspection uses the existing bounded
metadata parser. Partial failures are shown per file; successful files are retained.
The file selection clears after completion to avoid accidental repeat submissions.

Other artifacts can be stored and hashed without a parser. File extensions select the
registry type only; parser and preview eligibility use actual signatures. No uploads train
the model or run an authenticity detector. Use a test case for test files.

## Playback

Media analysis has **Play / preview**. Deepfake lab now also plays the selected source
instead of its old preview placeholder. Native controls support playback and seeking;
the Deepfake lab ruler reads the source's actual duration. No simulated duration or
confidence trace is substituted. WAV waveform extraction remains a separate measured view.

The case-scoped `/artifacts/{id}/preview` route restricts paths to this case's evidence
directory, checks the registered SHA-256, and serves only allowed media signatures/MIME
types with nosniff and byte-range support. Browser codec support varies; unsupported
formats can still be stored/downloaded for external tools. Preview does not establish authenticity.

## Verification

64 Python unit tests pass, including preview path isolation, absent artifacts, byte-integrity
mismatch, HTML rejection and MP4 MIME selection. All 11 public files passed live preview
range/digest checks; all six speech recordings passed measured waveform checks.
Browser MP4 decoding returned 960x540, 5.055 seconds and no playback error. A two-file
video/audio upload through the new dialog stored both files and completed both inspections
in the fictional Northstar case, with an explicit UI-test provenance note.
