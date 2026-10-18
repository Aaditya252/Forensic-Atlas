"""Append small public test videos and speech samples without replacing existing files."""
import hashlib
import json
import tarfile
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'cases/public/media-functional-pack'
REV = '13024db581b08fae11a0ca229497198b9b0534e7'


def main():
    opener = build_opener(ProxyHandler({}))
    def fetch(url):
        with opener.open(url, timeout=45) as response:
            data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('Sample exceeds download size limit')
        return data
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    existing = {item['file'] for item in manifest['files']}
    tree = json.loads(fetch(f'https://api.github.com/repos/mdn/interactive-examples/git/trees/{REV}?recursive=1'))
    for item in tree['tree']:
        if item['path'] not in ['live-examples/media/cc0-videos/flower.mp4', 'live-examples/media/cc0-videos/flower.webm']:
            continue
        name = Path(item['path']).name
        if name in existing:
            continue
        url = f'https://raw.githubusercontent.com/mdn/interactive-examples/{REV}/' + item['path']
        data = fetch(url)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert len(data) == item['size'] and blob == item['sha'], 'Upstream blob mismatch'
        (DEST / name).write_bytes(data)
        manifest['files'].append({'file': name, 'sourceUrl': url, 'byteSize': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'gitBlobSha1': blob, 'upstreamRevision': REV,
            'mediaType': 'Video', 'reuse': 'CC0 1.0; publisher cc0-videos collection',
            'attribution': 'Mozilla MDN interactive examples / flower video',
            'purpose': 'Video playback and container inspection; no deepfake ground-truth label.'})
    with tarfile.open(DEST / 'waves_yesno.tar.gz', 'r:gz') as archive:
        members = sorted((m for m in archive.getmembers() if m.isfile() and m.name.endswith('.wav')), key=lambda m:m.name)
        for member in members[3:6]:
            name = 'yesno_' + Path(member.name).name
            if name in existing:
                continue
            assert member.size < 2_000_000
            data = archive.extractfile(member).read(member.size + 1)
            assert len(data) == member.size
            (DEST / name).write_bytes(data)
            manifest['files'].append({'file': name, 'sourceUrl': manifest['archive']['sourceUrl'],
                'byteSize': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mediaType': 'Audio',
                'archiveMember': member.name, 'attribution': 'OpenSLR Yesno / anonymous Kaldi contributor',
                'reuse': 'Publisher states no formal licence, free to use for any purpose; https://www.openslr.org/1/',
                'purpose': 'Natural recorded speech playback and waveform tests; no authenticity label.'})
    manifest['archive']['selectedSamples'] = 6
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (DEST / 'MDN-SOURCE.md').write_text(f'Mozilla MDN CC0 videos\n\nSource revision: {REV}\nhttps://github.com/mdn/interactive-examples/tree/{REV}/live-examples/media/cc0-videos\nLicense: https://creativecommons.org/publicdomain/zero/1.0/\nFiles are unchanged; hashes and blob IDs are in manifest.json.\n', encoding='utf-8')
    print('Pack contains', len(manifest['files']), 'files')


if __name__ == '__main__':
    main()
