"""Isolated candidate evaluation; does not alter production verification or user data."""
import argparse,asyncio,copy,json,os
from pathlib import Path
from memory_models import MemoryModels,JEV,fingerprint
from memory_judgments import verify_proposals,decisions
from profile_budget import ProfileBudget


def candidate(source,proposals,*,context_only=False):
    req=verify_proposals(source,proposals,include_subject=False)
    # Keep intervening text: selected quotes alone can conceal a topic change.
    req['state']['source']=copy.deepcopy(source)
    for i,p in enumerate(proposals):
        for aspect in ('support','modality','time'):
            q=req['questions'][f'{aspect}_{i}']['instructions']
            q['context_rule']='Read the ordered original passages in state.source as context. Transcript segmentation and punctuation can split an utterance. Missing speaker labels do not prove a speaker change; neither do labels prove identity. Do not bridge an explicit topic or speaker change, competing subjects or quotations by guessing. The claim must remain supported by its cited excerpts in this context. A claim is a proposal to check, never evidence.'
        if context_only:continue
        req['questions'][f'support_{i}']['instructions']['question']='Does the cited evidence, read in its original conversational context, express the proposed claim? Check what was reported, not whether it is independently true in the world. Preserve the subject, negation and qualifications. Do not demand a complete sentence within each transcript segment. If subject continuity is genuinely ambiguous, choose uncertain.'
        req['questions'][f'modality_{i}']['instructions']['question']='Does the proposed basis match how the speaker presents the claim? Stated means an unqualified assertion, including a preference; tentative means explicitly uncertain. A hypothetical, quotation about someone else, or advice must not become an unqualified assertion about the proposed subject. Speaker identity and external truth are separate questions.'
        req['questions'][f'time_{i}']['instructions']['question']='Does the proposed temporal annotation match the report at capture time? Current means reported as an ongoing state then, not verified true today. A plain present-tense preference or ongoing property with no time qualification supports current with expression null. Preserve explicit historical, future, conditional and uncertain qualifications. Do not invent dates or infer completion.'
    if len(json.dumps(req).encode())>28000:raise ValueError('Candidate too large')
    return req


def cases():
    original=json.loads((Path(__import__('memory_judgments').__file__).parent/'fixtures/subject-continuity/calls.json').read_text())
    source=json.loads(original[0]['request']['input']);proposals=copy.deepcopy(original[0]['response']['data']['memories'])
    proposals[1]['mention']['speaker_label']=None
    result=[dict(name='project',source=source,proposals=proposals,expected=[True,True])]
    specs=[
      ('person',['Maya.','Enjoys swimming.'],'Maya enjoys swimming.','Maya',True,'current'),
      ('pet',['Our dog Pepper.','Prefers walks in the evening.'],'Pepper prefers evening walks.','Pepper',True,'current'),
      ('family',['My sister Lena.','Now works nights instead of mornings.'],'Lena now works nights.','Lena',True,'current'),
      ('competing',['Maya and Lena.','One of them enjoys swimming; I forget which.'],'Maya enjoys swimming.','Maya',False,'current'),
      ('quotation',['Maya was discussed earlier.','An unrelated speaker said, "I enjoy swimming."'],'Maya enjoys swimming.','Maya',False,'current'),
      ('historical',['Pepper.','Used to prefer evening walks, but no longer does.'],'Pepper prefers evening walks.','Pepper',False,'current'),
      ('hypothetical',['Lena.','If she worked nights, she might prefer morning appointments.'],'Lena prefers morning appointments.','Lena',False,'current')]
    for name,texts,claim,subject,expected,status in specs:
        s=copy.deepcopy(source);s['session_id']='preference-'+name
        s['passages']=[dict(id=f'p{i+1}',start=float(i*5),duration=3.,text=t,speakers=[] if i==0 else [0]) for i,t in enumerate(texts)]
        p=dict(text=claim,kind='preference',basis='stated',scope='named',mention=dict(name=subject,relationship=None,qualifiers=[],speaker_label=None),evidence=[dict(passage=r['id'],quote=r['text']) for r in s['passages']],time=dict(status=status,expression=None),change=dict(kind='none',previous_text=None))
        result.append(dict(name=name,source=s,proposals=[p],expected=[expected]))
    return result


def controls():
    result=[]
    for original in cases()[:2]:
        c=copy.deepcopy(original);c['proposals']=c['proposals'][:1];c['expected']=[True]
        # Separate synthetic controls; never rewrite original recordings as facts.
        text=c['proposals'][0]['text']
        c['source']['passages']=[dict(id='p1',start=0.,duration=3.,text=text,speakers=[0])]
        c['proposals'][0]['evidence']=[dict(passage='p1',quote=text)]
        result.append(c)
    return result


async def run(out,budget_path,control=False):
    out.mkdir(parents=True,exist_ok=False)
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True,include_rollout_allowance=True)
    models=MemoryModels('',os.environ['TYPESAFE_API_KEY']);results=[]
    suite=cases();runs=[('context-only',suite[0],True)]+[('candidate',c,False) for c in suite]
    if control:runs=[('control',c,False) for c in controls()]
    assert len(runs)==(2 if control else 9)
    for variant,c,context_only in runs:
        req=candidate(c['source'],c['proposals'],context_only=context_only)
        key=out.name+':'+c['name']+':'+variant+':'+fingerprint(req)
        budget.reserve(key,JEV)
        try:response=await models.judge(req)
        except BaseException:budget.finish(key);raise
        budget.finish(key,response.get('usage'))
        verdicts=decisions(response['data'],req)
        accepted=[all(verdicts[f'{a}_{i}']['accepted'] for a in ('support','modality','time')) for i in range(len(c['proposals']))]
        results.append(dict(case=c,variant=variant,request=req,response=response,decisions=verdicts,accepted=accepted,passed=accepted==c['expected']))
        (out/'results.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(dict(case=c['name'],variant=variant,accepted=accepted,expected=c['expected'],probabilities={k:v['probabilities'] for k,v in verdicts.items()})),flush=True)
    print(json.dumps(dict(budget=budget.report(),candidate_passed=all(r['passed'] for r in results if r['variant']!='context-only'))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--budget',type=Path,required=True);p.add_argument('--controls',action='store_true');a=p.parse_args();asyncio.run(run(a.out,a.budget,a.controls))
