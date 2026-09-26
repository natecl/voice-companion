"""Bounded provider QA for split subjects, correction lifecycle and relevant identity warnings."""
import argparse,asyncio,json,os,time
from pathlib import Path
from admission import Rejected
from memory_models import MemoryModels,LUNA,fingerprint
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from profile_budget import ProfileBudget
from companion_context import assemble
from ask import Luna,instructions,references
import memory_evidence


def source(name,texts):
    return dict(session_id=name,revision=1,captured_at=time.time(),timezone='UTC',completed=True,
        passages=[dict(id=f'p{i+1}',start=float(i*5),duration=3.,text=t,speakers=[] if i==0 else [0]) for i,t in enumerate(texts)])


async def run(directory,budget_path,replay_path=None):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,
        include_multisource_allowance=True,include_rollout_allowance=True)
    replay={} if replay_path is None else {fingerprint(c['request']):c for c in json.loads(replay_path.read_text())}
    reused=set()
    class Budget:
        count=0
        def reserve(self,key,model):
            if key.rsplit(':',1)[-1] in replay:
                reused.add(key);return
            if self.count>=16:raise Rejected('qa_call_cap')
            canonical.reserve(key,model);self.count+=1
        def finish(self,*args):
            if args[0] not in reused:canonical.finish(*args)
    budget=Budget();calls=[];results=[]
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    def record(role,method):
        async def invoke(req):
            cached=replay.get(fingerprint(req))
            if cached:assert cached['role']==role
            response=cached['response'] if cached else await method(req)
            calls.append(dict(role=role,request=req,response=response))
            (directory/'calls.json').write_text(json.dumps(calls,indent=2));return response
        return invoke
    models.extract=record('extract',models.extract);models.judge=record('judge',models.judge)
    store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('qa-subject-continuity')
    writer=EvidenceWriter(store,models,budget,chunking=True,semantic_boundaries=True,expiry=True,consolidation=True)
    first=source('split-subject',['Project Juniper.','Prefers morning meetings.','The meeting location is the library.'])
    if replay_path is not None:
        first=json.loads(next(c['request']['input'] for c in replay.values() if c['role']=='extract' and c['request'].get('text',{}).get('format',{}).get('name')=='memory_evidence_v2'))
        first.pop('origin',None)
    retention_complete=False
    correction=source('correction',['Project Juniper has changed its meeting location. It now meets at the community center instead of the library.'])
    try:
        for src in (first,correction):
            store.put_source(owner,src);out=await writer.process_next(owner)
            rows=store.search(owner,historical=True);unresolved=store.search(owner,unresolved_only=True)
            results.append(dict(case=src['session_id'],result=out,rows=rows,unresolved=unresolved))
            (directory/'results.json').write_text(json.dumps(results,indent=2))
            if src is first:
                retention_complete=not unresolved and len(rows)==2 and all(r['state']=='active' for r in rows)
                assert any('library' in r['text'].lower() and r['state']=='active' for r in rows),'No verified location for correction test'
            else:
                assert not unresolved,'Correction relation unresolved'
                old=[r for r in rows if 'library' in r['text'].lower() and r['state']=='superseded']
                new=[r for r in rows if 'community center' in r['text'].lower() and r['state']=='active']
                assert len(old)==len(new)==1 and old[0]['entity_id']==new[0]['entity_id'],'Correction lifecycle failed'
        # Extraction negatives must not assign a competing named subject or account identity.
        negatives=[('ambiguous',['Project Birch and Project Cedar.','One of them prefers evenings; I cannot remember which.']),
            ('quoted',['Project Birch was discussed earlier.','Someone else said, "I prefer evenings."'])]
        for name,texts in negatives:
            src=source(name,texts);req=memory_evidence.extraction_request(src);key=directory.name+':'+name
            budget.reserve(key,LUNA)
            try:res=await models.extract(req)
            except BaseException:budget.finish(key);raise
            budget.finish(key,res.get('usage'));proposals=memory_evidence.parse(res['data'],src)
            assert all(p['scope']=='unresolved' for p in proposals),'Ambiguous subject incorrectly named'
            results.append(dict(case=name,proposals=proposals));(directory/'results.json').write_text(json.dumps(results,indent=2))
        for name,texts,query in [
            ('neutral',['Project Juniper.','Prefers morning meetings.','The meeting location is the library.'],'What meeting preferences are recorded here?'),
            ('ownership',['I am an endurance runner.'],'Am I an endurance runner?'),
            ('other-subject',['Maya enjoys swimming.'],'What does Maya enjoy?')]:
            src=source('answer-'+name,texts);store.put_source(owner,src)
            data=assemble(store,owner,query,attachment=dict(session_id=src['session_id'],revision=1),use_memory=False)['data']
            key=directory.name+':answer:'+name;budget.reserve(key,LUNA);answer='';usage=None
            try:
                async for event in Luna(os.environ['OPENAI_API_KEY']).stream(data):
                    if event['type']=='delta':answer+=event['text']
                    if event['type']=='completed':usage=event
            finally:budget.finish(key,usage)
            results.append(dict(case=name,answer=answer,data=data,instructions=instructions(data)))
            (directory/'results.json').write_text(json.dumps(results,indent=2))
            assert references(answer,data['sources']),'Missing valid source reference'
            lower=answer.lower()
            if name=='ownership':assert any(w in lower for w in ('unidentified','not identified',"can't",'cannot','can’t','does not establish','doesn’t establish'))
            else:
                assert not any(w in lower for w in ('yours','your own','account owner','unidentified','not identified')),'Unsolicited ownership warning'
                assert ('morning' if name=='neutral' else 'swimming') in lower and '[[' in answer
        print(json.dumps(dict(lifecycle_and_answer_checks_passed=True,complete_split_subject_retention=retention_complete,calls=budget.count)),flush=True)
    except BaseException as error:
        (directory/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,error=str(error))))
        raise
    finally:
        print(json.dumps(dict(calls=budget.count,canonical=canonical.report())),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True);p.add_argument('--replay',type=Path);a=p.parse_args()
    asyncio.run(run(a.directory,a.budget,a.replay))
