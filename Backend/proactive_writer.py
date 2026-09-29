"""Conversational writer after the existing Jev gate. Opt-in; no transport."""
from pathlib import Path
from admission import Rejected
from proactive_models import draft_request, parse_draft

PROMPT = (Path(__file__).parent / 'prompts/proactive-writer-candidate.md').read_text()


def writer_request(state):
    request = draft_request(state, grouped_messages=True)
    request['instructions'] = PROMPT
    output_format = request['text']['format']
    output_format['name'] = 'proactive_writer_v1'
    del output_format['schema']['properties']['decision']
    output_format['schema']['required'].remove('decision')
    return request


def parse_writer(data, state):
    if not isinstance(data, dict) or set(data) != {'messages', 'evidence_ids'}:
        raise Rejected('invalid_proactive_output')
    # Empty delivery is a last safeguard, not a second timing classification.
    return parse_draft(dict(data, decision='silence' if data['messages'] == [] else 'contribute'),
                       state, grouped_messages=True)
