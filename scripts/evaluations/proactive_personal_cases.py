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

def prepared_cases():
    rows=[]
    for case in json.loads(CASES.read_text()):
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite',clock=lambda:300.)
            owner=store.owner_for('fictional-personal-evaluation')
            store.put_source(owner,recording('prior',case['past']))
            for index,text in enumerate([
                'Alex enjoys hiking and prefers short trails on weekends.',
                'Jordan is preparing a presentation about telescope optics.',
                'Alex and Priya chose a blue cover for the Cedar project notebook.'
            ]):
                store.put_source(owner,recording(f'distractor-{index}',text))
            context=prepare(store,owner,recording('capture',case['live'],completed=False))
            assert context and any(s['session_id']=='prior' for s in context['state']['sources']),case['id']
            request=draft_request(context['state']) if context else None
            candidate=dict(request,instructions=(ROOT/'Backend/prompts/proactive-v2-candidate.md').read_text()) if request else None
            rows.append(dict(case=case['id'],expected=case['expected'],rubric=case['rubric'],
                             source_count=len(context['state']['sources']) if context else 0,
                             baseline=request,candidate=candidate))
    return rows

if __name__=='__main__':
    import sys
    rows=prepared_cases()
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(rows,indent=2))
    print(json.dumps([dict(case=r['case'],expected=r['expected'],source_count=r['source_count']) for r in rows],indent=2))
