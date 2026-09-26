"""Build frozen synthetic independent-judgment requests without provider calls."""
import copy
import json
from pathlib import Path
from memory_evidence import parse
from memory_judgments import verify_proposals,pair_questions


def build():
    root=Path(__file__).parent/'fixtures'
    def recorded(name):
        record=json.loads((root/'memory_evidence/recorded'/f'{name}.json').read_text())
        return record['source'],parse(record['response']['data'],record['source'])[0]
    source,current=recorded('explicit-change')
    wrong=copy.deepcopy(current);wrong['scope']='author'
    request=verify_proposals(source,[current,wrong])
    cases=[dict(id='source-subject',role=None,request=request,
        expected={'support_0':'supported','subject_0':'related_to_author','modality_0':'supported','time_0':'supported','subject_1':'reject'})]
    anonymous_source,anonymous=recorded('anonymous-speaker')
    claimed=copy.deepcopy(anonymous);claimed['scope']='author';claimed['text']='The user is training for a marathon.'
    cases.append(dict(id='unknown-owner',role=None,request=verify_proposals(anonymous_source,[anonymous,claimed]),
                      expected={'support_0':'supported','subject_0':'unresolved','subject_1':'reject'}))
    prior=dict(source=dict(origin='personal_text',session_id='prior',passages=[dict(id='p1',text='My daughter Maya enjoys swimming.',speakers=[])]),
               memory=dict(text='The author’s daughter Maya enjoys swimming.',mention=dict(name='Maya',relationship='daughter',qualifiers=[],speaker_label=None)))
    other_source,other=recorded('qualified-person')
    pairs=dict(explicit_correction=dict(incoming=dict(source=source,proposal=current),previous=prior),
               other_person=dict(incoming=dict(source=other_source,proposal=other),previous=prior),
               name_only=dict(incoming=dict(source=dict(session_id='next',passages=[dict(text='Maya likes tennis.')])),
                              previous=dict(source=dict(session_id='previous',passages=[dict(text='Maya likes swimming.')]))),
               anonymous=dict(incoming=dict(source=anonymous_source,proposal=anonymous),
                              previous=dict(source=dict(session_id='earlier',passages=[dict(text='I like running.',speakers=[0])]))))
    cases.append(dict(id='identity',role='identity',request=pair_questions(pairs,role='identity'),
                      expected={'explicit_correction':'same','other_person':'different','name_only':'no_same','anonymous':'no_same'}))
    relations=dict(explicit_correction=pairs['explicit_correction'],
                   added_interest=dict(incoming=dict(source=dict(origin='personal_text',passages=[dict(text='My daughter Maya also enjoys tennis.')])),previous=prior),
                   past_description=dict(incoming=dict(source=dict(origin='personal_text',passages=[dict(text='My daughter Maya used to enjoy tennis when she was little.')])),previous=prior))
    cases.append(dict(id='lifecycle',role='relation',request=pair_questions(relations,role='relation'),
                      expected={'explicit_correction':'replacement','added_interest':'addition','past_description':'no_replacement'}))
    return cases

if __name__=='__main__':
    target=Path(__file__).parent/'fixtures/memory_judgments/cases.json'
    if target.exists():raise RuntimeError('Frozen fixture exists; explicit review required before replacement')
    target.write_text(json.dumps(build(),indent=2)+'\n')
