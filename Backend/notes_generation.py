"""Bounded transcript-only notes generation; providers and budgets are injected."""
import asyncio
import json
from pathlib import Path
from admission import Rejected
from recording_notes import MAX_INPUT_BYTES, RecordingNotes

MODEL = 'gpt-6-luna'
PROMPT = (Path(__file__).parent/'prompts/recording-notes-v1.md').read_text()

def object_schema(fields):
    return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)

def request(source):
    payload=json.dumps(source,ensure_ascii=False,separators=(',',':'))
    if len(json.dumps(source,ensure_ascii=False).encode())>MAX_INPUT_BYTES:raise Rejected('notes_input_too_large')
    if not source['passages']:raise Rejected('empty_transcript')
    if source.get('origin')=='personal_text':raise Rejected('notes_require_recording')
    string=dict(type='string')
    bullet=object_schema(dict(text=string,passages=dict(type='array',items=dict(type='string',enum=[p['id'] for p in source['passages']]))))
    section=object_schema(dict(heading=string,items=dict(type='array',items=bullet)))
    schema=object_schema(dict(title=string,overview=bullet,sections=dict(type='array',items=section)))
    return dict(model=MODEL,reasoning={'effort':'none'},service_tier='default',instructions=PROMPT,
        input=payload,max_output_tokens=3000,store=False,tools=[],truncation='disabled',
        text={'format':dict(type='json_schema',name='recording_notes_v1',strict=True,schema=schema)})


class NotesGenerator:
    def __init__(self,store,provider,budget):
        self.notes=RecordingNotes(store);self.provider=provider;self.budget=budget

    async def generate(self,owner,session):
        job=await asyncio.to_thread(self.notes.claim,owner,session)
        if job is None:return False
        reserved=False
        try:
            req=request(job['source'])
            await asyncio.to_thread(self.budget.reserve,job['attempt'],MODEL)
            reserved=True
            result=await self.provider(req)
            await asyncio.to_thread(self.budget.finish,job['attempt'],result.get('usage',{}))
            reserved=False
            await asyncio.to_thread(self.notes.complete,job,result['data'])
            return True
        except BaseException as error:
            if reserved:await asyncio.to_thread(self.budget.finish,job['attempt'])
            reason=('generation_interrupted' if isinstance(error,asyncio.CancelledError) else
                    'budget_limit' if isinstance(error,Rejected) and 'budget' in str(error) else
                    'notes_input_too_large' if str(error)=='notes_input_too_large' else
                    'invalid_notes' if isinstance(error,(KeyError,TypeError,ValueError)) or str(error).startswith(('invalid_notes','notes_too_large')) else
                    'generation_failed')
            await asyncio.to_thread(self.notes.fail,job,reason)
            raise
