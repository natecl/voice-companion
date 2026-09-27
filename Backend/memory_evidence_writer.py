"""Opt-in bounded evidence writer. No hosted enablement or automatic backfill."""
import asyncio
from admission import Rejected
import memory_atomic
import memory_expiry
import memory_candidates
import memory_evidence_chunks
import memory_judgments
import memory_identity_model
import memory_recording_identity
import memory_source_verification
from profile_identity import personal
from memory_models import metered
from memory_source_pipeline import SourceVerifier
from memory_writer import bounded_batches


class EvidenceWriter:
    def __init__(self,store,models,budget,*,luna_identity=True,chunking=False,semantic_boundaries=False,expiry=False,consolidation=False,independent_source_verification=False,source_scoped=False):
        self.source_scoped=source_scoped
        if source_scoped and (semantic_boundaries or consolidation):
            raise ValueError("Source-scoped learning uses deterministic chunks and separate observations")
        self.store,self.models,self.budget=store,models,budget
        self.independent_source_verification=independent_source_verification
        self.lock=asyncio.Lock()
        self.consolidation=consolidation
        self.expiry=expiry
        self.luna_identity=luna_identity
        self.chunking,self.semantic_boundaries=chunking,semantic_boundaries
        if semantic_boundaries and not chunking:raise ValueError("Semantic boundaries require chunking")

    async def process_next(self,owner):
        async with self.lock:
            job=await asyncio.to_thread(self.store.claim_job,owner)
            if job is None:return None
            try:
                source=await asyncio.to_thread(self.store.source,owner,job['session'])
                if source is None or source['revision']!=job['revision']:raise Rejected('stale_job')
                if not source['passages']:
                    await asyncio.to_thread(memory_atomic.commit,self.store,job,[])
                    return dict(job=job['id'],accepted=0,claims=[],decisions=[])
                chunks=await asyncio.to_thread(self.store.chunk_plan,job,planner=memory_evidence_chunks) if self.chunking else []
                if chunks and self.semantic_boundaries and chunks[0]['strategy']!='jev_boundary_overlap':
                    async def evaluate(request):
                        return await metered(self.store,self.budget,job,'boundary:evidence:v1',request,self.models.judge)
                    refined=await memory_evidence_chunks.semantic_plan(source,evaluate)
                    await asyncio.to_thread(self.store.replace_chunk_plan,job,refined,planner=memory_evidence_chunks)
                    chunks=[dict(c,claims=None) for c in refined]
                if chunks:
                    parts=[]
                    for chunk in chunks:
                        part=chunk['claims']
                        if part is not None:
                            independent=self.independent_source_verification and self.luna_identity and not personal(chunk['source'])
                            expected=memory_source_verification.VERSION if independent else memory_judgments.VERSION
                            if any(entry['checks']['support'].get('rubric')!=expected for entry in part):
                                raise Rejected('verification_contract_changed')
                        if part is None:
                            part=await self.extract_verified(job,chunk['source'],chunk['id']+':')
                            mapped=[]
                            for entry in part:
                                proposal=memory_evidence_chunks.original_proposal(source,chunk,entry['proposal'])
                                if proposal is not None:mapped.append(dict(entry,proposal=proposal))
                            part=mapped
                            await asyncio.to_thread(self.store.complete_chunk,job,chunk['id'],part)
                        parts.extend(part)
                    parts=memory_evidence_chunks.unique(parts)
                else:
                    parts=await self.extract_verified(job,source)
                items=[];audit=[]
                for index,part in enumerate(parts):
                    p,checks=part['proposal'],part['checks']
                    if not all(checks[a]['accepted'] and checks[a]['label']=='supported' for a in ('support','modality')):
                        audit.append(dict(candidate=index,result='rejected',checks=checks));continue
                    if not (checks['time']['accepted'] and checks['time']['label']=='supported'):
                        # Preserve independently supported undated facts without promoting
                        # an unverified temporal classification to current knowledge.
                        # Explicit date expressions still require their existing verification.
                        if (checks['time'].get('rubric')!=memory_source_verification.VERSION
                                or p['time']['expression'] is not None):
                            audit.append(dict(candidate=index,result='rejected',checks=checks));continue
                        checks=dict(checks,time=dict(checks['time'],
                            disposition='retain_time_unresolved',proposed_time=dict(p['time'])))
                        p=dict(p,time=dict(status='uncertain',expression=None))
                    pool=await asyncio.to_thread(memory_candidates.related,self.store,owner,p)
                    pool['candidates'].extend(self.pending(source,items,p))
                    old=pool['candidates']
                    identity={};relations={}
                    pairs={f'prior_{i}':dict(incoming=dict(source=source,proposal=p),previous=c) for i,c in enumerate(old)}
                    if pairs:
                        for role in (('relation','identity') if self.source_scoped else ('identity','relation')):
                            entries=list(pairs.items())
                            luna=role=='identity' and self.luna_identity
                            build=(memory_identity_model.contextual_request if (self.consolidation or self.source_scoped) else memory_identity_model.request) if luna else lambda pairs:memory_judgments.pair_questions(pairs,role=role)
                            for begin,end,request in bounded_batches(entries,lambda a,b:build(dict(entries[a:b])),'memory_identity_too_large' if luna else 'memory_judgment_too_large'):
                                response=await metered(self.store,self.budget,job,f'evidence-{role}:{index}:{begin}',request,self.models.extract if luna else self.models.judge)
                                parsed=memory_identity_model.decisions(response['data'],request) if luna else memory_judgments.decisions(response['data'],request,role)
                                if role=='identity':identity.update(parsed)
                                else:relations.update(parsed)
                            if self.source_scoped and role=='relation':
                                # An independently accepted addition is not a replacement
                                # target. Do not build cross-source identity links to it.
                                # Ambiguous/conflicting targets and pool truncation stay
                                # conservative; existing atomic correction guards remain.
                                kept=[(key,prior) for key,prior in zip(pairs,old)
                                      if not (relations[key]['accepted'] and relations[key]['label']=='addition')]
                                relations={f'prior_{i}':relations[key] for i,(key,_) in enumerate(kept)}
                                old=[prior for _,prior in kept]
                                pool=dict(pool,candidates=old)
                                pairs={f'prior_{i}':dict(incoming=dict(source=source,proposal=p),previous=c) for i,c in enumerate(old)}
                    applicability={}
                    temporal_pairs={key:pair for key,pair in pairs.items()
                        if identity[key]['accepted'] and identity[key]['label']=='same'
                        and relations[key]['label']=='replacement'}
                    if temporal_pairs:
                        entries=list(temporal_pairs.items())
                        for begin,end,request in bounded_batches(entries,lambda a,b:memory_judgments.pair_questions(dict(entries[a:b]),role='applicability'),'memory_judgment_too_large'):
                            response=await metered(self.store,self.budget,job,f'evidence-applicability:{index}:{begin}',request,self.models.judge)
                            applicability.update(memory_judgments.decisions(response['data'],request,'applicability'))
                    item=self.select(p,pool,checks,identity,relations,applicability)
                    if self.expiry:
                        requested=memory_expiry.request(source,p)
                        if requested is not None:
                            response=await metered(self.store,self.budget,job,f'expiry:{memory_expiry.VERSION}:{index}',requested,self.models.judge)
                            item['expiry']=memory_expiry.decision(response['data'],requested)
                    if self.consolidation and item['action']=='unresolved':
                        duplicates=[c for key,c in zip(pairs,old) if identity[key]['accepted'] and identity[key]['label']=='same'
                            and relations[key]['accepted'] and relations[key]['label']=='duplicate']
                        if (len(old)==len(duplicates)==1 and not pool['truncated'] and item['identity_verified']
                                and item.get('anchor') is not None and 'pending_index' not in duplicates[0]
                                and not item['possible_targets'] and not item['possible_target_items']
                                and p['kind'] in ('fact','preference') and p['basis']=='stated'
                                and p['change']['kind'] in ('none','addition')
                                and p['time']==dict(status='current',expression=None)):
                            prior=duplicates[0]
                            previous=prior.get('proposal')
                            if (previous and previous['time']==p['time'] and prior['kind']==p['kind']
                                    and prior['basis']=='stated' and prior['state']=='active'
                                    and prior.get('valid_until') is None and prior['valid_from'] is not None
                                    and not any(e['ref']['session']==source['session_id'] for e in prior['evidence'])):
                                item.update(action='duplicate',target=prior['id'])
                    item['_entity']=item.get('_entity',f'batch_{len(items)}')
                    items.append(item);audit.append(dict(candidate=index,result=item['action']))
                ids=await asyncio.to_thread(memory_atomic.commit,self.store,job,items)
                return dict(job=job['id'],accepted=len(ids),claims=ids,decisions=audit)
            except BaseException as error:
                code=str(error) if isinstance(error,Rejected) else 'learning_interrupted' if isinstance(error,asyncio.CancelledError) else 'learning_failed'
                await asyncio.to_thread(self.store.finish_failed,job,code)
                raise

    async def extract_verified(self,job,source,prefix=''):
        verifier=SourceVerifier(self.store,self.models,self.budget,
            luna_identity=self.luna_identity,
            independent_source_verification=self.independent_source_verification)
        return await verifier.extract_verified(job,source,prefix)

    @staticmethod
    def select(proposal,pool,checks,identity,relations,applicability=None):
        applicability=applicability or {}
        attributed=checks['subject']['accepted'] and checks['subject']['label']==proposal['scope'] and proposal['scope']!='unresolved'
        rubric=memory_judgments.VERSION
        if checks['support'].get('rubric')==memory_source_verification.VERSION:rubric+='+'+memory_source_verification.VERSION
        if checks['subject'].get('rubric')==memory_recording_identity.VERSION:rubric+='+'+memory_recording_identity.VERSION
        if any(d.get('rubric')==memory_identity_model.VERSION for d in identity.values()):rubric+='+'+memory_identity_model.VERSION
        item=dict(proposal=proposal,action='new',rubric=rubric,
                  identity_verified=attributed,profile_verified=attributed,possible_targets=[],possible_target_items=[],
                  judgments=dict(source=checks,identity=identity,relation=relations,applicability=applicability),
                  snapshots={c['id']:c['evidence_token'] for c in pool['candidates'] if 'pending_index' not in c})
        # No extracted hint or absence from bounded lexical retrieval authorizes replacement.
        unclear=pool['truncated'];same=[];replacements=[]
        for i,prior in enumerate(pool['candidates']):
            key=f'prior_{i}';ident=identity[key];relation=relations[key]
            if ident['accepted'] and ident['label']=='different':continue
            if not (ident['accepted'] and ident['label']=='same'):
                unclear=True;continue
            if prior['identity_status']!='established' or not prior['identity_links']:
                unclear=True;continue # Legacy metadata is not silently promoted.
            descriptor=(prior.get('proposal') or {}).get('mention')
            if descriptor and (descriptor['relationship']!=proposal['mention']['relationship']
                    or set(descriptor['qualifiers'] or [])!=set(proposal['mention']['qualifiers'])):
                # The identity ledger cannot yet represent cross-role aliases. Retain the fact
                # unresolved rather than fail the whole source or bypass its link guard.
                unclear=True;continue
            same.append(prior)
            if relation['label']=='replacement':
                # Classification routes a candidate; a separate applicability verdict authorizes mutation.
                temporal=applicability.get(key,{})
                if (proposal['time']['status']!='future'
                        and temporal.get('label') not in ('historical','future')):
                    if 'pending_index' in prior:item['possible_target_items'].append(prior['pending_index'])
                    else:item['possible_targets'].append(prior['id'])
                current_change=(temporal.get('accepted') and temporal.get('label')=='current_change'
                    and proposal['time']['status'] in ('past','current') and proposal['basis']=='stated')
                if (not current_change or prior['state'] not in ('active','expired')
                        or prior['valid_from'] is None):unclear=True
                else:
                    replacements.append(prior)
                    item['current_change']=temporal
            elif not relation['accepted'] or relation['label'] in ('conflict','uncertain','duplicate'):
                unclear=True # Consolidation is a later atomic operation, not a second current fact.
        entities={c['entity_id'] for c in same}
        if len(entities)>1 or len(replacements)>1:unclear=True
        if same and len(entities)==1 and proposal['scope']!='unresolved' and (attributed or (proposal['scope']!='author' and checks['subject']['label']!='wrong')):
            item['identity_verified']=True
            anchor=(replacements or same)[0]
            item.update(anchor_refs=[e['ref'] for e in anchor['evidence']],_entity=anchor['entity_id'])
            if 'pending_index' in anchor:item['anchor_item']=anchor['pending_index']
            else:item['anchor']=anchor['identity_links'][0]['id']
        if replacements and not unclear and item['identity_verified']:
            item['action']='correct'
            target=replacements[0]
            if 'pending_index' in target:item['target_item']=target['pending_index']
            else:item['target']=target['id']
        elif unclear or (not replacements and proposal['change']['kind'] in ('correction','uncertain')):
            item['action']='unresolved'
        if not item['identity_verified'] or proposal['time']['status']=='uncertain':item['action']='unresolved'
        if item['action']!='correct':item.pop('current_change',None)
        if item['action']!='unresolved' or checks['subject']['label']=='wrong' or (proposal['scope']=='author' and not attributed):
            item['possible_targets']=[]
            item['possible_target_items']=[]
        return item

    @staticmethod
    def pending(source,items,proposal):
        result=[]
        query=memory_candidates.terms(proposal['text']+' '+(proposal['change']['previous_text'] or ''))
        replaced={item['target_item'] for item in items if item['action']=='correct' and 'target_item' in item}
        for i,item in enumerate(items):
            if i in replaced:continue
            p=item['proposal']
            if not query & memory_candidates.terms(p['text']):continue
            identified=item.get('identity_verified',False) and p['scope']!='unresolved'
            refs=[dict(session=source['session_id'],revision=source['revision'],passage=r['passage']) for r in p['spans']]
            passages={r['id']:r for r in source['passages']}
            result.append(dict(id=f'batch_{i}',pending_index=i,proposal=p,text=p['text'],kind=p['kind'],basis=p['basis'],
                state='active' if item['action'] in ('new','correct') and (p['time']['status']=='current' or item.get('current_change')) else 'unresolved',
                valid_from=source['captured_at'] if p['time']['status']=='current' or item.get('current_change') else None,
                identity_status='established' if identified else 'unresolved',entity_id=item['_entity'] if identified else None,
                identity_links=[dict(id=f'batch_{i}')] if identified else [],
                evidence=[dict(ref=r,passage=passages[r['passage']],origin=source.get('origin','recording'),captured_at=source['captured_at']) for r in refs]))
        return result
