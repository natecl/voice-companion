"""Export three fictional structured-delivery requests. Never calls a provider."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from proactive_models import draft_request


def prepare():
    previous = ROOT / 'Backend/fixtures/proactive/conversational-iteration-evaluation/requests.json'
    return [dict(case='structured-' + row['case'], expected=row['expected'],
                 request=draft_request(json.loads(row['request']['input']), structured_delivery=True))
            for row in json.loads(previous.read_text()) if row['version'] == 7]


if __name__ == '__main__':
    rows = prepare()
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(dict(cases=[row['case'] for row in rows], paid_calls=0)))
