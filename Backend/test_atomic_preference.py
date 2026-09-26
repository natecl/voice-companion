"""Replay independent classifier experiments; failed acceptance stays explicit."""
import json,unittest
from pathlib import Path
from evaluate_atomic_preference import build,classify
ROOT=Path(__file__).parent/'fixtures/atomic-preference'
class AtomicPreferenceTests(unittest.TestCase):
    def test_reproduce_all_requests_and_failures(self):
        expected={'atomic-v1':['project'],'atomic-v2':['project','person'],'atomic-heldout':['tentative']}
        for name,failures in expected.items():
            rows=json.loads((ROOT/(name+'.json')).read_text())
            for row in rows:
                c=row['case'];req=build(c['source'],c['proposals'],variant='v2' if name=='atomic-v2' else 'v1')
                self.assertEqual(req,row['request'])
                self.assertEqual(classify(row['response']['data'],req,c['proposals']),row['checks'])
            self.assertEqual([r['case']['name'] for r in rows if not r['passed']],failures)
            for row in rows:
                if not any(row['case']['expected']):self.assertFalse(any(c['accepted'] for c in row['checks']))
