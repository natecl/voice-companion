"""Opt-in bounded evidence writer. No hosted enablement or automatic backfill."""
import asyncio
from admission import Rejected
import memory_atomic
import memory_candidates
import memory_evidence
import memory_judgments
from memory_models import metered
from memory_writer import bounded_batches


class EvidenceWriter:
    def __init__(self,store,models,budget):
        self.store,self.models,self.budget=store,models,budget
        self.lock=asyncio.Lock()

    async def process_next(self,owner):
        async with self.lock:
            job=await asyncio.to_thread(self.store.claim_job,owner)
            if job is None:return None
            try:
                source=await asyncio.to_thread(self.store.source,owner,job['session'])
                if not source['passages']:
                    await asyncio.to_thread(memory_atomic.commit,self.store,job,[])
                    return dict(job=job['id'],accepted=0,claims=[],decisions=[])
                request=memory_evidence.extraction_request(source)
                response=await metered(self.store,self.budget,job,'evidence-extract:v2',request,self.models.extract)
                proposals=memory_evidence.parse(response['data'],source)
                verified={}
                batches=bounded_batches(proposals,lambda a,b:memory_judgments.verify_proposals(source,proposals[a:b]),'memory_judgment_too_large')
                for start,end,request in batches:
                    response=await metered(self.store,self.budget,job,f'evidence-support:{start}',request,self.models.judge)
                    for key,value in memory_judgments.decisions(response['data'],request).items():
                        aspect,index=key.rsplit('_',1);verified[f'{aspect}_{start+int(index)}']=value
                items=[];audit=[]
                for index,p in enumerate(proposals):
                    checks={aspect:verified[f'{aspect}_{index}'] for aspect in ('support','subject','modality','time')}
                    if not all(checks[a]['accepted'] and checks[a]['label']=='supported' for a in ('support','modality','time')):
                        audit.append(dict(candidate=index,result='rejected',checks=checks));continue
                    pool=await asyncio.to_thread(memory_candidates.related,self.store,owner,p)
                    pool['candidates'].extend(self.pending(source,items,p))
                    old=pool['candidates']
                    identity={};relations={}
                    pairs={f'prior_{i}':dict(incoming=dict(source=source,proposal=p),previous=c) for i,c in enumerate(old)}
                    if pairs:
                        for role in ('identity','relation'):
                            entries=list(pairs.items())
                            for begin,end,request in bounded_batches(entries,lambda a,b:memory_judgments.pair_questions(dict(entries[a:b]),role=role),'memory_judgment_too_large'):
                                response=await metered(self.store,self.budget,job,f'evidence-{role}:{index}:{begin}',request,self.models.judge)
                                parsed=memory_judgments.decisions(response['data'],request,role)
                                if role=='identity':identity.update(parsed)
                                else:relations.update(parsed)
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
                    item['_entity']=item.get('_entity',f'batch_{len(items)}')
                    items.append(item);audit.append(dict(candidate=index,result=item['action']))
                ids=await asyncio.to_thread(memory_atomic.commit,self.store,job,items)
                return dict(job=job['id'],accepted=len(ids),claims=ids,decisions=audit)
            except BaseException as error:
                code=str(error) if isinstance(error,Rejected) else 'learning_interrupted' if isinstance(error,asyncio.CancelledError) else 'learning_failed'
                await asyncio.to_thread(self.store.finish_failed,job,code)
                raise

    @staticmethod
    def select(proposal,pool,checks,identity,relations,applicability=None):
        applicability=applicability or {}
        attributed=checks['subject']['accepted'] and checks['subject']['label']==proposal['scope'] and proposal['scope']!='unresolved'
        item=dict(proposal=proposal,action='new',rubric=memory_judgments.VERSION,
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
        if not item['identity_verified']:item['action']='unresolved'
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
                evidence=[dict(ref=r,passage=passages[r['passage']],origin=source.get('origin','recording')) for r in refs]))
        return result
