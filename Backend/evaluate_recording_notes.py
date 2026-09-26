"""Real notes pipeline with operator transport or exact-request saved responses."""
import argparse,asyncio,copy,json,shlex,subprocess
from pathlib import Path
from memory_models import fingerprint
from memory_store import MemoryStore
from notes_generation import NotesGenerator
from recording_notes import RecordingNotes

class ReplayBudget:
    # Live operator transport owns durable admission; replay incurs no API spend.
    def reserve(self,*args):pass
    def finish(self,*args):pass

async def run(directory,transport=None,replay=None,case_ids=None):
    directory.mkdir(parents=True,exist_ok=False)
    cases=json.loads((Path(__file__).parent/'fixtures/recording-notes/cases.json').read_text())
    if case_ids:cases=[case for case in cases if case['id'] in case_ids]
    saved={fingerprint(r['request']):r for r in json.loads(replay.read_text())} if replay else {}
    process=None;calls=[];results=[]
    async def provider(req):
        nonlocal process
        key=fingerprint(req)
        if replay:
            if key not in saved:raise AssertionError('Exact replay request missing')
            entry=copy.deepcopy(saved[key]);entry['paid']=False
        else:
            if process is None:process=subprocess.Popen(shlex.split(transport),stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            process.stdin.write(json.dumps(req)+'\n');process.stdin.flush()
            line=await asyncio.to_thread(process.stdout.readline)
            if not line:raise RuntimeError('Provider transport ended')
            raw=json.loads(line)
            if 'error' in raw:raise RuntimeError(raw['error'])
            assert raw['request']==req
            response=raw['raw']
            entry=dict(request=req,raw=response,paid=True,reserved_microusd=raw['reserved_microusd'])
            calls.append(entry);(directory/'calls.json').write_text(json.dumps(calls,indent=2))
            if response.get('status')!='completed':raise RuntimeError('Notes response incomplete')
            text=''.join(c['text'] for o in response['output'] if o['type']=='message' for c in o['content'] if c['type']=='output_text')
            entry['response']=dict(data=json.loads(text),usage=response.get('usage',{}))
        if replay:calls.append(entry)
        (directory/'calls.json').write_text(json.dumps(calls,indent=2))
        return entry['response']
    try:
        store=MemoryStore(directory/'notes.sqlite');owner=store.owner_for('notes-qa');notes=RecordingNotes(store)
        generator=NotesGenerator(store,provider,ReplayBudget())
        for case in cases:
            source=case['source'];store.put_source(owner,source);notes.enqueue(owner,source['session_id'],1)
            await generator.generate(owner,source['session_id'])
            result=RecordingNotes(MemoryStore(store.path)).read(owner,source['session_id'])
            assert result['state']=='ready'
            output=json.dumps(result['notes']).lower()
            assert all(t.lower() in output for t in case['required']),case['id']
            assert all(t.lower() not in output for t in case['forbidden']),case['id']
            results.append(dict(case=case['id'],notes=result['notes']))
            (directory/'results.json').write_text(json.dumps(results,indent=2))
            assert not await generator.generate(owner,source['session_id'])
            print(json.dumps(dict(case=case['id'],state=result['state'])),flush=True)
    finally:
        if process:process.stdin.close();process.wait(timeout=10)
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--case',action='append')
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--transport');group.add_argument('--replay',type=Path)
    a=p.parse_args();asyncio.run(run(a.directory,a.transport,a.replay,a.case))
