"""Preserve failed candidate evidence without changing production gates."""
import json,unittest
from pathlib import Path
from evaluate_preference_context import candidate,controls
from memory_judgments import decisions
ROOT=Path(__file__).parent/'fixtures/preference-context'
class PreferenceContextTests(unittest.TestCase):
    def test_exact_requests_and_recorded_failures(self):
        rows=json.loads((ROOT/'results.json').read_text())
        self.assertEqual(len(rows),9)
        for r in rows:
            req=candidate(r['case']['source'],r['case']['proposals'],context_only=r['variant']=='context-only')
            self.assertEqual(req,r['request'])
            self.assertEqual(decisions(r['response']['data'],req),r['decisions'])
        failures=[r['case']['name'] for r in rows if r['variant']=='candidate' and not r['passed']]
        self.assertEqual(failures,['project','person'])
        self.assertTrue(all(not any(r['accepted']) for r in rows if r['case']['name'] in ('competing','quotation','historical','hypothetical')))
    def test_complete_sentence_controls_are_not_a_solution(self):
        rows=json.loads((ROOT/'controls.json').read_text())
        for c,r in zip(controls(),rows,strict=True):
            self.assertEqual(candidate(c['source'],c['proposals']),r['request'])
            self.assertEqual(decisions(r['response']['data'],r['request']),r['decisions'])
        self.assertEqual([r['passed'] for r in rows],[True,False])
