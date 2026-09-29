"""Predeclare matched failure checks and fresh topic-transfer pairs; no transport."""
import json
from pathlib import Path
import sys
from prepare_proactive_usefulness import cases as baseline_cases, ROOT
from proactive_models import draft_request

PROMPT=(ROOT/'Backend/prompts/proactive-current-focus-candidate.md').read_text()

def cases():
    baseline={row['case']:row for row in baseline_cases()}
    rows=[dict(baseline[name],request=dict(baseline[name]['request'],instructions=PROMPT))
          for name in ('club-spending-limit','club-topic-only')]
    pairs=[
        ('trail', 'For the Willow hiking group, the north trail is closed this weekend. The south trail is open.',
         'The Willow hiking group is choosing a trail for this weekend. Shall we take the north trail?',
         'The Willow hiking group is discussing how to identify oak leaves. What features should we look for?',
         'Mention the north closure and open south option only during route selection.'),
        ('choir', 'For the Elm choir rehearsal, the venue changed from Hall A to Hall B because Hall A is being repaired.',
         'I am sending the Elm choir rehearsal directions now. I will tell everyone to go to Hall A.',
         'The Elm choir rehearsal discussion has moved to breathing technique. How should we practice sustaining a note?',
         'Correct the venue to Hall B during directions; do not interrupt the breathing discussion.'),
    ]
    template=json.loads(baseline['club-spending-limit']['request']['input'])
    for name,past,relevant,unrelated,rubric in pairs:
        for suffix,current,expected in [('relevant',relevant,'contribute'),('unrelated',unrelated,'silence')]:
            state=json.loads(json.dumps(template))
            state['sources'][0].update(text=past,text_end=len(past))
            state['current']['passages'][0]['text']=current
            rows.append(dict(case=name+'-'+suffix,expected=expected,rubric=rubric,
                             request=dict(draft_request(state),instructions=PROMPT)))
    return rows

if __name__=='__main__':
    rows=cases();Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(cases=[r['case'] for r in rows],paid_calls=0)))
