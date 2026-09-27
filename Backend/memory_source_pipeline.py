"""Source-local extraction and verification, independent of memory reconciliation.

Shared by learning pipelines; does not search prior claims or mutate their state.
Provider requests, cache stages, attribution checks and budgets stay unchanged.
"""
import memory_evidence
import memory_judgments
import memory_recording_identity
import memory_source_verification
from memory_models import metered
from memory_writer import bounded_batches
from profile_identity import personal


class SourceVerifier:
    def __init__(self, store, models, budget, *, luna_identity=True,
                 independent_source_verification=False):
        self.store, self.models, self.budget = store, models, budget
        self.luna_identity = luna_identity
        self.independent_source_verification = independent_source_verification

    async def extract_verified(self,job,source,prefix=''):
        request=memory_evidence.extraction_request(source)
        response=await metered(self.store,self.budget,job,prefix+'evidence-extract:v2',request,self.models.extract)
        proposals=memory_evidence.parse_recording_extraction(response['data'],source)
        verified={}
        recording_identity=self.luna_identity and not personal(source)
        if self.independent_source_verification and recording_identity:
            def build_support(a,b):
                cases=memory_source_verification.support_cases(source,proposals[a:b])
                return memory_source_verification.support_request(cases)[0]
            for start,end,request in bounded_batches(proposals,build_support,'source_verification_too_large'):
                response=await metered(self.store,self.budget,job,
                    prefix+f'{memory_source_verification.VERSION}:support:{start}',request,self.models.extract)
                proposals[start:end]=memory_source_verification.retain_support_evidence(response['data'],source,proposals[start:end])
                for key,value in memory_source_verification.support_decisions(response['data'],source,proposals[start:end]).items():
                    verified[f'support_{start+int(key.rsplit("_",1)[1])}']=value
            for start,end,request in bounded_batches(proposals,
                    lambda a,b:memory_source_verification.metadata_request(source,proposals[a:b]),'memory_judgment_too_large'):
                response=await metered(self.store,self.budget,job,
                    prefix+f'{memory_source_verification.VERSION}:metadata:{start}',request,self.models.judge)
                for key,value in memory_source_verification.metadata_decisions(response['data'],request,proposals[start:end]).items():
                    aspect,index=key.rsplit('_',1);verified[f'{aspect}_{start+int(index)}']=value
        else:
            batches=bounded_batches(proposals,lambda a,b:memory_judgments.verify_proposals(source,proposals[a:b],include_subject=not recording_identity),'memory_judgment_too_large')
            for start,end,request in batches:
                response=await metered(self.store,self.budget,job,prefix+f'evidence-support:{start}',request,self.models.judge)
                for key,value in memory_judgments.decisions(response['data'],request).items():
                    aspect,index=key.rsplit('_',1);verified[f'{aspect}_{start+int(index)}']=value
        if recording_identity:
            for start,end,request in bounded_batches(proposals,lambda a,b:memory_recording_identity.request(proposals[a:b]),'memory_identity_too_large'):
                response=await metered(self.store,self.budget,job,prefix+f'recording-identity:{start}',request,self.models.extract)
                for key,value in memory_recording_identity.decisions(response['data'],request).items():
                    verified[f'subject_{start+int(key.rsplit("_",1)[1])}']=value
        return [dict(proposal=p,checks={aspect:verified[f'{aspect}_{i}'] for aspect in ('support','subject','modality','time')})
                for i,p in enumerate(proposals)]

