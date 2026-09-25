"""One bounded automatic-learning job; uncertainty retains evidence without a UI queue."""
import asyncio
from datetime import datetime
import hashlib
import json
from admission import Rejected
from memory_models import (RUBRIC, extraction_request, judgment_request,
                           parse_candidates, parse_judgments, metered, expiry_options)


def accepted(answer, label):
    return answer['choice'] == label and answer['probabilities'][label] >= .90 and answer['confidence'] >= .60


def subject_key(name):
    if name is None or name.strip().casefold() in ('user','me','i','speaker 1','speaker 2','unknown'):
        return None
    return 'named_' + hashlib.sha256(name.strip().casefold().encode()).hexdigest()[:24]


def expiry(candidate, source):
    value = candidate['expires_at']
    if value is None: return None
    cited = ' '.join(p['text'] for p in source['passages'] if p['id'] in candidate['source_ids'])
    # No model date arithmetic. This slice only normalizes an explicit, verbatim timestamp.
    if value not in cited: raise Rejected('unsupported_expiry')
    try:
        date = datetime.fromisoformat(value.replace('Z','+00:00'))
        if date.tzinfo is None or date.timestamp() < 0: raise ValueError()
        return date.timestamp()
    except ValueError: raise Rejected('unsupported_expiry') from None


def select_claims(source, candidates, judgments, related):
    claims, decisions = [], []
    for i, c in enumerate(candidates):
        decision = {'candidate':i,'result':'discarded'}
        decisions.append(decision)
        if not accepted(judgments[f'support_{i}'], 'supported'):
            decision['reason'] = 'source_support'; continue
        mode = judgments[f'modality_{i}']
        if mode['choice'] not in ('stated','tentative') or not accepted(mode, mode['choice']):
            decision['reason'] = 'modality'; continue
        attribution = judgments[f'attribution_{i}']
        if attribution['choice'] == 'wrong':
            decision['reason'] = 'attribution'; continue
        subject = subject_key(c['subject_name']) if accepted(attribution,'named') else None
        c = dict(c)
        dates = expiry_options(source, c)
        if dates:
            timing = judgments[f'expiry_{i}']
            if timing['choice'].startswith('date_') and accepted(timing, timing['choice']):
                c['expires_at'] = dates[int(timing['choice'].split('_')[1])]
            elif not accepted(timing, 'none'):
                decision['reason'] = 'uncertain_expiry'; continue
            else:
                c['expires_at'] = None
        try: until = expiry(c, source)
        except Rejected:
            decision['reason'] = 'expiry'; continue
        # A past expiry does not establish when the fact first became valid.
        valid_from = None if until is not None and until <= source['captured_at'] else source['captured_at']
        claim = dict(text=c['text'], subject=subject, kind=c['kind'], basis=mode['choice'],
                     passages=c['source_ids'], valid_from=valid_from, valid_until=until,
                     judgment_version=RUBRIC, relation='new')
        relation = judgments[f'relation_{i}']
        label = relation['choice']
        if subject is not None and label.startswith(('duplicate_', 'update_')) and accepted(relation,label):
            target = related[i][int(label.split('_')[1])]
            # Owner filtering is performed in lookup; store repeats subject/kind/time checks atomically.
            if target['subject'] == subject and target['kind'] == c['kind']:
                if label.startswith('duplicate_') and target['basis'] == claim['basis'] and target['valid_until'] == until:
                    claim.update(relation='duplicate', target=target['id'], valid_from=target['valid_from'])
                elif label.startswith('update_') and valid_from is not None and target['valid_from'] is not None and source['captured_at'] >= target['valid_from']:
                    claim.update(relation='supersedes', target=target['id'])
        claims.append(claim)
        decision.update(result='accepted', reason=claim['relation'])
    return claims, decisions


class MemoryWriter:
    def __init__(self, store, models, budget):
        self.store, self.models, self.budget = store, models, budget
        self.lock = asyncio.Lock()

    async def process_next(self, owner):
        async with self.lock:
            job = await asyncio.to_thread(self.store.claim_job, owner)
            if job is None: return None
            try:
                source = await asyncio.to_thread(self.store.source, owner, job['session'])
                if source is None or source['revision'] != job['revision']: raise Rejected('stale_job')
                if not source['passages']:
                    await asyncio.to_thread(self.store.commit_claims, job, [])
                    return {'job':job['id'], 'accepted':0, 'reason':'empty_source'}
                request = extraction_request(source)
                extracted = await metered(self.store, self.budget, job, 'extract', request, self.models.extract)
                candidates = parse_candidates(extracted['data'], source)
                if not candidates:
                    await asyncio.to_thread(self.store.commit_claims, job, [])
                    return {'job':job['id'], 'accepted':0, 'reason':'no_candidates'}
                related = []
                for c in candidates:
                    pool = await asyncio.to_thread(self.store.search, owner, (c['subject_name'] or c['text'])[:1000], limit=50)
                    identity = subject_key(c['subject_name'])
                    related.append([p for p in pool if identity is not None and p['subject'] == identity and p['kind'] == c['kind']][:4])
                request = judgment_request(source, candidates, related)
                judged = await metered(self.store, self.budget, job, 'judge', request, self.models.judge)
                judgments = parse_judgments(judged['data'], request)
                claims, decisions = select_claims(source, candidates, judgments, related)
                await asyncio.to_thread(self.store.commit_claims, job, claims)
                await asyncio.to_thread(self.store.maintain)
                return {'job':job['id'], 'accepted':len(claims), 'decisions':decisions}
            except BaseException as error:
                code = str(error) if isinstance(error, Rejected) else 'learning_interrupted' if isinstance(error, asyncio.CancelledError) else 'learning_failed'
                await asyncio.to_thread(self.store.finish_failed, job, code)
                raise

    async def drain(self, owner, limit=16):
        results = []
        for _ in range(limit):
            result = await self.process_next(owner)
            if result is None: break
            results.append(result)
        return results


class MemoryWorker:
    """One background consumer. Any processing failure halts paid work until operator review."""
    def __init__(self, writer, admission):
        self.writer, self.admission = writer, admission

    async def run(self):
        while True:
            owners = await asyncio.to_thread(self.writer.store.pending_owners, self.admission.active_credentials())
            if not owners:
                await asyncio.sleep(1)
                continue
            for owner in owners:
                try:
                    result = await self.writer.process_next(owner)
                    if result:
                        print(json.dumps({'event':'memory_learned', 'job':result['job'], 'accepted':result['accepted']}), flush=True)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Persisted job holds the sanitized reason. Never log source/provider exception bodies.
                    print(json.dumps({'event':'memory_learning_halted'}), flush=True)
                    return
