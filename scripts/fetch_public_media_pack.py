"""Small public functional media pack; no authenticity/detector labels implied."""
import hashlib
import io
import json
import tarfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,ProxyHandler,build_opener

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'cases'/'public'/'media-functional-pack'
REV='4d21a042353022326071acb0251ab75cd6bae114'
opener=build_opener(ProxyHandler({}))


def fetch(url,limit):
    request=Request(url,headers={'User-Agent':'ForensicAtlas-local-functional-testing'})
    with opener.open(request,timeout=40) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Download exceeds the chosen pack limit')
    return data


def record(name,data,url,media_type,licence,attribution,**extra):
    (DEST/name).write_bytes(data)
    result={'file':name,'sourceUrl':url,'byteSize':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'mediaType':media_type,'reuse':licence,'attribution':attribution,**extra}
    print('SAVED',name,len(data),flush=True)
    return result


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    listing=json.loads(fetch('https://api.github.com/repos/mediaelement/mediaelement-files/contents?ref='+REV,1024*1024))
    wanted={'big_buck_bunny.mp4':'Video','big_buck_bunny.webm':'Video','big_buck_bunny.jpg':'Image'}
    records=[]
    for item in listing:
        if item['name'] not in wanted:continue
        data=fetch(item['download_url'],8*1024*1024)
        if len(data)!=item['size'] or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=item['sha']:
            raise ValueError('Pinned Git blob or size mismatch')
        records.append(record(item['name'],data,item['download_url'],wanted[item['name']],
            'CC BY 3.0 for Blender Peach movie content; https://peach.blender.org/about/',
            '(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org',upstreamRevision=REV,gitBlobSha1=item['sha'],
            purpose='Container, codec, image, metadata, and byte-intake functional tests; not a real/fake benchmark.'))
    if len(records)!=3:raise ValueError('Expected public video and poster files were not found')
    mirrors=['https://openslr.trmal.net/resources/1/waves_yesno.tar.gz','https://openslr.elda.org/resources/1/waves_yesno.tar.gz']
    archive=None;errors=[]
    for url in mirrors:
        try:archive=fetch(url,8*1024*1024);archive_url=url;break
        except Exception as exc:errors.append(type(exc).__name__)
    if archive is None:raise RuntimeError('Official speech mirrors unavailable: '+','.join(errors))
    (DEST/'waves_yesno.tar.gz').write_bytes(archive)
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as source:
        members=sorted((member for member in source.getmembers() if member.isfile() and member.name.endswith('.wav')),key=lambda member:member.name)
        if len(members)!=60:raise ValueError('Upstream speech archive count differs from the publisher page')
        for member in members[:3]:
            if member.size>2*1024*1024:raise ValueError('Speech sample exceeds the small pack bound')
            data=source.extractfile(member).read(member.size+1)
            if len(data)!=member.size:raise ValueError('Truncated archive member')
            name='yesno_'+Path(member.name).name
            records.append(record(name,data,archive_url,'Audio',
                'Publisher states no formal licence, free to use for any purpose; https://www.openslr.org/1/',
                'OpenSLR Yesno / anonymous Kaldi contributor',archiveMember=member.name,
                purpose='Real recorded speech for waveform/playback tests. Filename encodes yes/no words, not authenticity labels.'))
    manifest={'caseId':'PUBLIC-MEDIA-TESTS','title':'Public media functional test pack','downloadedAt':datetime.now(timezone.utc).isoformat(),
              'purpose':'Evaluate implemented software workflows, not detector accuracy or model training.',
              'files':records,'archive':{'file':'waves_yesno.tar.gz','sourceUrl':archive_url,'byteSize':len(archive),'sha256':hashlib.sha256(archive).hexdigest(),'memberCount':60,'selectedSamples':3},
              'sources':['https://github.com/mediaelement/mediaelement-files','https://peach.blender.org/about/','https://www.openslr.org/1/'],
              'detectorBenchmarks':[{'name':'FaceForensics++','url':'https://github.com/ondyari/FaceForensics','access':'Request/acceptance required; not downloaded'},
                {'name':'Celeb-DF','url':'https://github.com/yuezunli/celeb-deepfakeforensics','access':'Request/acceptance required; not downloaded'},
                {'name':'FakeAVCeleb','url':'https://github.com/DASH-Lab/FakeAVCeleb','access':'Request/acceptance required; not downloaded'},
                {'name':'WaveFake','url':'https://zenodo.org/records/5642694','access':'Open CC BY-SA 4.0; 28.9 GB generated-audio archive; catalogued, not downloaded'}]}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('READY',len(records),'selected files;',sum(row['byteSize'] for row in records),'selected bytes; archive',len(archive),'bytes',flush=True)


if __name__=='__main__':main()
