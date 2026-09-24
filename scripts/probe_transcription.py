"""One bounded paid streaming probe. Synthetic/consented PCM16 WAV only."""
import argparse
import asyncio
import json
from pathlib import Path
import time
import wave
import websockets

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, default=ROOT / 'work/transcription')
OUT = parser.parse_args().directory

async def main():
    values = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
                  if '=' in line and not line.lstrip().startswith('#'))
    key = values.get('XAI_API_KEY', '').strip().strip('\"\'')
    if not key:
        raise RuntimeError('Missing API key')
    with wave.open(str(OUT / 'voice.wav')) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 16000)
        duration = audio.getnframes() / 16000
        assert 0 < duration <= 30, 'Probe capped at 30 seconds'
        pcm = audio.readframes(audio.getnframes())
    started = time.monotonic()
    events = []
    summary = {'audio_seconds': duration, 'estimated_audio_cost_usd': duration * .20 / 3600,
               'billing_verified': False, 'automatic_retries': 0, 'status': 'started'}
    with (OUT / 'usage.jsonl').open('a') as ledger:
        ledger.write(json.dumps(summary) + '\n')
    url = ('wss://api.x.ai/v1/stt?model=grok-voice-transcribe-2.0&sample_rate=16000'
           '&encoding=pcm&interim_results=true&diarize=true&language=en')
    try:
        async with asyncio.timeout(50):
            async with websockets.connect(url, additional_headers={'Authorization': f'Bearer {key}'},
                                          open_timeout=10, close_timeout=3) as ws:
                ready = json.loads(await ws.recv())
                events.append({'elapsed': time.monotonic()-started, 'event': ready})
                if ready.get('type') != 'transcript.created':
                    raise RuntimeError('Expected transcript.created')
                async def send():
                    for offset in range(0, len(pcm), 3200):
                        await ws.send(pcm[offset:offset+3200])
                        await asyncio.sleep(.1)
                    await ws.send(json.dumps({'type': 'audio.done'}))
                sender = asyncio.create_task(send())
                try:
                    async for raw in ws:
                        event = json.loads(raw)
                        events.append({'elapsed': time.monotonic()-started, 'event': event})
                        if event.get('type') == 'error':
                            raise RuntimeError('Provider error; inspect saved event')
                        if event.get('type') == 'transcript.done':
                            summary['status'] = 'completed'
                            break
                    if summary['status'] != 'completed':
                        raise RuntimeError('Connection ended before transcript.done')
                finally:
                    if not sender.done():
                        sender.cancel()
                    await asyncio.gather(sender, return_exceptions=True)
    except Exception as error:
        summary['status'] = 'failed'
        summary['error_type'] = type(error).__name__
        if hasattr(error, 'response'):
            summary['http_status'] = error.response.status_code
    finally:
        summary['elapsed_seconds'] = time.monotonic()-started
        (OUT / 'events.json').write_text(json.dumps(events, indent=2))
        (OUT / 'summary.json').write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
    if summary['status'] != 'completed':
        raise SystemExit(1)

if __name__ == '__main__':
    asyncio.run(main())
