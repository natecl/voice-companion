import unittest
from score_quality import align, tokens

class AlignmentTests(unittest.TestCase):
    def test_edit_counts_and_matched_indices(self):
        counts, pairs = align(['a', 'b', 'c'], ['a', 'x', 'c', 'd'])
        self.assertEqual(counts, {'substitutions': 1, 'deletions': 0, 'insertions': 1})
        self.assertEqual(sorted(pairs), [(0, 0), (2, 2)])

    def test_deletion_and_empty_hypothesis(self):
        self.assertEqual(align(['a', 'b'], ['a'])[0]['deletions'], 1)
        self.assertEqual(align(['a', 'b'], [])[0]['deletions'], 2)

    def test_normalization_keeps_possessives_as_lexical_differences(self):
        self.assertEqual(tokens("Follow-up, NEXT Thursday."), ['follow', 'up', 'next', 'thursday'])
        self.assertNotEqual(tokens("laboratory's"), tokens('laboratory'))

if __name__ == '__main__':
    unittest.main()
