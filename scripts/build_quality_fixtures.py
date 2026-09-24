"""Deterministic synthetic screening fixtures; no API calls."""
import array
import json
import math
from pathlib import Path
import random
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/quality'
OUT.mkdir(parents=True, exist_ok=True)
turns = [
    ('Samantha', 'The specialist mentioned echocardiography and a follow up appointment. Please bring the vaccination history and the medication list.'),
    ('Daniel', 'I wrote those down. Should we ask about the laboratory results before scheduling another visit next Thursday?'),
    ('Samantha', 'Yes. Let us confirm the appointment time and write down any questions before we leave.'),
    ('Daniel', 'At the lecture we compared photosynthesis with cellular respiration. The professor asked us to explain how energy moves through each process.'),
    ('Samantha', 'My notes include the definition of chlorophyll and the role of mitochondria. I still need to review the diagram from the second slide.'),
    ('Daniel', 'We can study together tomorrow. First we should list the terms we understand, then identify the questions that remain unanswered.'),
]
clips = []
for index, (voice, text) in enumerate(turns):
    aiff, wav = OUT / f'{index}.aiff', OUT / f'{index}.wav'
    subprocess.run(['say', '-v', voice, '-r', '165', '-o', str(aiff), text], check=True)
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', '-c', '1', str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as stream:
        pcm = array.array('h', stream.readframes(stream.getnframes()))
    clips.append(pcm)

def save(name, count, noisy=False):
    pcm = array.array('h')
    reference = []
    for index in range(count):
        if index: pcm.extend([0] * 6400)
        start = len(pcm) / 16000
        pcm.extend(clips[index])
        reference.append({'speaker': index % 2, 'text': turns[index][1], 'start': start, 'end': len(pcm) / 16000})
    if noisy:
        rng = random.Random(20260924)
        rms = math.sqrt(sum(x*x for x in pcm) / len(pcm))
        sigma = rms / (10 ** (12 / 20))
        pcm = array.array('h', (max(-32768, min(32767, round(x + rng.gauss(0, sigma)))) for x in pcm))
    folder = OUT / name
    folder.mkdir(exist_ok=True)
    with wave.open(str(folder / 'voice.wav'), 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())
    (folder / 'reference.json').write_text(json.dumps({'name': name, 'turns': reference, 'noise_db': 12 if noisy else None}, indent=2))
    duration = len(pcm) / 16000
    assert duration < 55
    print(json.dumps({'fixture': name, 'seconds': duration, 'estimated_usd': duration * .2 / 3600}))

save('clean', 3)
save('noisy', 3, noisy=True)
save('near-limit', 6)
