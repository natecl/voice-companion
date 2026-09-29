"""Prepare independent Jev opportunity and Luna voice checks; no transport."""
import json
from pathlib import Path
import sys
from prepare_contribution_first import cases
from proactive_models import judge_request
from proactive_writer import writer_request


def prepare():
    rows=[]
    for case in cases():
        name=case['case'].removeprefix('contribution-first-')
        if name == 'rescheduled-study-session':
            continue
        state=json.loads(case['request']['input'])
        rows.append(dict(case='gate-'+name, stage='gate', expected=case['expected'],
                         request=judge_request(state), rubric=case['rubric']))
        if name in ('missing-prerequisite', 'venue-choice'):
            rows.append(dict(case='writer-'+name, stage='writer', expected='contribute',
                             request=writer_request(state), rubric=case['rubric']))
    return rows


if __name__ == '__main__':
    rows=prepare()
    Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(cases=[row['case'] for row in rows], paid_calls=0)))
