"""Live research screening checks; never interpret these as accuracy validation."""
import hashlib
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.request import Request, ProxyHandler, build_opener
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
API='http://127.0.0.1:8100'
opener=build_opener(ProxyHandler({}))
checks=[]
SILENT_NAME='silent-noaudio.mp4'


def request(case,artifact,body=None,key=None):
    url=f'{API}/api/v1/cases/{case}/artifacts/{artifact}/audio-screen'
    headers={'Content-Type':'application/json','Idempotency-Key':key or uuid.uuid4().hex}
    try:
        with opener.open(Request(url,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=120) as response:
            return response.status,json.load(response)
    except HTTPError as error:
        return error.code,json.load(error)


def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    print(('PASS' if condition else 'FAIL'),name,flush=True)
    return bool(condition)


def silent_fixture(case):
    """Generate a video with no audio stream and register it as a verification fixture.

    The public media pack no longer carries a silent clip. The fixture is uploaded through
    the normal intake route (digest recorded, audited) and reused whenever the bytes match,
    so repeat runs do not add duplicate artifacts to the case.
    """
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        return None
    fixture_dir=ROOT/'output/fixtures'
    fixture_dir.mkdir(parents=True,exist_ok=True)
    path=fixture_dir/SILENT_NAME
    if not path.exists():
        subprocess.run([ffmpeg,'-nostdin','-v','error','-f','lavfi','-i','color=c=gray:s=160x120:r=10:d=2',
                        '-an','-c:v','libx264','-pix_fmt','yuv420p','-y',str(path)],check=True,timeout=60,
                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with opener.open(f'{API}/api/v1/cases/{case}/workspace',timeout=30) as response:
        evidence=json.load(response)['data']['evidence']
    for item in evidence:
        if item.get('name')==SILENT_NAME and item.get('sha256')==digest:
            return item['id']
    boundary='----atlas'+uuid.uuid4().hex
    fields={'media_type':'Video','source_label':'Verification fixture: generated silent video, no audio track'}
    parts=[]
    for name,value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{SILENT_NAME}"\r\nContent-Type: video/mp4\r\n\r\n'.encode()+path.read_bytes()+b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    try:
        with opener.open(Request(f'{API}/api/v1/cases/{case}/artifacts',data=b''.join(parts),
                headers={'Content-Type':f'multipart/form-data; boundary={boundary}','Idempotency-Key':uuid.uuid4().hex}),timeout=120) as response:
            body=json.load(response)['data']
    except HTTPError as error:
        print('fixture upload failed:',error.code,error.read().decode()[:200],flush=True)
        return None
    if body.get('sha256')!=digest:
        print('fixture upload digest mismatch',flush=True)
        return None
    return body['id']


media=json.loads((ROOT/'cases/public/media-functional-pack/import-manifest.json').read_text())
synthetic=json.loads((ROOT/'cases/public/deepfake-audio/import-manifest.json').read_text())
video=next(f for f in media['files'] if f['file']=='big_buck_bunny.mp4')
speech=next(f for f in media['files'] if f['mediaType']=='Audio')
generated=synthetic['files'][0]
check('experimental acknowledgement required',request(media['caseId'],speech['artifactId'],{})[0]==422)
check('cross-case source unavailable',request(synthetic['caseId'],speech['artifactId'],{'acceptExperimental':True})[0]==404)
silent_id=silent_fixture(media['caseId'])
if silent_id:
    code,error=request(media['caseId'],silent_id,{'acceptExperimental':True})
    check('silent video does not get a fake verdict',code==422 and 'no audio' in str(error).lower())
else:
    check('silent video fixture could not be registered',False)
results=[]
for case,sample in [(media['caseId'],speech),(synthetic['caseId'],generated),(media['caseId'],video)]:
    key=uuid.uuid4().hex
    code,response=request(case,sample['artifactId'],{'acceptExperimental':True},key)
    check('real model execution '+sample['file'],code==200)
    data=response['data'];results.append(data)
    check('scope stays research audio-only '+sample['file'],data['validated'] is False and data['visualAnalysis'] is False and data['sha256']==sample['sha256'])
    check('measured waveform and windows '+sample['file'],len(data['bins'])==720 and len(data['segments'])>0)
    check('score bounds and time bounds '+sample['file'],all(0<=w['startSeconds']<w['endSeconds']<=data['durationSeconds']+.001 and (w['score'] is None or 0<=w['score']<=1) for w in data['segments']))
    check('idempotent result '+sample['file'],request(case,sample['artifactId'],{'acceptExperimental':True},key)==(code,response))
    check('latest result persists '+sample['file'],request(case,sample['artifactId'])[1]['data']['id']==data['id'])
    if data['durationSeconds']<3:
        check('short sample cannot get green or red claim',all(w['level'] in {'uncertain','unassessed'} for w in data['segments']))
(ROOT/'output/research-audio-screen-verification.json').write_text(json.dumps({'checks':checks,'results':results,
    'notice':'Functional execution checks only. Known natural speech was over-flagged; not accuracy validation.'},indent=2),encoding='utf-8')
