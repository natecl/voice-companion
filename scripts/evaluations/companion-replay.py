"""Current backend on the identical two sources, replaying exact saved provider calls."""
import asyncio,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'Backend'))
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter

async def main(out):
    out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]/'Backend/fixtures'
    calls=json.loads((root/'subject-continuity/calls.json').read_text());index=0
    sources=json.loads((root/'gbrain-comparison/sources.json').read_text());report=dict(scope='exact saved provider replay, no fresh model-quality claim',checks={})
    class Models:
        async def invoke(self,role,request):
            nonlocal index
            c=calls[index];index+=1
            assert (role,request)==(c['role'],c['request'])
            return copy.deepcopy(c['response'])
        async def extract(self,req):return await self.invoke('extract',req)
        async def judge(self,req):return await self.invoke('judge',req)
    class Budget:
        def reserve(self,*args):pass
        def finish(self,*args):pass
    store=MemoryStore(out/'memory.sqlite');owner=store.owner_for('comparison')
    writer=EvidenceWriter(store,Models(),Budget(),chunking=True,semantic_boundaries=True,expiry=True,consolidation=True)
    for source in sources:
        source.pop('origin',None);store.put_source(owner,source);await writer.process_next(owner)
    rows=store.search(owner,historical=True);report['before_delete']=rows
    report['checks']['correction_lifecycle']=sorted(r['state'] for r in rows)==['active','superseded'] and len({r['entity_id'] for r in rows})==1
    report['checks']['split_preference_retained']=any('morning' in r['text'] for r in rows)
    other=store.owner_for('other-user');report['checks']['owner_isolation']=store.search(other,historical=True)==[]
    store.delete_source(owner,sources[1]['session_id']);store=MemoryStore(out/'memory.sqlite')
    rows=store.search(owner,historical=True);report['after_delete']=rows
    report['checks']['deletion_and_reopen_remove_unsupported_correction']=not any('community center' in (r['text'] or '') for r in rows)
    with store.connect() as db:
        report['checks']['deleted_payload_and_support_removed']=db.execute('SELECT payload,deleted FROM source WHERE owner=? AND session=?',(owner,sources[1]['session_id'])).fetchone()['payload'] is None and db.execute('SELECT count(*) FROM support WHERE owner=? AND session=?',(owner,sources[1]['session_id'])).fetchone()[0]==0
    assert index==9
    report['replayed_calls']=index
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['checks']))

asyncio.run(main(Path(sys.argv[1])))
