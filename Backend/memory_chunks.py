"""Lossless deterministic turn chunks. Jev boundary selection is a later adapter.

Ranges are character offsets in original passage text, never fabricated audio
positions. Context overlap is bounded and does not replace primary coverage.
"""
import hashlib
import json
from admission import Rejected
from memory_models import extraction_request, JEV, RUBRIC
from profile_identity import PROFILE_RUBRIC

VERSION = 'turn-chunks-v1'
TARGET_REQUEST_BYTES = 10000
MAX_CHUNKS = 32


def contract(source):
    # Bump VERSION whenever chunk selection/mapping or completed-result semantics change.
    value = [VERSION, JEV, RUBRIC, PROFILE_RUBRIC, extraction_request(dict(source,passages=[]))]
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def request_size(source):
    return len(json.dumps(extraction_request(source), ensure_ascii=False).encode())


def pieces(source):
    for passage in source['passages']:
        text, start = passage['text'], 0
        while start < len(text):
            lo, hi = 1, len(text)-start
            while lo < hi:
                mid = (lo+hi+1)//2
                if len(json.dumps(text[start:start+mid], ensure_ascii=False).encode()) <= 2000:
                    lo = mid
                else:
                    hi = mid-1
            end = start+lo
            if end < len(text):
                boundaries = [i+1 for i in range(start+lo*3//4,end) if text[i].isspace()]
                if boundaries: end = boundaries[-1]
            yield passage, start, end
            start = end


def plan(source):
    # Small sources retain their exact original prompt and passage IDs.
    try:
        extraction_request(source)
        return []
    except Rejected as error:
        if str(error) != 'memory_extraction_too_large': raise
    chunks, current = [], []

    def build(entries):
        ranges, passages = [], []
        for index, (passage,start,end,primary) in enumerate(entries):
            fragment = f'fragment-{index}'
            passages.append(dict(passage,id=fragment,text=passage['text'][start:end]))
            ranges.append(dict(fragment=fragment,passage=passage['id'],start=start,end=end,primary=primary))
        return dict(source,passages=passages), ranges

    def append(entries):
        view, ranges = build(entries)
        digest = hashlib.sha256(json.dumps([VERSION,source['revision'],view,ranges],sort_keys=True).encode()).hexdigest()
        chunks.append(dict(id=digest,version=VERSION,contract=contract(source),source=view,ranges=ranges,strategy='deterministic_turn_overlap'))
        if len(chunks) > MAX_CHUNKS: raise Rejected('memory_chunk_limit')

    for passage,start,end in pieces(source):
        entry = (passage,start,end,True)
        candidate,_ = build(current+[entry])
        if current and request_size(candidate) > TARGET_REQUEST_BYTES:
            append(current)
            prior, pstart, pend, _ = current[-1]
            # A small preceding excerpt supplies local continuity, not a summary.
            current = [(prior,max(pstart,pend-200),pend,False)]
        current.append(entry)
        view,_ = build(current)
        if request_size(view) > TARGET_REQUEST_BYTES: raise Rejected('memory_chunk_too_large')
    if current: append(current)
    return chunks


def original_claims(chunk, claims):
    mapping = {r['fragment']:r['passage'] for r in chunk['ranges']}
    result=[]
    for claim in claims:
        if any(p not in mapping for p in claim['passages']): raise Rejected('invalid_chunk_sources')
        result.append(dict(claim,passages=sorted({mapping[p] for p in claim['passages']})))
    return result


def deduplicate(claims):
    """Exact repetition only; semantic equivalence still needs independent judgment."""
    unique={}
    for claim in claims:
        key=json.dumps({k:v for k,v in claim.items() if k!='passages'},sort_keys=True)
        if key not in unique: unique[key]=dict(claim,passages=list(claim['passages']))
        else: unique[key]['passages']=sorted(set(unique[key]['passages'])|set(claim['passages']))
    return list(unique.values())
