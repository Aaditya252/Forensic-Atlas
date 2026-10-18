"""Source-scoped, deterministic reading of saved media inspections."""
import re

from backend.agent_prompts import verify_output


def assess_media_context(snapshot: dict) -> dict:
    known = {str(row['id']) for row in snapshot.get('evidence',[]) if isinstance(row,dict) and row.get('id')}
    records, seen, facts, items = snapshot.get('mediaInspections',[]), set(), [], []
    if not isinstance(records,list):
        records = []
    for record in records[:20]:
        if not isinstance(record,dict) or record.get('caseId') != snapshot.get('case',{}).get('id'):
            continue
        artifact, ident, stamp = record.get('artifactId'), record.get('id'), record.get('createdAt')
        if not isinstance(artifact,str) or artifact not in known or artifact in seen or not isinstance(ident,str) or not re.fullmatch(r'INS-[a-f0-9]{24}',ident):
            continue
        if not isinstance(stamp,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT[\d:.]+Z',stamp):
            continue
        seen.add(artifact)
        status = record.get('status')
        if not isinstance(status,str):
            continue
        if status == 'completed' and record.get('integrityMatch') is True:
            container = record.get('format')
            if not isinstance(container,str) or not re.fullmatch(r'[a-zA-Z0-9_,.-]{1,80}',container):
                continue
            text = f'Saved inspection {ident} at {stamp} recorded container {container} and a matching registered SHA-256 digest for {artifact}.'
            next_step = 'Inspect the original media and parser limitations; metadata does not establish authenticity.'
        elif record.get('integrityMatch') is False:
            text = f'Saved inspection {ident} at {stamp} recorded a byte-integrity discrepancy for {artifact}; parsed metadata was not retained.'
            next_step = 'Investigate the stored-byte discrepancy against intake records before further analysis.'
        elif status in {'unsupported','dependency_unavailable','failed'}:
            text = f'Saved inspection {ident} at {stamp} returned metadata status {status} for {artifact}; no completed metadata result was available in that inspection.'
            next_step = 'Review the saved parser error and supported file signatures before retrying inspection.'
        else:
            continue
        fact = {'text':text,'state':'derived','sources':[artifact],'origin':'media-inspection'}
        if not verify_output({'statements':[fact]},known)['ok']:
            continue
        facts.append(fact)
        items.append({'inspectionId':ident,'artifactId':artifact,'createdAt':stamp,'status':status,
                      'integrityMatch':record.get('integrityMatch'),'nextStep':next_step})
        if len(facts)>=3:
            break
    return {'agentId':'media-metadata','state':'derived' if facts else 'unknown','facts':facts,'items':items,
            'summary':f'{len(facts)} saved media inspection(s) are available as historical, source-linked context.' if facts else 'No usable saved media inspections were returned in the bounded read window.',
            'sourceIds':sorted({s for f in facts for s in f['sources']}),
            'limits':['Historical inspection records are not refreshed byte checks.','No authenticity or deepfake finding is inferred from metadata.']}
