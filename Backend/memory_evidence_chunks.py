"""Evidence-writer chunk contract and exact mapping back to original passages."""
import json
import memory_chunks
import memory_evidence
import memory_judgments
import memory_identity_model
import memory_recording_identity

VERSION='evidence-chunks-v1'


def options():
    return dict(extraction=memory_evidence.extraction_request,
        rubric=[VERSION,memory_evidence.VERSION,memory_judgments.VERSION,memory_identity_model.VERSION,memory_recording_identity.VERSION])


def contract(source):return memory_chunks.contract(source,**options())
def plan(source):return memory_chunks.plan(source,**options())
def validate_plan(source,chunks):return memory_chunks.validate_plan(source,chunks,**options())
async def semantic_plan(source,evaluate):return await memory_chunks.semantic_plan(source,evaluate,**options())


def original_proposal(source,chunk,proposal):
    ranges={r['fragment']:r for r in chunk['ranges']}
    # Overlap supplies context; it must not independently create another memory.
    if not any(ranges[s['passage']]['primary'] for s in proposal['spans']):return None
    spans=[];evidence=[]
    for ref,span in zip(proposal['evidence'],proposal['spans']):
        r=ranges[span['passage']]
        spans.append(dict(passage=r['passage'],start=r['start']+span['start'],end=r['start']+span['end']))
        evidence.append(dict(passage=r['passage'],quote=ref['quote']))
    raw={key:proposal[key] for key in memory_evidence.FIELDS};raw['evidence']=evidence
    return memory_evidence.parse(dict(memories=[raw]),source,exact_spans=spans)[0]


def unique(parts):
    # Only the identical proposal at the identical source ranges is repeated work.
    # Semantic duplicates and genuinely repeated statements remain separate evidence.
    seen=set();result=[]
    for part in parts:
        key=json.dumps(part['proposal'],sort_keys=True)
        if key not in seen:seen.add(key);result.append(part)
    return result
