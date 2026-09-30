import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('verifier',Path(__file__).parents[1]/'verify_checkpoint.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.git('init','-q');self.git('config','user.email','fixture@example.invalid');self.git('config','user.name','Fixture')
        (self.root/'.gitignore').write_text('work/\n')
        self.git('add','.');self.git('commit','-qm','base')
        self.base=self.git('rev-parse','HEAD')
        self.manifest=dict(packet='fixture',base=self.base,acceptance=['exercise runner'],
            checks=[dict(id='test',group='mechanical_checks',kind='fixture',runner='verifier-self-tests')],
            not_applicable=dict(live_behavior_checks='Local runner tested through actual child execution.',inspection='No UI or model claim.'))
    def git(self,*args):
        return subprocess.check_output(['git',*args],cwd=self.root,text=True,stderr=subprocess.DEVNULL).strip()
    def packet(self):
        p=self.root/'packet.json';p.write_text(json.dumps(self.manifest))
        self.git('add','.');self.git('commit','-qm','packet');return p
    def run_child(self,code):
        p=self.packet()
        with patch.dict(v.REGISTRY,{'verifier-self-tests':[sys.executable,'-c',code]}):
            return v.run(self.root,p)
    def test_success_still_requires_orchestrator_review(self):
        r=self.run_child('pass')
        self.assertEqual(r['status'],'needs_review');self.assertEqual(r['review']['status'],'pending')
        r=v.review(self.root,r,'orchestrator','accepted_for_integration','Inspected child execution and receipt',['next'])
        self.assertEqual(r['review']['released_packets'],['next'])
        self.assertEqual(r['status'],'accepted_for_integration')
    def test_actual_child_failure_blocks_acceptance(self):
        r=self.run_child('raise SystemExit(7)')
        self.assertEqual(r['checks'][0]['exit_code'],7)
        with self.assertRaises(ValueError):v.review(self.root,r,'orchestrator','accepted_for_integration','checked',[])
    def test_unknown_or_paid_execution_never_runs(self):
        self.manifest['checks'][0].update(runner='paid-provider',kind='live_provider')
        with patch.object(v,'execute') as execute:
            with self.assertRaises(ValueError):v.run(self.root,self.packet())
            execute.assert_not_called()
    def test_missing_evidence_is_incomplete(self):
        self.manifest['checks']=[dict(id='live',group='live_behavior_checks',kind='live_provider',evidence='work/missing.json')]
        self.manifest['not_applicable']={'mechanical_checks':'External-only fixture','inspection':'Reviewed later'}
        r=v.run(self.root,self.packet());self.assertEqual(r['status'],'incomplete')
    def test_dirty_and_new_commit_invalidate_evidence(self):
        r=self.run_child('pass')
        (self.root/'changed').write_text('new')
        with self.assertRaises(ValueError):v.review(self.root,r,'reviewer','accepted_for_integration','checked',[])
        self.git('add','.');self.git('commit','-qm','change')
        with self.assertRaises(ValueError):v.review(self.root,r,'reviewer','accepted_for_integration','checked',[])
    def test_child_does_not_inherit_key_and_output_is_not_in_receipt(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'secret-fixture'}):
            r=self.run_child("import os; assert 'OPENAI_API_KEY' not in os.environ; print('private transcript fixture')")
        self.assertEqual(r['checks'][0]['result'],'pass')
        self.assertNotIn('private transcript fixture',json.dumps({k:x for k,x in r['checks'][0].items() if k!='command'}))
    def test_external_fixture_cannot_satisfy_live_kind_and_artifact_changes_fail_review(self):
        self.manifest['checks']=[dict(id='proof',group='live_behavior_checks',kind='live_provider',evidence='work/proof.json')]
        self.manifest['not_applicable']={'mechanical_checks':'External fixture','inspection':'Review required'}
        p=self.packet();(self.root/'work').mkdir()
        proof=self.root/'work/proof.json'
        proof.write_text(json.dumps(dict(commit=v.identity(self.root),kind='fixture',result='pass')))
        self.assertEqual(v.run(self.root,p)['status'],'incomplete')
    def test_changed_artifact_and_outside_paths_rejected(self):
        with self.assertRaises(ValueError):v.local_path(self.root,'../outside')
        r=self.run_child('pass');(self.root/'work').mkdir()
        artifact=self.root/'work/evidence';artifact.write_text('first')
        r['checks'][0]['artifacts']=[v.artifact(self.root,'work/evidence')]
        artifact.write_text('changed')
        with self.assertRaises(ValueError):v.review(self.root,r,'reviewer','accepted_for_integration','checked',[])
    def test_missing_verification_category_rejected(self):
        del self.manifest['not_applicable']['inspection']
        with self.assertRaises(ValueError):v.validate(self.manifest)

    def test_identity_provider_requires_matching_actual_provider_and_configuration(self):
        self.manifest['checks'] = [dict(id='oauth', group='live_behavior_checks',
            kind='live_identity_provider', provider='apple', evidence='work/oauth.json')]
        self.manifest['not_applicable'] = {'mechanical_checks': 'External receipt fixture', 'inspection': 'Review follows'}
        packet = self.packet()
        work = self.root / 'work'; work.mkdir()
        (work / 'raw.txt').write_text('Fictional test artifact only')
        proof = dict(commit=v.identity(self.root), kind='live_identity_provider', result='pass',
                     artifacts=['work/raw.txt'], procedure='Fixture procedure', observed='Fixture observed',
                     provider='apple', configuration='Fixture app/backend configuration',
                     pipeline_layer='native -> real authorization -> account service', provider_calls=1)
        path = work / 'oauth.json'
        for changed in (dict(proof, kind='fixture'), dict(proof, provider='google'),
                        dict(proof, configuration=''), dict(proof, provider_calls=0),
                        dict(proof, provider_calls=True)):
            path.write_text(json.dumps(changed))
            with self.subTest(proof=changed):
                self.assertEqual(v.run(self.root, packet)['status'], 'incomplete')
        path.write_text(json.dumps(proof))
        receipt = v.run(self.root, packet)
        self.assertEqual(receipt['status'], 'needs_review')
        self.assertEqual(receipt['checks'][0]['provider'], 'apple')
        self.assertEqual(receipt['checks'][0]['provider_calls'], 1)
        # These are parser fixtures; no OAuth/model call is made by the verifier.
        self.assertEqual(receipt['paid_calls'], 0)

    def test_malformed_external_receipt_is_incomplete(self):
        self.manifest['checks'] = [dict(id='proof', group='live_behavior_checks', kind='fixture', evidence='work/proof.json')]
        self.manifest['not_applicable'] = {'mechanical_checks': 'External fixture', 'inspection': 'Review required'}
        packet = self.packet(); (self.root / 'work').mkdir()
        (self.root / 'work/proof.json').write_text('[]')
        self.assertEqual(v.run(self.root, packet)['status'], 'incomplete')

if __name__=='__main__':unittest.main()
