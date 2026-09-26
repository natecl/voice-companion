import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from test_memory import source
from test_memory_learning import answers


def proposal(text,change='none',qualifiers=None):
    return dict(text=text,kind='preference',basis='stated',scope='related_to_author',
        mention=dict(name='Maya',relationship='daughter',qualifiers=qualifiers or [],speaker_label=None),
        evidence=[dict(passage='p1',quote=text)],time=dict(status='current',expression=None),
        change=dict(kind=change,previous_text='Maya enjoys swimming.' if change=='correction' else None))


class EvidenceWriterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite',personal_learning=True,clock=lambda:300.)
        self.owner=self.store.owner_for('owner');outer=self
        self.outputs=[];self.calls=[]
        class Models:
            async def extract(self,request):
                outer.calls.append('extract');return dict(data=dict(memories=outer.outputs),usage={})
            async def judge(self,request):
                outer.calls.append('judge');labels={}
                for key,q in request['questions'].items():
                    if 'author' in q['criteria']:labels[key]=q['instructions']['aspect_value']['scope']
                    elif 'supported' in q['criteria']:labels[key]='supported'
                    elif 'current_change' in q['criteria']:labels[key]='current_change'
                    else:
                        pair=request['state']['pairs'][key]
                        incoming=pair['incoming']
                        if 'same' in q['criteria']:
                            labels[key]='different' if 'other' in ' '.join(incoming['excerpts']) else 'same'
                        else:labels[key]='replacement' if 'instead of' in incoming['claim'] else 'addition'
                return dict(data=answers(request,labels),usage={})
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        self.writer=EvidenceWriter(self.store,Models(),Budget(),luna_identity=False)

    async def run_source(self,session,proposals):
        self.outputs=proposals
        data=source(session,text=' '.join(p['text'] for p in proposals));data['origin']='personal_text'
        self.store.put_source(self.owner,data)
        return await self.writer.process_next(self.owner)

    async def test_full_writer_correction_and_distinct_person(self):
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        await self.run_source('two',[proposal('My daughter Maya now enjoys tennis instead of swimming.','correction')])
        await self.run_source('three',[proposal('My other daughter Maya enjoys painting.',qualifiers=['other'])])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','active','superseded'])
        first=next(r for r in rows if r['state']=='superseded')
        corrected=next(r for r in rows if r['replaces']==first['id'])
        other=next(r for r in rows if 'other' in r['text'])
        self.assertEqual(first['entity_id'],corrected['entity_id'])
        self.assertNotEqual(other['entity_id'],corrected['entity_id'])

    async def test_same_source_correction_is_atomic_and_uses_pending_evidence(self):
        result=await self.run_source('one',[proposal('My daughter Maya enjoys swimming.'),
            proposal('My daughter Maya now enjoys tennis instead of swimming.','correction')])
        self.assertEqual(result['accepted'],2)
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertEqual(len(self.store.search(self.owner,historical=True)),2)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0],1)

    async def test_uncertain_identity_preserves_unresolved_without_overwrite(self):
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        normal=self.writer.models.judge
        async def uncertain(request):
            if any('same' in q['criteria'] for q in request['questions'].values()):
                return dict(data=answers(request,{key:'uncertain' for key in request['questions']}),usage={})
            return await normal(request)
        self.writer.models.judge=uncertain
        await self.run_source('two',[proposal('My daughter Maya now enjoys tennis instead of swimming.','correction')])
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)

    async def test_source_deleted_after_judgment_never_commits(self):
        normal=self.writer.models.judge
        async def deleted(request):
            response=await normal(request)
            self.store.delete_source(self.owner,'one')
            return response
        self.writer.models.judge=deleted
        with self.assertRaisesRegex(Rejected,'stale_job'):
            await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        self.assertEqual(self.store.search(self.owner),[])

    async def test_same_source_chain_does_not_correct_already_replaced_fact_twice(self):
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.'),
            proposal('My daughter Maya now enjoys tennis instead of swimming.','correction'),
            proposal('My daughter Maya now enjoys painting instead of tennis.','correction')])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sum(r['state']=='superseded' for r in rows),2)
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertIn('painting',self.store.search(self.owner)[0]['text'])

    async def test_supported_fact_survives_uncertain_attribution_without_profile_or_identity(self):
        normal=self.writer.models.judge
        async def weak(request):
            result=await normal(request)
            if 'subject_0' in request['questions']:
                a=result['data']['answers']['subject_0']
                a['probabilities']={k:(.89 if k=='related_to_author' else .11 if k=='named' else 0.) for k in a['probabilities']}
            return result
        self.writer.models.judge=weak
        result=await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        self.assertEqual(result['accepted'],1)
        rows=self.store.search(self.owner,unresolved_only=True)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['identity_status'],'unresolved')
        with self.store.connect() as db:
            row=db.execute('SELECT subject,profile_link FROM claim').fetchone()
            self.assertIsNone(row['subject']);self.assertFalse(row['profile_link'])
            self.assertEqual(db.execute('SELECT count(*) FROM memory_identity_link').fetchone()[0],0)

    async def test_completed_change_requires_independent_current_applicability(self):
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        normal=self.writer.models.judge
        async def temporal(request):
            criteria=next(iter(request['questions'].values()))['criteria']
            if 'current_change' in criteria:
                return dict(data=answers(request,{key:'current_change' for key in request['questions']}),usage={})
            if 'replacement' in criteria:
                data=answers(request,{key:'replacement' for key in request['questions']})
                for answer in data['answers'].values():
                    answer['probabilities']={k:(.92 if k=='replacement' else .08 if k=='uncertain' else 0.) for k in answer['probabilities']}
                return dict(data=data,usage={})
            result=await normal(request)
            if 'subject_0' in request['questions']:
                a=result['data']['answers']['subject_0']
                a['probabilities']={k:(.89 if k=='related_to_author' else .11 if k=='named' else 0.) for k in a['probabilities']}
            return result
        self.writer.models.judge=temporal
        p=proposal('My daughter Maya switched from swimming to tennis.')
        p['kind']='event';p['time']['status']='past'
        await self.run_source('two',[p])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        current=next(r for r in rows if r['state']=='active')
        self.assertEqual(current['kind'],'event') # Never rewrite the source claim as an invented present-tense assertion.
        self.assertIn('switched',current['text'])
        with self.store.connect() as db:
            self.assertFalse(db.execute('SELECT profile_link FROM claim WHERE id=?',(current['id'],)).fetchone()[0])
        self.store.delete_source(self.owner,'one')
        self.assertEqual(self.store.search(self.owner),[])
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)

    async def test_historical_future_and_uncertain_changes_do_not_replace_current_fact(self):
        for label,status in [('historical','past'),('future','future'),('uncertain','past'),('current_change','future')]:
            with self.subTest(label=label):
                self.setUp()
                await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
                normal=self.writer.models.judge
                async def temporal(request):
                    criteria=next(iter(request['questions'].values()))['criteria']
                    if 'current_change' in criteria:
                        return dict(data=answers(request,{key:label for key in request['questions']}),usage={})
                    if 'replacement' in criteria:
                        return dict(data=answers(request,{key:'replacement' for key in request['questions']}),usage={})
                    return await normal(request)
                self.writer.models.judge=temporal
                p=proposal('My daughter Maya switched temporarily to tennis.')
                p['kind']='event';p['time']['status']=status
                await self.run_source('two',[p])
                if label=='uncertain':
                    self.assertEqual(self.store.search(self.owner),[])
                    unresolved=self.store.search(self.owner,unresolved_only=True)
                    self.assertEqual(len(unresolved),2)
                    old=next(r for r in unresolved if 'swimming' in r['text'])
                    self.assertEqual(old['reason'],'pending_supported_change')
                    self.assertEqual(old['stored_state'],'active')
                    self.assertEqual(len({r['entity_id'] for r in unresolved}),1)
                    self.assertTrue(old['current_disputed_by'])
                    raw=self.store.evidence(self.owner,'one')
                    self.assertEqual(raw['passages'][0]['claims'][0]['state'],'unresolved')
                    self.assertEqual(self.store.profile(self.owner),[])
                else:
                    self.assertEqual(len(self.store.search(self.owner)),1)
                    self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)
                    self.assertIn('swimming',self.store.search(self.owner)[0]['text'])

    async def test_correction_chain_can_cross_event_and_current_fact_wording(self):
        normal=self.writer.models.judge
        async def temporal(request):
            criteria=next(iter(request['questions'].values()))['criteria']
            if 'current_change' in criteria:
                return dict(data=answers(request,{key:'current_change' for key in request['questions']}),usage={})
            if 'replacement' in criteria:
                return dict(data=answers(request,{key:'replacement' for key in request['questions']}),usage={})
            return await normal(request)
        self.writer.models.judge=temporal
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        p=proposal('My daughter Maya switched to tennis.');p['kind']='event';p['time']['status']='past'
        await self.run_source('two',[p])
        await self.run_source('three',[proposal('My daughter Maya now enjoys painting instead of tennis.','correction')])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded','superseded'])
        self.assertIn('painting',self.store.search(self.owner)[0]['text'])
        self.store.delete_source(self.owner,'two')
        self.assertEqual(self.store.search(self.owner),[])

    async def test_same_source_temporal_correction_chain_uses_established_pending_state(self):
        normal=self.writer.models.judge
        async def temporal(request):
            criteria=next(iter(request['questions'].values()))['criteria']
            if 'current_change' in criteria:
                return dict(data=answers(request,{key:'current_change' for key in request['questions']}),usage={})
            if 'replacement' in criteria:
                return dict(data=answers(request,{key:'replacement' for key in request['questions']}),usage={})
            return await normal(request)
        self.writer.models.judge=temporal
        event=proposal('My daughter Maya switched to tennis.');event['kind']='event';event['time']['status']='past'
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.'),event,
            proposal('My daughter Maya now enjoys painting instead of tennis.','correction')])
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertIn('painting',self.store.search(self.owner)[0]['text'])
        self.assertEqual(len(self.store.search(self.owner,historical=True)),3)

    async def test_uncertain_same_source_change_qualifies_prior_in_current_reads(self):
        normal=self.writer.models.judge
        async def temporal(request):
            criteria=next(iter(request['questions'].values()))['criteria']
            if 'current_change' in criteria:
                return dict(data=answers(request,{key:'uncertain' for key in request['questions']}),usage={})
            if 'replacement' in criteria:
                return dict(data=answers(request,{key:'replacement' for key in request['questions']}),usage={})
            return await normal(request)
        self.writer.models.judge=temporal
        event=proposal('My daughter Maya switched to tennis.');event['kind']='event';event['time']['status']='past'
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.'),event])
        self.assertEqual(self.store.search(self.owner),[])
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM claim_relation_proposal').fetchone()[0],1)

    async def test_writer_replays_exact_requests_preserving_remaining_identity_abstention(self):
        directory=Path(__file__).parent/'fixtures/memory_evidence_writer/household-v10-failed'
        recorded=json.loads((directory/'provider-calls.json').read_text())
        index=0
        async def consume(role,request):
            nonlocal index
            expected=recorded[index];index+=1
            self.assertEqual(expected['role'],role)
            self.assertEqual(request,expected['request'])
            return copy.deepcopy(expected['response'])
        async def extract(request):return await consume('extract',request)
        async def judge(request):return await consume('judge',request)
        self.writer.models.extract=extract;self.writer.models.judge=judge
        for name in ['first','correction','distinct']:
            artifact=json.loads((directory/(name+'.json')).read_text())
            self.store.put_source(self.owner,artifact['source'])
            await self.writer.process_next(self.owner)
        self.assertEqual(index,len(recorded))
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        unresolved=self.store.search(self.owner,unresolved_only=True)
        self.assertEqual(len(unresolved),1)
        self.assertIn('citrus',unresolved[0]['text'])
        self.assertNotIn(unresolved[0]['entity_id'],{r['entity_id'] for r in rows})

    async def test_luna_identity_writer_replays_household_flow(self):
        await self.replay_luna_flow('luna-low-household')

    async def test_luna_identity_writer_replays_routine_flow(self):
        await self.replay_luna_flow('luna-low-routine')

    async def replay_luna_flow(self,folder):
        directory=Path(__file__).parent/'fixtures/memory_evidence_writer'/folder
        recorded=json.loads((directory/'provider-calls.json').read_text())
        index=0
        async def consume(role,request):
            nonlocal index
            expected=recorded[index];index+=1
            self.assertEqual(expected['role'],role)
            self.assertEqual(request,expected['request'])
            return copy.deepcopy(expected['response'])
        async def extract(request):return await consume('extract',request)
        async def judge(request):return await consume('judge',request)
        self.writer.luna_identity=True
        self.writer.models.extract=extract;self.writer.models.judge=judge
        for name in ['first','correction','distinct']:
            artifact=json.loads((directory/(name+'.json')).read_text())
            self.store.put_source(self.owner,artifact['source'])
            await self.writer.process_next(self.owner)
        self.assertEqual(index,len(recorded))
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','active','superseded'])
        self.assertEqual(len({r['entity_id'] for r in rows}),2)
        self.assertEqual(self.store.search(self.owner,unresolved_only=True),[])

    async def test_unrepresentable_cross_role_link_retains_fact_without_failing_source(self):
        await self.run_source('one',[proposal('My daughter Maya enjoys swimming.')])
        p=proposal('My colleague Maya also enjoys tennis.');p['mention']['relationship']='colleague'
        result=await self.run_source('two',[p])
        self.assertEqual(result['accepted'],1)
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)
        self.assertEqual(len(self.store.search(self.owner)),1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT state FROM job WHERE session='two'").fetchone()[0],'done')
