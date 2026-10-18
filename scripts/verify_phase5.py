"""Upload a labelled synthetic WAV and exercise the real metadata parser."""
import hashlib
import io
import json
import math
import struct
import uuid
import wave
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
base = 'http://127.0.0.1:8100/api/v1/cases/DF-24-017'
opener = build_opener(ProxyHandler({}))
checks = []
token = uuid.uuid4().hex
stream = io.BytesIO()
with wave.open(stream,'wb') as wav:
    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
    wav.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*440*i/16000))) for i in range(16000)))
audio = stream.getvalue()
ROOT.joinpath('output/phase5-synthetic-tone.wav').write_bytes(audio)


def call(path,body=None,key='inspect-'+token,content_type='application/json'):
    if isinstance(body,dict): body=json.dumps(body).encode()
    request=Request(base+path,data=body,headers={'Content-Type':content_type,'Idempotency-Key':key})
    try:
        with opener.open(request,timeout=45) as response:return response.status,json.load(response)
    except HTTPError as exc:return exc.code,json.load(exc)


def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    assert condition,name
    print('PASS',name,flush=True)


boundary='phase5'+token
parts=[]
for name,value in [('media_type','Audio'),('source_label','Clearly synthetic one-second 440 Hz tone generated for Phase 5 development verification')]:
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="phase5-synthetic-tone.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()+audio+b'\r\n')
parts.append(f'--{boundary}--\r\n'.encode())
code,uploaded=call('/artifacts',b''.join(parts),key='upload-'+token,content_type='multipart/form-data; boundary='+boundary)
check('synthetic WAV uploaded and digest registered',code==200 and uploaded['data']['sha256']==hashlib.sha256(audio).hexdigest())
artifact=uploaded['data']['id']; path='/artifacts/'+artifact+'/inspection'
code,result=call(path,{})
data=result.get('data',{})
check('real ffprobe metadata completes',code==200 and data.get('status')=='completed')
check('stored byte digest matches registration',data['integrityMatch'] and data['sha256']==uploaded['data']['sha256'])
check('real WAV properties returned',float(data['durationSeconds'])==1 and data['streams'][0]['sample_rate']=='16000' and data['streams'][0]['channels']==1)
check('no detector output fabricated',data['detectorRun'] is False and 'confidence' not in data)
check('inspection request replay is idempotent',call(path,{})==(code,result))
check('saved inspection can be read back',call(path)[1]['data']==data)
check('fixture without bytes returns explicit gap',call('/artifacts/ART-025/inspection')[0]==404)
check('caller cannot supply parser arguments',call(path,{'path':'elsewhere'},key='invalid-'+token)[0]==422)
_,page=call('/pages/media')
check('uploaded media appears in page selector data',any(row['artifact_id']==artifact for row in page['data']['storedArtifacts']))
ROOT.joinpath('output/phase5-verification.json').write_text(json.dumps({'status':'passed','checks':checks,'artifactId':artifact,'inspection':data,'fixture':'synthetic one-second 440 Hz mono WAV, 16 kHz, signed 16-bit PCM; not evidence'},indent=2),encoding='utf-8')
