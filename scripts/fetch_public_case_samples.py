"""Download a bounded, public Digital Corpora fictional training scenario."""
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import ProxyHandler,build_opener

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'cases'/'public'/'nitroba-2008'
BASE='https://digitalcorpora.s3.amazonaws.com/corpora/scenarios/2008-nitroba/'
FILES=[('scenario.txt',2416,None),('nitroba.pcap',56180821,'2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb'),
       ('screenshot.png',745820,None),('screenshot2.png',517612,None),('screenshot3.png',488066,None)]


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    opener=build_opener(ProxyHandler({}))
    records=[]
    previous={}
    if (DEST/'manifest.json').is_file():
        prior=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
        previous={row['file']:row for row in prior.get('files',[])}
    for name,size,expected in FILES:
        target=DEST/name
        url=BASE+name
        reuse_digest=expected or previous.get(name,{}).get('sha256')
        if target.is_file() and target.stat().st_size==size and reuse_digest and hashlib.sha256(target.read_bytes()).hexdigest()==reuse_digest:
            digest=hashlib.sha256(target.read_bytes()).hexdigest()
            records.append({**previous.get(name,{}),'file':name,'sourceUrl':url,'byteSize':size,'sha256':digest,'publisherSha256':expected})
            print('REUSE',name,size,flush=True)
            continue
        digest=hashlib.sha256();md5=hashlib.md5();count=0
        with opener.open(url,timeout=45) as response, target.with_suffix(target.suffix+'.part').open('wb') as output:
            etag=response.headers.get('ETag','').strip('"')
            modified=response.headers.get('Last-Modified')
            while chunk:=response.read(1024*1024):
                count+=len(chunk)
                if count>size:raise ValueError('Download exceeded the source listing size')
                digest.update(chunk);md5.update(chunk);output.write(chunk)
        value=digest.hexdigest()
        if count!=size or (expected and value!=expected) or (len(etag)==32 and md5.hexdigest()!=etag):
            raise ValueError('Size or source checksum mismatch for '+name)
        os.replace(target.with_suffix(target.suffix+'.part'),target)
        records.append({'file':name,'sourceUrl':url,'byteSize':count,'sha256':value,'publisherSha256':expected,'s3ETag':etag,'lastModified':modified})
        print('DOWNLOADED',name,count,'SHA256',value,flush=True)
    terms='https://digitalcorpora.org/about-digitalcorpora/terms-of-use/'
    with opener.open(terms,timeout=30) as response:
        raw=response.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Terms page exceeded source snapshot limit')
    (DEST/'upstream-terms.html').write_bytes(raw)
    manifest={'caseId':'PUBLIC-NITROBA-2008','title':'Nitroba 2008 · public fictional forensic training case',
              'downloadedAt':datetime.now(timezone.utc).isoformat(),'scenarioUrl':'https://digitalcorpora.org/corpora/scenarios/nitroba-university-harassment-scenario/',
              'termsUrl':terms,'reuse':'Original scenario content: CC0 unless separately copyrighted; see upstream terms. No claim that all embedded third-party material is CC0.',
              'purpose':'Local forensic software testing only; not real case evidence or model training.','files':records,
              'omitted':'Teacher solutions, disk images, executable corpora, and restricted answer keys were not downloaded.'}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('READY',sum(r['byteSize'] for r in records),'bytes',flush=True)


if __name__=='__main__':main()
