"""One bounded question-only judgment. Failure always preserves direct answering."""
import asyncio
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time

MODEL = 'jev-1.13.0'
VERSION = 'question-intent-v1'
WAIT_SECONDS = .750
MIN_CONFIDENCE = .70
MIN_PROBABILITY = .80
QUESTION = json.loads((Path(__file__).parent / 'prompts/jev-question-v1.json').read_text())
POLICIES = {
    'recall': 'Answer the specific factual question directly from the conversation. Preserve uncertainty and do not add unrequested advice.',
    'summary': 'Synthesize the requested scope, separating decisions, proposals, unresolved questions and explicit next steps. Do not infer commitments.',
    'perspective': 'Offer the requested reasoning or recommendation. Clearly distinguish your perspective from cited conversation facts; do not merely summarize.',
}


@dataclass(frozen=True)
class Judgment:
    route: str = 'direct'
    reason: str = 'unavailable'
    seconds: float = 0
    input_tokens: int | None = None


def payload(question):
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise ValueError('Invalid question')
    value = {'model': MODEL, 'state': {'user_question': question}, 'questions': {'intent': QUESTION}}
    if len(json.dumps(value, ensure_ascii=False).encode()) > 8000:
        raise ValueError('Routing input too large')
    return value


def interpret(data):
    if data['model'] != MODEL:
        raise ValueError('Unexpected model')
    answer = data['answers']['intent']
    choice, probabilities, confidence = answer['choice'], answer['probabilities'], answer['confidence']
    if answer['type'] != 'choice' or set(probabilities) != set(QUESTION['criteria']) or choice not in probabilities:
        raise ValueError('Unexpected choice')
    for value in [confidence, *probabilities.values()]:
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Invalid probability')
    if abs(sum(probabilities.values()) - 1) > .01 or probabilities[choice] < max(probabilities.values()):
        raise ValueError('Invalid distribution')
    tokens = data['usage']['input_tokens']
    if type(tokens) is not int or not 0 <= tokens <= 9000:
        raise ValueError('Unexpected usage')
    if choice == 'mixed_uncertain':
        return Judgment(reason='mixed_uncertain', input_tokens=tokens)
    if confidence < MIN_CONFIDENCE or probabilities[choice] < MIN_PROBABILITY:
        return Judgment(reason='uncertain', input_tokens=tokens)
    return Judgment(route=choice, reason='classified', input_tokens=tokens)


class Jev:
    def __init__(self, client):
        self.client = client

    async def classify(self, question):
        # Shared async client reuses TLS connections. No redirects or retries.
        async with self.client.stream('POST', 'https://api.typesafe.ai/v1/systemone', json=payload(question)) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 16000:
                    raise ValueError('Response too large')
            return interpret(json.loads(body))


async def route_question(provider, question, *, store, token):
    started = time.monotonic()
    reservation = None
    completed = False
    result = Judgment()
    try:
        # Accounting failures never allow an unreserved Jev request.
        reservation = store.reserve(token, 'jev')
        async with asyncio.timeout(WAIT_SECONDS):
            result = await provider.classify(question)
        completed = True
    except TimeoutError:
        result = Judgment(reason='timeout')
    except Exception:
        result = Judgment(reason='unavailable')
    finally:
        if reservation:
            store.finish(reservation, completed=completed)
    return Judgment(result.route, result.reason, time.monotonic() - started, result.input_tokens)
