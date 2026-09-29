"""Export candidate requests without changing runtime or making provider calls."""
import asyncio,json,sys
from pathlib import Path
from proactive_conversation_replay import run
ROOT=Path(__file__).resolve().parents[2]
from proactive_models import draft_request
async def prepare():
    result=await run()
    ids={'missing-prerequisite','new-useful-opening','acknowledged-after-cooldown'}
    return [dict(case=r['case'],request=draft_request(json.loads(r['request']['input']),grouped_messages=True),expected=r['expected_model_decision'])
            for r in result['requests'] if r['case'] in ids]
if __name__=='__main__':
    rows=asyncio.run(prepare())
    Path(sys.argv[1]).write_text(json.dumps(rows,indent=2))
    print(json.dumps(dict(cases=[r['case'] for r in rows],paid_calls=0,runtime_changed=False)))
