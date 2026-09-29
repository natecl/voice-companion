"""Six fresh fictional baseline cases, prepared through real retrieval; no model calls."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Backend'))
from memory_store import MemoryStore
from proactive_context import prepare
from proactive_models import draft_request
from proactive_replay import recording

CASES=[
 dict(id='study-time-conflict',expected='contribute',
      past='The chemistry study group moved its library session from 3 PM to 5 PM because the room is unavailable before 5.',
      live='For the chemistry study group, I am telling everyone to meet in the library at 3 PM.',
      rubric='Correct the planned time to 5 PM and explain room availability; no invented personal agreement.'),
 dict(id='study-time-resolved',expected='silence',
      past='The chemistry study group moved its library session from 3 PM to 5 PM because the room is unavailable before 5.',
      live='The chemistry study group is meeting in the library at 5 PM, not 3. The room is unavailable before 5. Everyone has the updated time.',
      rubric='Do not repeat the resolved time change or add a generic follow-up.'),
 dict(id='pickup-requirement',expected='contribute',
      past='For the community pottery pickup, the studio requires the original claim ticket. A photo of the ticket is not accepted.',
      live='I am heading to the community pottery studio for pickup. I only have a photo of the claim ticket, so I should be ready.',
      rubric='Flag that the original ticket is required and a photo is not accepted; give a practical grounded suggestion.'),
 dict(id='pickup-current-correction',expected='silence',
      past='For the community pottery pickup, the studio requires the original claim ticket. A photo of the ticket is not accepted.',
      live='For the community pottery pickup, I called the studio today. They changed the rule and confirmed a photo of the claim ticket is now accepted. I have the photo ready.',
      rubric='Respect the explicit current correction; do not insist on the obsolete original-ticket rule.'),
 dict(id='club-spending-limit',expected='contribute',
      past='The astronomy club agreed to spend at most $80 on snacks for its stargazing event. The grocery order is $65; delivery adds $25.',
      live='For the astronomy club stargazing event, I am placing the $65 grocery order with $25 delivery. Are we ready to confirm?',
      rubric='Point out the $90 total exceeds the agreed $80 cap; distinguish any proposed alternative from a known available option.'),
 dict(id='club-topic-only',expected='silence',
      past='The astronomy club agreed to spend at most $80 on snacks for its stargazing event. The grocery order is $65; delivery adds $25.',
      live='For the astronomy club stargazing event, let us talk about identifying constellations. How do we find Orion in the sky?',
      rubric='Shared club/event vocabulary alone is not a useful opening for a snacks-budget interruption.'),
]


def cases():
    rows=[]
    for case in CASES:
        with tempfile.TemporaryDirectory() as directory:
            store=MemoryStore(Path(directory)/'memory.sqlite',clock=lambda:300.)
            owner=store.owner_for('fictional-usefulness')
            store.put_source(owner,recording('prior',case['past']))
            live=recording('capture',case['live'],completed=False)
            context=prepare(store,owner,live)
            assert context and context['state']['sources'],case['id']
            rows.append(dict(case=case['id'],expected=case['expected'],rubric=case['rubric'],
                             request=draft_request(context['state'])))
    return rows


if __name__=='__main__':
    rows=cases();Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(cases=[r['case'] for r in rows],baseline='proactive-v4',paid_calls=0)))
