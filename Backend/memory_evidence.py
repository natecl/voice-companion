"""Versioned extraction proposals with exact source spans; no memory mutations."""
import json
from pathlib import Path
from admission import Rejected
from memory_identity import description
from memory_models import LUNA
from profile_identity import personal

VERSION = 'memory-evidence-v2.1'
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
    request=dict(model=LUNA,reasoning={'effort':'none'},service_tier='default',instructions=PROMPT,
        input=json.dumps(source,ensure_ascii=False),max_output_tokens=3000,store=False,tools=[],truncation='disabled',
        text={'format':dict(type='json_schema',name='memory_evidence_v2',strict=True,schema=SCHEMA)})
    if len(json.dumps(request,ensure_ascii=False).encode())>16000:raise Rejected('memory_extraction_too_large')
    return request


def text(value,limit,*,nullable=False):
    return (nullable and value is None) or (isinstance(value,str) and bool(value.strip()) and len(value)<=limit)


def parse(data,source):
    if (not isinstance(data,dict) or set(data)!={'memories'} or not isinstance(data['memories'],list)
            or len(data['memories'])>8):raise Rejected('invalid_evidence_extraction')
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
        for ref in c['evidence']:
            if not isinstance(ref,dict) or set(ref)!={'passage','quote'}:raise Rejected('invalid_evidence_sources')
            if not isinstance(ref['passage'],str):raise Rejected('invalid_evidence_sources')
            p=passages.get(ref['passage']);quote=ref['quote']
            if p is None or not text(quote,2000) or p['text'].count(quote)!=1:raise Rejected('invalid_evidence_quote')
            label=c['mention']['speaker_label']
            if label is not None and p['speakers']!=[label]:raise Rejected('invalid_mention_speaker')
            start=p['text'].index(quote)
            spans.append(dict(passage=ref['passage'],start=start,end=start+len(quote)))
        expression=c['time']['expression']
        if expression is not None and not any(expression in r['quote'] for r in c['evidence']):raise Rejected('unsupported_time_expression')
        if any(not any(q in r['quote'] for r in c['evidence']) for q in c['mention']['qualifiers']):raise Rejected('unsupported_qualifier')
        result.append(dict(c,spans=spans,contract=VERSION))
    return result
