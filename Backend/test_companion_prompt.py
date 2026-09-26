import json
from pathlib import Path
import unittest
from ask import instructions,input_fits,references

class RecordedCompanionPromptTests(unittest.TestCase):
    def test_historical_v1_identity_correction_and_quoted_evidence(self):
        root=Path(__file__).parent/'fixtures/companion-service'
        cases=json.loads((root/'identity-v2.json').read_text())+[json.loads((root/'quoted-v1.json').read_text())]
        for case in cases:
            with self.subTest(question=case['data']['question']):
                self.assertEqual((Path(__file__).parent/'prompts/companion-chat-v1.md').read_text(),case['instructions'])
                self.assertTrue(input_fits(case['data']))
                self.assertTrue(references(case['answer'],case['data']['sources']))
        self.assertIn('identified as you',cases[0]['answer'])
        self.assertIn('identified as you',cases[1]['answer'])
        self.assertIn('tennis',cases[2]['answer'])
        self.assertIn('tennis',cases[3]['answer'])
        self.assertNotIn('BANANA',cases[3]['answer'])
