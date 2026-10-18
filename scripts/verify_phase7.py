"""Read-only live checks of measured PCM waveform and audio range serving."""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,ProxyHandler,build_opener

ROOT=Path(__file__).resolve().parents[1]
fixture=json.loads(ROOT.joinpath('output/phase5-verification.json').read_text(encoding='utf-8'))
artifact=fixture['artifactId']
base='http://127.0.0.1:8100/api/v1/cases/DF-24-017/artifacts/'
opener=build_opener(ProxyHandler({}));checks=[]


def read(suffix,headers=None):
    try:
        with opener.open(Request(base+suffix,headers=headers or {}),timeout=45) as response:
            raw=response.read()
            return response.status,json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
    except HTTPError as exc:return exc.code,json.load(exc)


def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    assert condition,name
    print('PASS',name,flush=True)


code,body=read(artifact+'/waveform');data=body.get('data',{})
check('waveform uses registered source bytes',code==200 and data['sha256']==fixture['inspection']['sha256'])
check('sample dimensions measured correctly',data['sampleRate']==16000 and data['channels']==1 and data['durationSeconds']==1 and data['frameCount']==16000)
check('bounded envelope covers entire audio',len(data['bins'])==256 and data['bins'][0]['startSeconds']==0 and data['bins'][-1]['endSeconds']==1)
check('measured tone amplitude is correct',abs(data['peakAmplitude']-3000/32768)<0.00001 and data['fullScaleSampleCount']==0)
check('bins contain numeric sample ranges',all(-1<=b['min']<=b['max']<=1 and 0<=b['rms']<=1 for b in data['bins']))
check('no detector score fabricated',data['detectorRun'] is False and 'confidence' not in data)
code,audio=read(artifact+'/audio-preview')
check('original WAV preview served',code==200 and audio[:4]==b'RIFF' and len(audio)==fixture['inspection']['byteSize'])
code,partial=read(artifact+'/audio-preview',{'Range':'bytes=0-43'})
check('audio byte range supports seeking',code==206 and len(partial)==44)
check('fixture without bytes has no waveform',read('ART-025/waveform')[0]==404)
ROOT.joinpath('output/phase7-verification.json').write_text(json.dumps({'status':'passed','checks':checks,'artifactId':artifact,'peakAmplitude':data['peakAmplitude'],'rmsAmplitude':data['rmsAmplitude'],'binCount':len(data['bins']),'fixture':'labelled synthetic one-second tone; not evidence'},indent=2),encoding='utf-8')
