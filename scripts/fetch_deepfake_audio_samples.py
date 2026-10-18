"""Fetch a bounded, revision-pinned selection of publisher audio examples."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'cases/public/deepfake-audio'
REVISION = 'eaed30201667c33bc7e15cfb3a3af95d13feaec6'
REPO = 'gan-police/audiodeepfake-detection'


def main():
    opener = build_opener(ProxyHandler({}))

    def fetch(url, limit=2_000_000):
        with opener.open(url, timeout=45) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Download exceeded the sample size limit')
        return data

    tree = json.loads(fetch(f'https://api.github.com/repos/{REPO}/git/trees/{REVISION}?recursive=1'))
    DEST.mkdir(parents=True, exist_ok=True)
    base = f'https://raw.githubusercontent.com/{REPO}/{REVISION}/'
    for name in ('LICENSE', 'README.md', 'CITATION.bib'):
        (DEST / ('UPSTREAM-' + name)).write_bytes(fetch(base + name))
    # These are classification examples, not the amplified fingerprint demonstrations.
    selected = [entry for entry in tree['tree'] if entry['path'].startswith('audio-samples/classification_examples/') and entry['path'].endswith('.wav')][:3]
    records = []
    for entry in selected:
        data = fetch(base + entry['path'])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != entry['size'] or blob != entry['sha']:
            raise ValueError('Upstream Git blob verification failed')
        name = Path(entry['path']).name
        (DEST / name).write_bytes(data)
        records.append({'file': name, 'sourceUrl': base + entry['path'], 'byteSize': len(data),
                        'sha256': hashlib.sha256(data).hexdigest(), 'gitBlobSha1': blob,
                        'mediaType': 'Audio', 'upstreamRevision': REVISION,
                        'publisherLabel': 'generated speech',
                        'generator': 'multi-band MelGAN' if name.startswith('D_') else 'MelGAN',
                        'reuse': 'Repository EUPL-1.2; underlying WaveFake CC BY-SA 4.0; retain both notices',
                        'purpose': 'Publisher-labeled synthetic audio example; not a local detector finding or accuracy benchmark.'})
    originals = list(records)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('ffmpeg is required to create documented PCM playback derivatives')
    for item in originals:
        name = Path(item['file']).stem + '_pcm16.wav'
        subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-y', '-i', str(DEST / item['file']), '-c:a', 'pcm_s16le', str(DEST / name)], check=True, timeout=20)
        data = (DEST / name).read_bytes()
        records.append({**item, 'file': name, 'byteSize': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                        'gitBlobSha1': None, 'derivedFromFile': item['file'], 'derivedFromSha256': item['sha256'],
                        'transformation': 'ffmpeg decode float PCM WAV to signed 16-bit PCM WAV; original retained unchanged',
                        'purpose': 'Locally converted playback/waveform derivative, not original publisher bytes.'})
    manifest = {'caseId': 'PUBLIC-DEEPFAKE-AUDIO', 'title': 'Generated speech research samples',
                'purpose': 'Exercise intake, integrity, speech playback, waveform, metadata, agents and reports with published generated speech. No validated detector is installed.',
                'sourceRepository': f'https://github.com/{REPO}',
                'underlyingDataset': 'https://zenodo.org/records/5642694', 'files': records}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (DEST / 'README.md').write_text('''# Generated speech research samples

Three unchanged classification audio examples and three explicitly labeled PCM derivatives from Konstantin Gasenzer and Moritz Wolter,
*Towards generalizing deep-audio fake detection networks*. Repository revision and blob hashes
are retained in manifest.json. The upstream repository is EUPL-1.2; retain UPSTREAM-LICENSE,
UPSTREAM-README.md and UPSTREAM-CITATION.bib. These MelGAN examples derive from WaveFake
(CC BY-SA 4.0, https://zenodo.org/records/5642694), using LJSpeech source material.
CC BY-SA terms: https://creativecommons.org/licenses/by-sa/4.0/.

These are short generated speech excerpts, not amplified generator-fingerprint sound effects.
Labels are supplied by the publisher's example organization and generator filenames.
They do not establish a result from Forensic Atlas. No accuracy estimate can be made from
three generated-only clips. Compare functional playback with PUBLIC-MEDIA-TESTS speech;
those recordings are a different speaker/language and are not a controlled detection benchmark.

Expected: all six hashes match; metadata succeeds for all files. Original float WAV
waveform requests return unsupported; signed 16-bit derivatives support measured waveforms;
agents cite saved metadata; a detection request fails closed until a validated detector is installed.
Do not use these clips for identity attribution or as investigative case evidence.
''', encoding='utf-8')
    print('Downloaded', len(records), 'original/derived audio files;', sum(x['byteSize'] for x in records), 'bytes')


if __name__ == '__main__':
    main()
