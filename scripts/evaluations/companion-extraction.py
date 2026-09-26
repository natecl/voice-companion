"""Same-model extraction control. Proposals only, not full Jev admission/retention."""
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Backend'))
from memory_evidence import extraction_request, parse_recording_extraction

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[2]
cases = json.loads((root / 'Backend/fixtures/gbrain-comparison/model-cases.json').read_text())
originals = {s['session_id']: s for s in json.loads((root / 'Backend/fixtures/gbrain-comparison/sources.json').read_text())}
results = []
for case in cases:
    source = originals.get(case['id'])
    if source is None:
        passages = []
        for i, line in enumerate(case['text'].splitlines()):
            match = re.fullmatch(r'Speaker ([AB]) \((\d+)s\): (.*)', line)
            speaker, start, text = match.groups()
            passages.append(dict(id='p'+str(i+1),start=float(start),duration=3.0,speakers=[ord(speaker)-65],text=text))
        source = dict(session_id=case['id'],revision=1,completed=True,captured_at=1790431200.0,timezone='UTC',origin='recording',passages=passages)
    request = dict(kind='chat',body=extraction_request(source))
    process = subprocess.run(['ssh','-i','/Users/n.chinlue/.ssh/voice_companion_render','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
        'srv-daqtfs7lot8c73dleuug@ssh.virginia.render.com','python3 /tmp/gbrain-provider-20260926.py'],
        input=json.dumps(request),capture_output=True,text=True,timeout=60)
    if process.returncode:
        raise RuntimeError(process.stdout)
    saved = json.loads(process.stdout)
    result = dict(case=case['id'],source=source,**saved)
    results.append(result)
    (out/'report.json').write_text(json.dumps(results,indent=2))
    response = saved['response']
    if response.get('status') != 'completed':raise ValueError('Incomplete extraction; no retry')
    text = ''.join(c['text'] for o in response['output'] for c in o.get('content',[]) if c['type']=='output_text')
    result['proposals'] = parse_recording_extraction(json.loads(text),source)
    (out/'report.json').write_text(json.dumps(results,indent=2))
    print(case['id'],len(result['proposals']),'parsed proposals',flush=True)
