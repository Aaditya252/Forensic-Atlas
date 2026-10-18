"""Import verified public training files into a separate local case and test them."""
import hashlib
import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler,Request,build_opener

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import backend.app as api


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',choices=['nitroba-2008','media-functional-pack','deepfake-audio'],default='nitroba-2008')
    options=parser.parse_args()
    folder=ROOT/'cases'/'public'/options.pack
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    case_id=manifest['caseId']
    if case_id not in {'PUBLIC-NITROBA-2008','PUBLIC-MEDIA-TESTS','PUBLIC-DEEPFAKE-AUDIO'}:raise ValueError('Unexpected training case identifier')
    api.initialize()
    template=json.loads(api.DEMO_PATH.read_text(encoding='utf-8-sig'))
    template['case']={'id':case_id,'title':manifest['title'],'status':'public_training',
        'description':manifest.get('purpose','Public corpus used for local functional testing; no investigative conclusion has been established.'),
        'leadExaminer':'Local test operator','openedAt':api.now(),'authority':'Public educational corpus; see retained upstream reuse terms',
        'classification':'PUBLIC TRAINING','workspaceName':'Public training · Nitroba' if options.pack=='nitroba-2008' else manifest['title']}
    template['overview']={key:0 if isinstance(value,(int,float)) else 'Not recorded' for key,value in template['overview'].items()}
    for field in ('evidence','reviewItems','sourceCoverage','events'):template[field]=[]
    template['updatedAt']=api.now()
    with api.connect() as db:
        existing=db.execute('SELECT snapshot_json FROM cases WHERE case_id=?',(case_id,)).fetchone()
        if existing and json.loads(existing['snapshot_json']).get('case',{}).get('classification')!='PUBLIC TRAINING':
            raise ValueError('Existing case is not a public training case; no import performed')
        db.execute('INSERT OR IGNORE INTO cases VALUES(?,?,?,?)',(case_id,json.dumps(template),api.now(),api.now()))
    opener=build_opener(ProxyHandler({}));base='http://127.0.0.1:8100/api/v1/cases/'+case_id
    checks=[];imported=[]

    def call(path,body=None,key=None,content_type='application/json'):
        if isinstance(body,dict):body=json.dumps(body).encode()
        headers={'Content-Type':content_type}
        if key:headers['Idempotency-Key']=key
        request=Request(base+path,data=body,headers=headers)
        try:
            with opener.open(request,timeout=120) as response:
                raw=response.read()
                return response.status,json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
        except HTTPError as exc:return exc.code,json.load(exc)

    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        assert condition,name
        print('PASS',name,flush=True)

    for item in manifest['files']:
        data=(folder/item['file']).read_bytes()
        check('download hash '+item['file'],len(data)==item['byteSize'] and hashlib.sha256(data).hexdigest()==item['sha256'])
        media_type=item.get('mediaType') or ('Image' if item['file'].endswith('.png') else 'Log / export' if item['file'].endswith('.pcap') else 'Document')
        boundary='publiccase'+item['sha256'][:20]
        source='PUBLIC TRAINING / '+case_id+' / '+item['sourceUrl']
        payload=b''
        for name,value in [('media_type',media_type),('source_label',source)]:
            payload+=f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        payload+=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{item["file"]}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode()
        code,response=call('/artifacts',payload,'public-import-'+item['sha256'],'multipart/form-data; boundary='+boundary)
        check('registered intake '+item['file'],code==200 and response['data']['sha256']==item['sha256'])
        artifact=response['data']['id']
        code,stored=call('/artifacts/'+artifact+'/download')
        check('stored byte round-trip '+item['file'],code==200 and hashlib.sha256(stored).hexdigest()==item['sha256'])
        record={**item,'artifactId':artifact,'mediaType':media_type}
        if media_type in {'Image','Video','Audio'}:
            code,inspection=call('/artifacts/'+artifact+'/inspection',{},'public-inspect-'+item['sha256'])
            check('real media metadata '+item['file'],code==200 and inspection['data']['status']=='completed' and inspection['data']['integrityMatch'])
            record['inspection']=inspection['data']
        imported.append(record)
    _,workspace=call('/workspace')
    check('training case contains only imported artifacts',len(workspace['data']['evidence'])==len(imported) and not workspace['data']['reviewItems'])
    code,run=call('/agents/hub/run',{},'public-nitroba-hub-v1')
    check('agents consume public media inspections',code==200 and len(run['data']['mediaInspectionContext']['facts'])==3)
    report={'caseId':case_id,'status':'passed','files':imported,'checks':checks,'notice':'Public fictional training evidence; no authenticity, attribution, or network-investigation result was evaluated.'}
    (folder/'import-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    report_name='public-case-verification.json' if options.pack=='nitroba-2008' else options.pack+'-import-verification.json'
    ROOT.joinpath('output',report_name).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('OPEN http://127.0.0.1:8100/?case='+case_id+'#evidence',flush=True)


if __name__=='__main__':main()
