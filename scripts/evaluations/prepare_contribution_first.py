"""Export a bounded voice/transfer/silence screen; no provider transport."""
import copy
import json
from pathlib import Path
import sys
from prepare_structured_proactive import prepare, ROOT
from proactive_models import draft_request


def cases():
    rows=prepare()
    rubrics={
        'structured-missing-prerequisite': dict(
            move='Engage the calendar decision with a useful status question or grounded next step, not three retrospective facts.',
            preserve=['team agreement','basic recording flow','five people','before adding features','unknown current completion','calendar waits']),
        'structured-rescheduled-study-session': dict(
            move='Correct the plan to meet at 3 directly, then give the practical reason.',
            preserve=['5 PM instead of 3 PM','library unavailable before 5','library location']),
        'structured-acknowledged-after-cooldown': dict(
            move='Stay silent; the group already addressed the prerequisite.',preserve=[]),
    }
    for row in rows:
        row['rubric']=rubrics[row['case']]
        row['case']='contribution-first-'+row['case'].removeprefix('structured-')
    initial=json.loads(rows[0]['request']['input'])
    state=copy.deepcopy(initial)
    state['current']['passages'][0]['text']='For the Cedar pilot, all five people have now tested the basic recording flow. We finished the agreed tests. We are ready to add calendar integration.'
    rows.append(dict(case='contribution-first-tests-completed',expected='silence',
        request=draft_request(state,structured_delivery=True),
        rubric=dict(move='Accept the current completion update; do not repeat the old pending status or ask whether tests happened.',preserve=[])))
    state=copy.deepcopy(initial)
    state['current']['passages'][0]['text']='For the Juniper meetup, I am about to book the 80-seat hall for $450. Shall I confirm it?'
    source=state['sources'][0];source['session_id']='juniper'
    source['text']='The Juniper group agreed on a total venue budget of $300. Only 20 people are attending. The 30-seat room costs $240, while the 80-seat hall costs $450. Both rooms are available for the meetup.'
    source['text_end']=len(source['text'])
    rows.append(dict(case='contribution-first-venue-choice',expected='contribute',
        request=draft_request(state,structured_delivery=True),
        rubric=dict(move='Help choose an available room within the agreed budget, rather than recite venue facts.',
            preserve=['$300 budget','$450 hall exceeds budget','20 people','30-seat room $240','availability'])))
    return rows


if __name__=='__main__':
    rows=cases()
    Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(cases=[r['case'] for r in rows],paid_calls=0)))
