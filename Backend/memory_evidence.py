"""Versioned extraction proposals with exact source spans; no memory mutations."""
import json
from pathlib import Path
from admission import Rejected
from memory_identity import description
from memory_models import LUNA
from profile_identity import personal

VERSION = 'memory-evidence-v2.5'
RECORDING_CONTINUITY = '\nRead passages in order as one conversation. A named subject can be a project, group, person or pet, not just a speaker. For example, p1="Team Aspen." p2="Prefers evenings." supports named Team Aspen; cite BOTH excerpts. Do not turn a continuing predicate into a speaker preference. A following same-topic detail such as "Its meetings are at the cafe" also concerns that named subject; include the earlier name as evidence instead of extracting the detail in isolation. Carry subjects only across clear discourse, never across competing subjects or topic/quotation changes. If cited excerpts lack one consistent speaker label, use null. A plain present-tense statement is current as reported at capture time, not proof it remains true today. This does not identify the account owner.'
PROMPT = (Path(__file__).parent/'prompts/memory-evidence-v2.md').read_text()


def object_schema(fields):
    return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)


def enum(*values):
    return {'type':'string','enum':list(values)}


NULLABLE_TEXT={'type':['string','null']}
MENTION=object_schema(dict(name=NULLABLE_TEXT,relationship=NULLABLE_TEXT,
    qualifiers={'type':'array','items':{'type':'string'}},speaker_label={'type':['integer','null']}))
FIELDS=dict(text={'type':'string'},kind=enum('fact','preference','event','decision'),basis=enum('stated','tentative'),
    mention=MENTION,scope=enum('author','related_to_author','named','unresolved'),
    evidence={'type':'array','items':object_schema(dict(passage={'type':'string'},quote={'type':'string'}))},
    time=object_schema(dict(status=enum('current','past','future','uncertain'),expression=NULLABLE_TEXT)),
    change=object_schema(dict(kind=enum('none','addition','correction','uncertain'),previous_text=NULLABLE_TEXT)))
SCHEMA=object_schema(dict(memories={'type':'array','items':object_schema(FIELDS)}))


def extraction_request(source):
    schema=SCHEMA
    view=source
    instructions=PROMPT
    if not personal(source):
        # Authorship is application provenance, not a probabilistic extraction choice.
        variants=[]
        for scope,name_type in [('named','string'),('unresolved','null')]:
            mention=object_schema(dict(MENTION['properties'],name={'type':name_type}))
            variants.append(object_schema(dict(FIELDS,scope=enum(scope),mention=mention)))
        schema=object_schema(dict(memories={'type':'array','items':{'anyOf':variants}}))
        instructions+='\nApplication provenance: these are unidentified recording speakers. Use named when the memory subject has an explicit name, even though cross-source identity is not verified. Use unresolved with null name for an unnamed subject. Never infer an account-owner relationship.'
        instructions+=RECORDING_CONTINUITY
        view=dict(source,origin='recording')
    request=dict(model=LUNA,reasoning={'effort':'none'},service_tier='default',instructions=instructions,
        input=json.dumps(view,ensure_ascii=False),max_output_tokens=3000,store=False,tools=[],truncation='disabled',
        text={'format':dict(type='json_schema',name='memory_evidence_v2',strict=True,schema=schema)})
    if len(json.dumps(request,ensure_ascii=False).encode())>16000:raise Rejected('memory_extraction_too_large')
    return request


def text(value,limit,*,nullable=False):
    return (nullable and value is None) or (isinstance(value,str) and bool(value.strip()) and len(value)<=limit)


def parse(data,source,*,exact_spans=None):
    if (not isinstance(data,dict) or set(data)!={'memories'} or not isinstance(data['memories'],list)
            or len(data['memories'])>8):raise Rejected('invalid_evidence_extraction')
    if exact_spans is not None and len(data['memories'])!=1:raise Rejected('invalid_evidence_sources')
    passages={p['id']:p for p in source['passages']};result=[]
    for candidate in data['memories']:
        if not isinstance(candidate,dict) or set(candidate)!=set(FIELDS):raise Rejected('invalid_evidence_extraction')
        c=candidate
        if not text(c['text'],2000):raise Rejected('invalid_evidence_extraction')
        for key in ('kind','basis','scope'):
            if c[key] not in FIELDS[key]['enum']:raise Rejected('invalid_evidence_extraction')
        description(c['mention'])
        if c['mention']['qualifiers'] is None:raise Rejected('invalid_evidence_extraction')
        if c['scope'] in ('author','related_to_author') and not personal(source):
            raise Rejected('unsupported_author_identity')
        if c['scope']=='author' and (c['mention']['name'] is not None or c['mention']['relationship'] is not None):
            raise Rejected('invalid_evidence_extraction')
        if c['scope']=='related_to_author' and not c['mention']['relationship']:raise Rejected('invalid_evidence_extraction')
        if c['scope']=='named' and not c['mention']['name']:raise Rejected('invalid_evidence_extraction')
        if c['scope']=='unresolved' and c['mention']['name'] is not None:raise Rejected('invalid_evidence_extraction')
        for key in ('time','change'):
            schema=FIELDS[key]
            if not isinstance(c[key],dict) or set(c[key])!=set(schema['properties']):raise Rejected('invalid_evidence_extraction')
        if c['time']['status'] not in FIELDS['time']['properties']['status']['enum']:raise Rejected('invalid_evidence_extraction')
        if not text(c['time']['expression'],200,nullable=True):raise Rejected('invalid_evidence_extraction')
        if c['change']['kind'] not in FIELDS['change']['properties']['kind']['enum']:raise Rejected('invalid_evidence_extraction')
        if not text(c['change']['previous_text'],500,nullable=True):raise Rejected('invalid_evidence_extraction')
        if c['change']['kind'] in ('none','addition') and c['change']['previous_text'] is not None:raise Rejected('invalid_evidence_extraction')
        if not isinstance(c['evidence'],list) or not 1<=len(c['evidence'])<=4:raise Rejected('invalid_evidence_sources')
        spans=[]
        if exact_spans is not None and len(exact_spans)!=len(c['evidence']):raise Rejected('invalid_evidence_sources')
        for index,ref in enumerate(c['evidence']):
            if not isinstance(ref,dict) or set(ref)!={'passage','quote'}:raise Rejected('invalid_evidence_sources')
            if not isinstance(ref['passage'],str):raise Rejected('invalid_evidence_sources')
            p=passages.get(ref['passage']);quote=ref['quote']
            if p is None or not text(quote,2000):raise Rejected('invalid_evidence_quote')
            if exact_spans is None:
                if p['text'].count(quote)!=1:raise Rejected('invalid_evidence_quote')
                start=p['text'].index(quote)
            else:
                span=exact_spans[index]
                if (set(span)!={'passage','start','end'} or span['passage']!=ref['passage']
                        or type(span['start']) is not int or type(span['end']) is not int
                        or not 0<=span['start']<span['end']<=len(p['text'])
                        or p['text'][span['start']:span['end']]!=quote):raise Rejected('invalid_evidence_quote')
                start=span['start']
            label=c['mention']['speaker_label']
            if label is not None and p['speakers']!=[label]:raise Rejected('invalid_mention_speaker')
            spans.append(dict(passage=ref['passage'],start=start,end=start+len(quote)))
        expression=c['time']['expression']
        if expression is not None and not any(expression in r['quote'] for r in c['evidence']):raise Rejected('unsupported_time_expression')
        if any(not any(q in r['quote'] for r in c['evidence']) for q in c['mention']['qualifiers']):raise Rejected('unsupported_qualifier')
        result.append(dict(c,spans=spans,contract=VERSION))
    return result


def parse_recording_extraction(data,source):
    """Discard a narrator hint when cited spans mix that label with unlabelled audio.

    Raw provider output remains in the audit cache. Wrong/conflicting speaker labels
    still fail strict parsing. Missing diarization cannot destroy supported text.
    """
    if personal(source):return parse(data,source)
    normalized=json.loads(json.dumps(data))
    passages={p['id']:p for p in source['passages']}
    if isinstance(normalized,dict) and isinstance(normalized.get('memories'),list):
        for c in normalized['memories']:
            if not isinstance(c,dict) or not isinstance(c.get('mention'),dict) or not isinstance(c.get('evidence'),list):continue
            label=c['mention'].get('speaker_label')
            refs=c['evidence']
            if type(label) is not int or not refs:continue
            if any(not isinstance(r,dict) or not isinstance(r.get('passage'),str) or r['passage'] not in passages for r in refs):continue
            speakers=[passages[r['passage']]['speakers'] for r in refs]
            if [] in speakers and all(s in ([],[label]) for s in speakers):c['mention']['speaker_label']=None
    return parse(normalized,source)
