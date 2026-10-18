"""Fetch the official small AASIST-L research model with pinned source hashes."""
import hashlib
import json
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'a04c9863f63d44471dde8a6abcb3b082b07cd1d1'


def main():
    target = ROOT/'models/aasist-l'
    target.mkdir(parents=True, exist_ok=True)
    opener = build_opener(ProxyHandler({}))
    with opener.open(f'https://api.github.com/repos/clovaai/aasist/git/trees/{REVISION}?recursive=1',timeout=30) as response:
        tree = {item['path']:item for item in json.load(response)['tree']}
    records = []
    for source, name in [('models/AASIST.py','architecture.py'),('models/weights/AASIST-L.pth','weights.pth'),
                         ('config/AASIST-L.conf','config.json'),('LICENSE','LICENSE'),('NOTICE','NOTICE'),('README.md','UPSTREAM-README.md')]:
        url = f'https://raw.githubusercontent.com/clovaai/aasist/{REVISION}/{source}'
        with opener.open(url,timeout=45) as response:
            content = response.read(2_000_001)
        item = tree[source]
        assert len(content) <= 2_000_000 and len(content) == item['size']
        assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest() == item['sha']
        (target/name).write_bytes(content)
        records.append({'file':name,'sha256':hashlib.sha256(content).hexdigest(),'sourceUrl':url,'byteSize':len(content)})
    (target/'manifest.json').write_text(json.dumps({'model':'AASIST-L','revision':REVISION,'license':'MIT',
        'source':'https://github.com/clovaai/aasist','files':records,'sampleRate':16000,'windowSamples':64600,
        'scope':'Experimental audio anti-spoof screening only; no visual detection or local accuracy validation.',
        'classOrder':['spoof','bonafide'],'trainedByUs':False},indent=2),encoding='utf-8')
    print('Pinned official AASIST-L files downloaded; weights', (target/'weights.pth').stat().st_size,'bytes')


if __name__ == '__main__':
    main()
