import unittest

from assess_ay_onsets import count_bounds


class OnsetBoundsTests(unittest.TestCase):
    def test_known_current_counts(self):
        result=count_bounds(134,157,110)
        self.assertAlmostEqual(result['retiming_only_upper_bound'],268/291)
        self.assertEqual(result['minimum_matches_with_no_false_positives'],122)
        self.assertEqual(result['maximum_candidates_with_all_reference_matched'],148)
        self.assertEqual(result['minimum_detection_edits'],57)
        self.assertEqual(result['balanced_candidate_case']['minimum_matches'],128)
        for case in result['best_case_edit_solutions']:self.assertGreaterEqual(case['f1'],.95)

    def test_exact_threshold_is_accepted(self):
        result=count_bounds(134,146,133)
        self.assertEqual(result['f1'],.95)
        self.assertEqual(result['minimum_detection_edits'],0)

    def test_missing_and_extra_events(self):
        self.assertEqual(count_bounds(100,0,0)['minimum_detection_edits'],91)
        self.assertEqual(count_bounds(100,100,100)['minimum_detection_edits'],0)
        with self.assertRaises(ValueError):count_bounds(10,5,6)


if __name__=='__main__':unittest.main()
