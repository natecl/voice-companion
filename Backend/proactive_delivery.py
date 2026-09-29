"""Candidate one-call evidence/delivery contract, normalized to existing chat storage."""
from admission import Rejected


def schema(evidence_ids):
    def object_schema(properties):
        return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)
    return object_schema(dict(
        decision=dict(type='string', enum=['silence', 'contribute']),
        facts=dict(type='array', description='Distinct decision-relevant source excerpts, including conditions and status.',
            items=object_schema(dict(evidence_id=dict(type='string', enum=evidence_ids), quote=dict(type='string')))),
        messages=dict(type='array', description='Ordered separate texts. Express each fact once in its own message.',
            items=object_schema(dict(
                fact_index=dict(type=['integer', 'null'], description='Zero-based facts index, or null for one optional suggestion/question.'),
                text=dict(type='string', description='One conversational beat, not a recap.'))))))


def normalize(data, state):
    """Check literal support and complete index coverage, NOT semantic entailment/tone.

    The model can still omit a fact or misphrase a quoted fact. Live evaluation must
    establish those properties. Never repair, truncate or retry a rejected output.
    """
    def reject():
        raise Rejected('invalid_proactive_output')
    if (not isinstance(data, dict) or set(data) != {'decision', 'facts', 'messages'}
            or data['decision'] not in ('silence', 'contribute')
            or not isinstance(data['facts'], list) or not isinstance(data['messages'], list)):
        reject()
    if data['decision'] == 'silence':
        if data['facts'] or data['messages']: reject()
        return dict(decision='silence', text='', evidence_ids=[])
    if not data['facts'] or not data['messages']: reject()
    sources = {source['id']: source['text'] for source in state['sources']}
    evidence_ids = []
    excerpts = set()
    for fact in data['facts']:
        if (not isinstance(fact, dict) or set(fact) != {'evidence_id', 'quote'}
                or not isinstance(fact['evidence_id'], str) or fact['evidence_id'] not in sources
                or not isinstance(fact['quote'], str) or not fact['quote'].strip()
                or fact['quote'] not in sources[fact['evidence_id']]):
            reject()
        key = (fact['evidence_id'], fact['quote'])
        if key in excerpts: reject()
        excerpts.add(key)
        if fact['evidence_id'] not in evidence_ids: evidence_ids.append(fact['evidence_id'])
    covered = set()
    messages = []
    suggestions = 0
    for message in data['messages']:
        if (not isinstance(message, dict) or set(message) != {'fact_index', 'text'}
                or not isinstance(message['text'], str) or not message['text'].strip()
                or '\n' in message['text'] or '\r' in message['text']):
            reject()
        index = message['fact_index']
        if index is None:
            suggestions += 1
            if suggestions > 1: reject()
        elif type(index) is not int or not 0 <= index < len(data['facts']) or index in covered:
            reject()
        else:
            covered.add(index)
        messages.append(message['text'])
    if covered != set(range(len(data['facts']))): reject()
    return dict(decision='contribute', text='\n\n'.join(messages), evidence_ids=evidence_ids)
