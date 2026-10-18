"""Exercise implemented workflows using the imported public media pack."""
import argparse
import hashlib
import json
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,ProxyHandler,build_opener

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pack', choices=['media-functional-pack','deepfake-audio'], default='media-functional-pack')
options=parser.parse_args()
pack=json.loads(ROOT.joinpath('cases/public',options.pack,'import-manifest.json').read_text(encoding='utf-8'))
case=pack['caseId'];base='http://127.0.0.1:8100/api/v1/cases/'+case
opener=build_opener(ProxyHandler({}));token=uuid.uuid4().hex;checks=[]


def call(path,body=None,key=None):
    headers={'Content-Type':'application/json','Idempotency-Key':key or token+'-'+path}
    request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    try:
        with opener.open(request,timeout=120) as response:
            raw=response.read()
            return response.status,json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw.decode(errors='replace')
    except HTTPError as exc:return exc.code,json.load(exc)


def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    assert condition,name
    print('PASS',name,flush=True)


audio=[row for row in pack['files'] if row['mediaType']=='Audio']
video=next((row for row in pack['files'] if row['mediaType']=='Video'),None)
context_sample=video or audio[0]
for sample in audio:
    code,response=call('/artifacts/'+sample['artifactId']+'/waveform')
    if options.pack=='deepfake-audio' and not sample.get('derivedFromFile'):
        check('original float WAV explicitly unsupported '+sample['file'],code==422)
        continue
    wave=response.get('data',{})
    check('measured audio waveform '+sample['file'],code==200 and wave['sampleRate']>0 and 0<wave['peakAmplitude']<=1 and len(wave['bins'])==256)
    check('waveform has measured speech variation '+sample['file'],len({round(row['rms'],4) for row in wave['bins']})>10)
if video:check('video is explicitly unsupported by PCM waveform endpoint',call('/artifacts/'+video['artifactId']+'/waveform')[0]==422)
for page in ['evidence','coverage','timeline','entities','media','deepfake','review','acquisitions','reports','settings','agents']:
    check('case read model '+page,call('/pages/'+page)[0]==200)
_,triage=call('/agents/review-triage')
check('empty review queue creates no suggestions',triage['data']['orderedItems']==[])
_,timeline=call('/agents/timeline-normalizer')
check('timeline does not invent events',timeline['data']['items']==[])
_,parser=call('/agents/parser-coverage')
check('missing parser manifest is explicit',parser['data']['state']=='unknown')
_,transcript=call('/agents/transcript-attribution')
check('no transcript or speaker identity fabricated',transcript['data']['speakerLabels']==[] and transcript['data']['state']=='unknown')
code,context=call('/context/ask',{'entityId':context_sample['artifactId'],'question':'What evidence-linked entities connect to this record?','depth':2})
check('graph returns an explicit gap for unlinked source',code==200 and context['data']['state']=='unknown' and context['data']['paths']==[])
code,handoff=call('/agents/handoffs',{'fromAgent':'case-orchestrator','toAgent':'case-memory','task':'PUBLIC TEST: confirm receipt; no case finding.','state':'derived','sourceIds':[audio[0]['artifactId']],'context':{'purpose':'Functional regression test'}})
check('source-linked handoff creates',code==200)
path='/agents/handoffs/'+handoff['data']['id']+'/ack'
code,receipt=call(path,{'expectedVersion':1})
check('handoff receipt persists',code==200 and receipt['data']['version']==2)
check('handoff replay is idempotent',call(path,{'expectedVersion':1})==(code,receipt))
check('stale handoff acknowledgement rejected',call(path,{'expectedVersion':1},key='stale-'+token)[0]==409)
code,detector=call('/media-runs',{'artifactId':context_sample['artifactId'],'profile':'multimodal-screening','modelRoute':'local-validated'})
check('unconfigured detector fails closed without scores',code==200 and detector['data']['status']=='failed' and detector['data'].get('signals',[])==[] and 'confidence' not in detector['data'])
code,summary=call('/summary',{})
check('real local model produces source-verified summary',code==200 and summary['data']['verification']['ok'])
result=summary['data']
check('media fact required in summary',any(row['origin']=='media-inspection' for row in result['statements']))
_,memory=call('/agents/recall?agentId=case-summary')
episode=memory['data']['items'][0]['id']
check('summary is recalled from graph memory',memory['data']['items'][0]['memoryKind']=='episodic_unverified')
code,report=call('/reports/from-summary',{'title':'Public media workflow validation report','summaryEpisodeId':episode})
check('report saves from public-media summary',code==200)
_,export=call('/reports/'+report['data']['id']+'/export/json')
digest=hashlib.sha256(json.dumps(export['report'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
check('report JSON integrity verifies',digest==export['contentSha256'])
code,html=call('/reports/'+report['data']['id']+'/export/html')
check('report HTML retains draft and provenance',code==200 and 'UNREVIEWED DRAFT' in html and result['model']['modelSha256'] in html)
check('another case artifact is not readable',call('/artifacts/ART-CEC59547/inspection')[0]==404)
ROOT.joinpath('output',options.pack+'-workflow-verification.json').write_text(json.dumps({'status':'passed','checks':checks,'caseId':case,'summaryId':result['summaryId'],'reportId':report['data']['id'],'modelElapsedMs':result['elapsedMs'],'model':result['model'],'notice':'Functional regression results only; no deepfake accuracy measurement or model training.'},indent=2),encoding='utf-8')
