"""Local candidate-discovery baseline for frozen gate messages; no network calls."""
import json,tempfile,time
from pathlib import Path
from local_embeddings import LocalEmbeddings
from memory_store import MemoryStore
from memory_vectors import index_source
from notes_recall import collect
from evaluate_notes_first import seed, save_note
from test_memory import source

root=Path(__file__).resolve().parents[2]
fixtures=root/'Backend/fixtures/memory-gate'
embedder=LocalEmbeddings(root/'work/embedding-models',offline=True)
rows=[]
with tempfile.TemporaryDirectory() as folder:
    store=MemoryStore(Path(folder)/'memory.sqlite',clock=lambda:1790461403.,personal_learning=True,retain_recording_memories=True)
    owner=seed(store,'gate-synthetic','personal')
    for key,text in [('juniper','Project Juniper now meets at the community center instead of the library.'),
                     ('dentist','My dentist appointment is at 10 am on Tuesday.'),
                     ('weekend','I enjoy quiet outdoor walks on weekends.')]:
        src=source(key,text=text);store.put_source(owner,src)
        save_note(store,owner,src,dict(title=key,overview=dict(text=text,passages=['p1']),sections=[]))
    with store.connect() as db:
        sessions=[r[0] for r in db.execute('SELECT session FROM source WHERE owner=? AND deleted=0',(owner,))]
    for session in sessions:index_source(store,owner,session,embedder)
    for case in json.loads((fixtures/'cases.json').read_text()):
        start=time.monotonic()
        candidates=collect(store,owner,case['message'],embedder=embedder)
        rows.append(dict(id=case['id'],candidates=len(candidates),seconds=time.monotonic()-start,
                         baseline_ranking_call=bool(candidates)))
(fixtures/'baseline.json').write_text(json.dumps(dict(corpus='Five synthetic recordings: Maya, anonymous marathon speaker, Juniper, dentist, weekend preference; local CPU discovery only, no ranking/answer calls.',cases=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
