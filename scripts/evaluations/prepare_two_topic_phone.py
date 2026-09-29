"""Prepare fictional phone-pilot sources in a LOCAL QA database only.

No hosted writes, budget provisioning, learning, generated notes or network.
Activation must use a new approved phone allowance and isolated source registry.
"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Backend'))
from memory_store import MemoryStore
from proactive_conversation_replay import SOURCES
from proactive_replay import recording


def prepare(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    store=MemoryStore(directory/'memory.sqlite',clock=lambda:300.)
    owner=store.owner_for('fictional-two-topic-phone-preparation')
    records=[]
    for key,text in SOURCES.items():
        source=recording('two-topic-pilot-'+key,text)
        store.put_source(owner,source,learn=False,generate_notes=False)
        records.append(source)
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM source').fetchone()[0]==2
        assert db.execute('SELECT count(*) FROM job').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM recording_notes').fetchone()[0]==0
    (directory/'seed-sources.json').write_text(json.dumps(records,indent=2))
    return dict(status='prepared locally, NOT activated on phone',sources=[s['session_id'] for s in records],
        learning_jobs=0,generated_notes=0,paid_calls=0)


if __name__=='__main__':print(json.dumps(prepare(sys.argv[1]),indent=2))
