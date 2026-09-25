"""Frozen eight-case comparison of direct and routed policies on the same Luna model.

Administrative hosted run, 8 Jev + 16 Luna calls maximum, reserved upfront.
Synthetic data only; exclusive persistent output prevents accidental reruns.
"""
import asyncio
from contextlib import aclosing
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Backend'))
import httpx
from ask import Luna, validate_request, references
from jev import Jev, Judgment, POLICIES, WAIT_SECONDS
from service_policy import open_ledger

async def main():
    cases=json.loads(Path('Fixtures/jev/answer-comparison.json').read_text())
    if len(cases)!=8:raise ValueError('Expected frozen eight-case comparison')
    os.umask(0o077)
    with (Path(os.environ['VOICE_DATA_DIR'])/'jev-answer-comparison-v2.jsonl').open('x') as output:
        store=open_ledger();owner,token=store.enroll(lifetime_seconds=600)
        reservations=[];completed=False
        try:
            reservations.append(store.reserve_evaluation(token,'jev',8))
            reservations.append(store.reserve_evaluation(token,'ask',16))
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY']},timeout=WAIT_SECONDS,follow_redirects=False,transport=httpx.AsyncHTTPTransport(retries=0)) as client:
                router=Jev(client);luna=Luna(os.environ['OPENAI_API_KEY'])
                for index,case in enumerate(cases):
                    data=validate_request(json.dumps({k:case[k] for k in ['question','passages']}))
                    # Alternate order to avoid always measuring the routed variant second.
                    for variant in (['direct','routed'] if index%2==0 else ['routed','direct']):
                        started=time.monotonic();policy='';judgment=Judgment(reason='disabled');text='';first=None;usage=None
                        async with asyncio.timeout(20):
                            if variant=='routed':
                                routing_start=time.monotonic()
                                try:
                                    async with asyncio.timeout(WAIT_SECONDS):judgment=await router.classify(data['question'])
                                except TimeoutError:judgment=Judgment(reason='timeout')
                                policy=POLICIES.get(judgment.route,'')
                                routing_seconds=time.monotonic()-routing_start
                            else:routing_seconds=0
                            async with aclosing(luna.stream(data,policy=policy)) as events:
                                async for event in events:
                                    if event['type']=='delta':
                                        if first is None:first=time.monotonic()-started
                                        text+=event['text']
                                    elif event['type']=='completed':usage=event
                        if not text.strip() or usage is None:raise ValueError('Incomplete answer; no retry')
                        record={'id':case['id'],'variant':variant,'review':case['review'],'text':text,'references':references(text,data['passages']),'first_text_seconds':first,'elapsed_seconds':time.monotonic()-started,'routing_seconds':routing_seconds,'judgment':asdict(judgment),'usage':usage}
                        output.write(json.dumps(record)+'\n');output.flush();os.fsync(output.fileno())
                        print(json.dumps(record),flush=True)
            completed=True
        finally:
            for reservation in reservations:store.finish(reservation,completed=completed)
            store.revoke(owner);store.close()
if __name__=='__main__':asyncio.run(main())
