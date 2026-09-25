"""Administrative synthetic evaluation; one reserved, frozen batch, no retries.

Run on the hosted service against its existing ledger. Output is exclusively
synthetic fixture data. An exclusive output file prevents rerunning a named batch.
"""
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Backend'))
import httpx
from jev import Jev, Judgment, WAIT_SECONDS, VERSION, MODEL
from service_policy import open_ledger

async def main():
    fixture=Path(sys.argv[1])
    cases=json.loads(fixture.read_text())
    if not 1 <= len(cases) <= 48:raise ValueError('Batch too large')
    directory=Path(os.environ['VOICE_DATA_DIR'])
    destination=directory / ('jev-'+fixture.stem+'-v1.jsonl')
    os.umask(0o077)
    with destination.open('x') as output:
        store=open_ledger()
        owner,token=store.enroll(lifetime_seconds=300)
        reservation=None;completed=False
        try:
            reservation=store.reserve_evaluation(token,'jev',len(cases))
            print(json.dumps({'batch':fixture.name,'reservation':reservation,'max_calls':len(cases),'model':MODEL,'question_version':VERSION}),flush=True)
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY']},timeout=WAIT_SECONDS,follow_redirects=False,transport=httpx.AsyncHTTPTransport(retries=0)) as client:
                provider=Jev(client)
                for case in cases:
                    started=time.monotonic()
                    try:
                        async with asyncio.timeout(WAIT_SECONDS):
                            result=await provider.classify(case['question'])
                    except TimeoutError:result=Judgment(reason='timeout')
                    except Exception as error:
                        # Do not emit exception strings that can include request credentials.
                        result=Judgment(reason=type(error).__name__)
                    record={**case,**asdict(result),'seconds':time.monotonic()-started,'correct':result.route==case['expected']}
                    output.write(json.dumps(record)+'\n');output.flush();os.fsync(output.fileno())
                    print(json.dumps(record),flush=True)
                    if result.reason not in ('classified','mixed_uncertain','uncertain','timeout'):
                        raise RuntimeError('Provider error; stopped without retry')
            completed=True
        finally:
            if reservation:store.finish(reservation,completed=completed)
            store.revoke(owner);store.close()

if __name__=='__main__':asyncio.run(main())
