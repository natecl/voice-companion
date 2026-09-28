"""Seed fictional histories into isolated stores; prepare bounded baseline/candidate requests.

No network or model invocation. Output supports a separately funded matched test.
"""
import json,tempfile
from pathlib import Path
from memory_store import MemoryStore
from proactive_context import prepare
from proactive_models import draft_request
from proactive_replay import recording
ROOT=Path(__file__).resolve().parents[2]
CASES=ROOT/'Backend/fixtures/proactive/personal-cases.json'

def seed_case(store,owner,case):
    store.put_source(owner,recording('prior',case['past']))
    for index,text in enumerate([
        'Alex enjoys hiking and prefers short trails on weekends.',
        'Jordan is preparing a presentation about telescope optics.',
        'Alex and Priya chose a blue cover for the Cedar project notebook.'
    ]):
        store.put_source(owner,recording(f'distractor-{index}',text))

def prepared_cases(cases_path=CASES):
    rows=[]
    for case in json.loads(cases_path.read_text()):
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite',clock=lambda:300.)
            owner=store.owner_for('fictional-personal-evaluation')
            seed_case(store,owner,case)
            context=prepare(store,owner,recording('capture',case['live'],completed=False))
            assert context and any(s['session_id']=='prior' for s in context['state']['sources']),case['id']
            request=dict(draft_request(context['state']),instructions=(ROOT/'Backend/prompts/proactive-v1.md').read_text()) if context else None
            candidate=dict(request,instructions=(ROOT/'Backend/prompts/proactive-v2.md').read_text()) if request else None
            rows.append(dict(case=case['id'],expected=case['expected'],rubric=case['rubric'],
                             source_count=len(context['state']['sources']) if context else 0,
                             baseline=request,candidate=candidate))
    return rows

if __name__=='__main__':
    import sys
    rows=prepared_cases()
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(rows,indent=2))
    print(json.dumps([dict(case=r['case'],expected=r['expected'],source_count=r['source_count']) for r in rows],indent=2))
