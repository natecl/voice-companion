import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_feature as feature
import verify_checkpoint as checkpoint


class FeatureVerifierTests(unittest.TestCase):
    def test_every_feature_has_valid_complete_contract_and_paths(self):
        features = feature.catalog()
        self.assertGreaterEqual(len(features), 17)
        for key, entry in features.items():
            with self.subTest(feature=key):
                manifest = json.loads((feature.ROOT / entry['manifest']).read_text())
                checkpoint.validate(manifest)
                self.assertEqual(manifest['packet'], 'FEATURE-' + key)
                context = feature.ROOT / entry['context_map']
                self.assertTrue(context.is_file())
                contents = context.read_text()
                for section in ('Current implementation', 'Gaps and non-goals', 'Contracts and dependencies',
                                'Verification and delivery state', 'Next bounded work'):
                    self.assertIn('## ' + section, contents)
                self.assertIn('verify_feature.py ' + key, contents)
                import re
                for target in re.findall(r'\]\(([^)]+)\)', contents):
                    if '://' not in target:
                        self.assertTrue((context.parent / target.split('#')[0]).is_file(), target)

                for path in entry['implementation']:
                    self.assertTrue((feature.ROOT / path).is_file(), path)
                self.assertTrue(any(c['group'] == 'inspection' for c in manifest['checks']))
                self.assertTrue(any(c['group'] == 'live_behavior_checks' for c in manifest['checks']))

    def test_unknown_feature_never_executes(self):
        with patch.object(checkpoint, 'run') as run:
            with self.assertRaises(ValueError):
                feature.verify('meeting-notes;echo unsafe')
            run.assert_not_called()

    def test_unimplemented_release_features_have_no_fake_automated_success(self):
        for feature_id in ('pricing', 'subscriptions', 'distribution'):
            with self.subTest(feature=feature_id), patch.object(checkpoint, 'run') as run:
                with self.assertRaises(ValueError):
                    feature.verify(feature_id, checks_only=True)
                run.assert_not_called()

    def test_full_feature_uses_linked_manifest_and_never_self_approves(self):
        with patch.object(checkpoint, 'run', return_value={'status': 'needs_review'}) as run:
            receipt = feature.verify('meeting-notes')
            self.assertEqual(run.call_args.args[1], feature.ROOT / 'docs/features/verification/meeting-notes.json')
            self.assertEqual(receipt['verification_scope'], 'full_feature')
            self.assertFalse(receipt['feature_verified'])

    def test_checks_only_has_no_live_claim(self):
        with patch.object(checkpoint, 'run', return_value={'status': 'needs_review'}) as run:
            receipt = feature.verify('meeting-notes', checks_only=True)
            path = run.call_args.args[1]
            try:
                manifest = json.loads(path.read_text())
                checkpoint.validate(manifest)
                self.assertTrue(all(c['group'] == 'mechanical_checks' for c in manifest['checks']))
                self.assertEqual(receipt['verification_scope'], 'mechanical_only')
                self.assertFalse(receipt['feature_verified'])
            finally:
                path.unlink()

    def test_mechanical_receipt_cannot_release_dependents(self):
        receipt = {'verification_scope': 'mechanical_only'}
        with self.assertRaisesRegex(ValueError, 'full feature'):
            checkpoint.review(feature.ROOT, receipt, 'orchestrator', 'accepted_for_integration', 'reviewed', ['next'])

    def test_account_regressions_and_native_sources_are_mapped(self):
        entry = feature.catalog()['access']
        self.assertTrue({
            'Backend.test_account_migration', 'Backend.test_migration_operator',
            'Backend.test_apple_oauth', 'Backend.test_provider_grants',
            'Backend.test_account_isolation_regression', 'Backend.test_managed_backups',
            'Backend.test_backup_restore', 'Backend.test_backup_retention',
        } <= set(entry['test_modules']))
        self.assertIn('UnitTests/RecordingLifecycleTests.swift', entry['external_test_sources'])
        self.assertIn('UnitTests/RecordingNotesCacheTests.swift', entry['external_test_sources'])
        manifest = json.loads((feature.ROOT / entry['manifest']).read_text())
        provider_checks = [c for c in manifest['checks'] if c['kind'] == 'live_identity_provider']
        self.assertEqual({c['provider'] for c in provider_checks}, {'google', 'apple'})
        self.assertTrue(any(c['kind'] == 'physical_device' for c in manifest['checks']))
        self.assertEqual({c['provider'] for c in provider_checks if c['id'].endswith('-failure-recovery')}, {'google', 'apple'})

    def test_catalog_rejects_wrong_runner_missing_native_source_and_outside_paths(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'docs/features').mkdir(parents=True)
            (root / 'Backend').mkdir()
            (root / 'Backend/test_sample.py').write_text('')
            (root / 'source.swift').write_text('')
            (root / 'map.md').write_text('')
            manifest = dict(packet='FEATURE-sample', base='fixture', acceptance=['inspect'], checks=[
                dict(id='mechanical', group='mechanical_checks', kind='fixture', runner='feature:sample'),
                dict(id='behavior', group='live_behavior_checks', kind='simulator', evidence='work/behavior.json'),
                dict(id='review', group='inspection', kind='review', evidence='work/review.json')])
            manifest_path = root / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            entry = dict(name='Sample', outcome='Outcome', status='Incomplete', verification_scope='Bounded',
                         implementation=['source.swift'], external_test_sources=['source.swift'],
                         test_modules=['Backend.test_sample'], manifest='manifest.json', context_map='map.md')
            path = root / 'docs/features/catalog.json'
            path.write_text(json.dumps({'sample': entry}))
            with patch.dict(checkpoint.REGISTRY, dict(checkpoint.REGISTRY), clear=True):
                feature.catalog(root)
                self.assertIn('feature:sample', checkpoint.REGISTRY)
                for field, bad in [('implementation', ['../outside']),
                                   ('external_test_sources', ['missing.swift']),
                                   ('test_modules', ['Backend.test_sample', 'Backend.test_sample'])]:
                    changed = dict(entry, **{field: bad})
                    path.write_text(json.dumps({'sample': changed}))
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        feature.catalog(root)
                path.write_text(json.dumps({'sample': entry}))
                manifest['checks'][0]['runner'] = 'feature:other'
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'runner'):
                    feature.catalog(root)
                # Removing the suite removes its old command; it cannot remain
                # executable through a stale registration from the prior load.
                entry['test_modules'] = []
                manifest['checks'][0].pop('runner')
                manifest['checks'][0]['evidence'] = 'work/mechanical.json'
                path.write_text(json.dumps({'sample': entry}))
                manifest_path.write_text(json.dumps(manifest))
                feature.catalog(root)
                self.assertNotIn('feature:sample', checkpoint.REGISTRY)

    def test_full_feature_cannot_exempt_live_acceptance(self):
        # A checkpoint may have justified exemptions; a full feature may not
        # turn its required real behavior into mechanical-only acceptance.
        entries = json.loads((feature.ROOT / 'docs/features/catalog.json').read_text())
        target = feature.ROOT / entries['access']['manifest']
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            raw = original_read(path, *args, **kwargs)
            if path == target:
                manifest = json.loads(raw)
                manifest['checks'] = [c for c in manifest['checks'] if c['group'] != 'live_behavior_checks']
                manifest['not_applicable'] = {'live_behavior_checks': 'Only fixtures available'}
                return json.dumps(manifest)
            return raw
        with patch.object(Path, 'read_text', read), patch.object(checkpoint, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'live behavior'):
                feature.verify('access')
            run.assert_not_called()
