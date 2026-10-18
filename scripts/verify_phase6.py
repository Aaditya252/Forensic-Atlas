"""Verify actual inspection → agent → local model → graph memory → report flow."""
import json
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler,Request,build_opener

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.graph_store import CaseGraph
base='http://127.0.0.1:8100/api/v1/cases/DF-24-017'
opener=build_opener(ProxyHandler({}))
token=uuid.uuid4().hex
checks=[]


def call(path,body=None,key='phase6-'+token):
    request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Idempotency-Key':key})
    try:
        with opener.open(request,timeout=120) as response:return response.status,json.load(response)
    except HTTPError as exc:return exc.code,json.load(exc)


def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    assert condition,name
    print('PASS',name,flush=True)


fixture=json.loads(ROOT.joinpath('output/phase5-verification.json').read_text(encoding='utf-8'))
artifact=fixture['artifactId']
code,run=call('/agents/hub/run',{})
check('coordinator reads persisted inspections',code==200 and artifact in run['data']['mediaInspectionContext']['sourceIds'])
check('media workstream is source linked',any(w['agentId']=='media-metadata' and artifact in w['sources'] for w in run['data']['workstreams']))
code,summary=call('/summary',{},key='summary-'+token)
check('real local model summary succeeds',code==200)
result=summary['data']
media=[row for row in result['statements'] if row['origin']=='media-inspection']
check('summary includes saved media observation',bool(media) and artifact in result['sources'])
check('inspection identifier and historical time retained',fixture['inspection']['id'] in media[0]['text'] and fixture['inspection']['createdAt'] in media[0]['text'])
check('bounded inspection tool trace retained',any(t['tool']=='media.read_saved_inspections' for t in result['inputContext']['trace']))
_,memory=call('/agents/memory?agentId=case-summary&limit=1')
episode=memory['data']['items'][0]
check('summary persisted in FalkorDB',episode['payload']['summaryId']==result['summaryId'])
graph=CaseGraph('DF-24-017')
links=graph.graph.query('MATCH (e:AgentEpisode {caseId:$caseId,id:$episode})-[:SUPPORTED_BY]->(a:CaseEntity {caseId:$caseId,id:$artifact}) RETURN count(a)',params={'caseId':'DF-24-017','episode':episode['id'],'artifact':artifact}).result_set
check('uploaded artifact has graph provenance edge',links[0][0]==1)
code,report=call('/reports/from-summary',{'title':'Phase 6 synthetic media context demonstration','summaryEpisodeId':episode['id']},key='report-'+token)
check('media-aware report snapshot saves',code==200)
_,export=call('/reports/'+report['data']['id']+'/export/json')
check('report preserves media statement exactly',media[0] in export['report']['statements'])
ROOT.joinpath('output/phase6-verification.json').write_text(json.dumps({'status':'passed','checks':checks,'artifactId':artifact,'summaryId':result['summaryId'],'reportId':report['data']['id'],'elapsedMs':result['elapsedMs'],'usage':result['usage'],'model':result['model']},indent=2),encoding='utf-8')
