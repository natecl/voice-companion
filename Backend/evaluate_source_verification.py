"""Bounded operator QA of candidate writer; exact-request replay, never paid retries.

Transport is an operator-supplied JSON-lines process that reserves calls before
sending them. This script never reads credentials or enables the hosted writer.
"""
import argparse
import asyncio
import copy
import json
from pathlib import Path
import shlex
import subprocess
from memory_models import fingerprint
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
import memory_source_verification as verifier

ROOT=Path(__file__).parent/'fixtures'

class Transport:
    def __init__(self, command, directory, replay_paths=()):
        self.command,self.directory=command,directory
        self.process=None
        recorded=json.loads((ROOT/'subject-continuity/calls.json').read_text())
        for path in replay_paths:
            recorded.extend(json.loads(path.read_text()))
        self.replay={fingerprint(c['request']):c['response'] for c in recorded}
        self.calls=[]
    async def call(self, request):
        cached=self.replay.get(fingerprint(request))
        if cached is not None:
            response=copy.deepcopy(cached); paid=False; raw=None
        else:
            if self.process is None:
                self.process=subprocess.Popen(shlex.split(self.command),stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            self.process.stdin.write(json.dumps(request)+'\n');self.process.stdin.flush()
            line=await asyncio.to_thread(self.process.stdout.readline)
            if not line:raise RuntimeError('Provider transport ended')
            raw=json.loads(line)
            if 'error' in raw:raise RuntimeError(raw['error'])
            assert raw['request']==request
            result=raw['raw']
            if request['model']==verifier.MODEL or request['model']=='gpt-6-luna':
                if result.get('status')!='completed':raise RuntimeError('Provider response incomplete')
                text=''.join(c['text'] for o in result['output'] if o['type']=='message' for c in o['content'] if c['type']=='output_text')
                response=dict(data=json.loads(text),usage=result.get('usage',{}))
            else:response=dict(data=result,usage=result.get('usage',{}))
            paid=True
        self.calls.append(dict(request=request,response=response,paid=paid,transport=raw))
        (self.directory/'calls.json').write_text(json.dumps(self.calls,indent=2))
        print(json.dumps(dict(call=len(self.calls),paid=paid,model=request['model'],role=request.get('text',{}).get('format',{}).get('name','metadata/lifecycle'))),flush=True)
        return response
    extract=call
    judge=call
    def close(self):
        if self.process is not None:
            self.process.stdin.close();self.process.wait(timeout=10)

class TransportBudget:
    # The remote transport atomically reserves before network access. Exact replay
    # has no cost; writer metering/cache still runs through its normal code path.
    def reserve(self,*args):pass
    def finish(self,*args):pass

async def run(directory,command,replay_paths=()):
    directory.mkdir(parents=True,exist_ok=False)
    models=Transport(command,directory,replay_paths);results=[]
    def save():
        (directory/'results.json').write_text(json.dumps(results,indent=2))
    try:
        store=MemoryStore(directory/'memory.sqlite');owner=store.owner_for('qa-independent-source')
        writer=EvidenceWriter(store,models,TransportBudget(),chunking=True,semantic_boundaries=True,
            expiry=True,consolidation=True,independent_source_verification=True)
        original=json.loads((ROOT/'subject-continuity/calls.json').read_text())
        for index in (0,3):
            source=json.loads(original[index]['request']['input']);source.pop('origin',None)
            store.put_source(owner,source);out=await writer.process_next(owner)
            rows=store.search(owner,historical=True);unresolved=store.search(owner,unresolved_only=True)
            results.append(dict(case=source['session_id'],result=out,rows=rows,unresolved=unresolved));save()
            assert not unresolved,'Supported recording has unresolved memories'
            assert any('morning' in r['text'] and r['state']=='active' for r in rows),'Preference retention failed'
            if index==0:assert len(rows)==2 and all(r['state']=='active' for r in rows),'Initial memory retention failed'
            else:
                old=[r for r in rows if 'library' in r['text'] and r['state']=='superseded']
                new=[r for r in rows if 'community center' in r['text'] and r['state']=='active']
                assert len(old)==len(new)==1 and old[0]['entity_id']==new[0]['entity_id'],'Correction failed'
        reopened=MemoryStore(directory/'memory.sqlite')
        assert store.search(owner,historical=True)==reopened.search(owner,historical=True)
        with store.connect() as db:assert not any(r[0] for r in db.execute('SELECT profile_link FROM claim'))
        cases=json.loads((ROOT/'source-verification/qa-cases.json').read_text())
        inputs={r['id']:dict(claim=r['claim'],passages=[dict(id=f'p{i+1}',text=t,speakers=[]) for i,t in enumerate(r['passages'])]) for r in cases}
        request,_=verifier.support_request(inputs)
        support=verifier.parse_support((await models.extract(request))['data'],inputs)
        for r in cases:
            assert (support[r['id']]['verdict']=='supported')==r['expected_support'],'Frozen support gate failed: '+r['id']
        # Keep each transcript separate for metadata. Unsupported claims already
        # fail admission; no extra paid metadata call adds necessary evidence.
        for r in cases:
            accepted=False;decisions=None
            if support[r['id']]['verdict']=='supported':
                source=dict(passages=inputs[r['id']]['passages'])
                p=dict(text=r['claim'],basis=r['basis'],time=dict(status=r['time'],expression=None))
                request=verifier.metadata_request(source,[p])
                decisions=verifier.metadata_decisions((await models.judge(request))['data'],request,[p])
                accepted=all(v['accepted'] for v in decisions.values())
            results.append(dict(case=r['id'],support=support[r['id']],metadata=decisions,accepted=accepted,expected=r['expected_admission']));save()
            assert accepted==r['expected_admission'],'Frozen admission gate failed: '+r['id']
        print(json.dumps(dict(composition_checks_passed=True,new_calls=sum(c['paid'] for c in models.calls))),flush=True)
    except BaseException as error:
        (directory/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,error=str(error))))
        raise
    finally:models.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--transport',required=True)
    parser.add_argument('--replay',type=Path,action='append',default=[])
    args=parser.parse_args();asyncio.run(run(args.directory,args.transport,args.replay))
