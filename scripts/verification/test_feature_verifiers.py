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
