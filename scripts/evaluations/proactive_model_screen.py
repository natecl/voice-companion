"""Three frozen matched cases; max nine explicit calls, no automatic paid retries."""
import json,subprocess,sys,tempfile
from pathlib import Path
from memory_store import MemoryStore
from proactive_context import prepare
from proactive_models import draft_request,judge_request,parse_draft,allow_draft
from proactive_replay import recording

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok='--resume-cached' in sys.argv)
cases=json.loads(Path('Backend/fixtures/proactive/cases.json').read_text())[:3]
results=[]
for case in cases:
    with tempfile.TemporaryDirectory() as folder:
        store=MemoryStore(Path(folder)/'memory.sqlite',clock=lambda:300.)
        owner=store.owner_for('model-screen')
        store.put_source(owner,recording('prior',case['past']))
        live=recording('capture',case['live'],completed=False)
        context=prepare(store,owner,live)
        state=context['state'] if context else None
    for route in ('llm','jev'):
        row=dict(case=case['id'],route=route,expected=case['expected'],rubric=case['rubric'],state=state,calls=[])
        results.append(row)
        if state is None:
            row.update(decision='silence',reason='no_local_evidence')
            (out/'results.json').write_text(json.dumps(results,indent=2))
            print(case['id'],route,'silence (local evidence absent)',flush=True);continue
        def call(kind,req):
            payload=dict(id=f"{case['id']}:{route}:{kind}",request=req)
            process=subprocess.run(['ssh','-i','/Users/n.chinlue/.ssh/voice_companion_render',
                '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10',
                'srv-daqtfs7lot8c73dleuug@ssh.virginia.render.com','python3 /tmp/proactive-provider-20260928.py'],
                input=json.dumps(payload)+'\n',text=True,capture_output=True,timeout=35)
            if process.returncode:raise RuntimeError('Operator transport failed; no retry')
            saved=json.loads(process.stdout);row['calls'].append(saved)
            (out/'results.json').write_text(json.dumps(results,indent=2))
            if 'error' in saved:raise RuntimeError('Provider attempt failed: '+saved['error']+'; no retry')
            assert saved['request']==req
            return saved['raw']
        if route=='jev':
            req=judge_request(state);raw=call('judge',req)
            if not allow_draft(raw,req):
                row['decision']='silence';(out/'results.json').write_text(json.dumps(results,indent=2))
                print(case['id'],route,'silence',flush=True);continue
        raw=call('draft',draft_request(state))
        assert raw.get('status')=='completed','Incomplete response; no retry'
        text=''.join(c['text'] for o in raw['output'] if o['type']=='message' for c in o['content'] if c['type']=='output_text')
        row.update(parse_draft(json.loads(text),state))
        (out/'results.json').write_text(json.dumps(results,indent=2))
        print(case['id'],route,row['decision'],flush=True)
