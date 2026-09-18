"""Check reference error bounds, temporal caps and original FMR1 decoding."""
import unittest

import numpy as np

from probe_bounded_dictionary import accept_pattern
import probe_fine_motion as motion
from probe_bounded_motion import choose_omissions, predict
from review_motion_quality import transition_counts


class BoundedMotionTests(unittest.TestCase):
    def test_missing_and_spurious_changes_are_distinct(self):
        previous = np.zeros((1, 3, 3), dtype=np.uint8)
        reference = previous.copy()
        candidate = previous.copy()
        reference[0, 0] = 255
        reference[0, 2] = 100
        candidate[0, 1] = 200
        candidate[0, 2] = 90
        self.assertEqual(transition_counts(previous, reference, previous, candidate),
                         dict(source_changes=2, missing_changes=1, spurious_changes=1))

    def test_partial_cell_keeps_large_changes(self):
        original = np.zeros((1, 768, 4), dtype=np.uint8)
        proposed = original.copy()
        proposed[0, 0] = [0x40, 0x80, 0xc0, 0x04]
        attrs = np.full(768, 7, dtype=np.uint8)
        selected, _ = choose_omissions(original, proposed, attrs, np.zeros(768), 2, 24, 1)
        self.assertEqual(selected[0, 0].tolist(), [True, False, False, True])
        restored = np.where(selected, proposed, original)
        self.assertTrue(accept_pattern(original[0], restored[0], attrs, 24, 2).all())

    def test_age_and_rmse_reject_omissions(self):
        original = np.zeros((1, 768, 4), dtype=np.uint8)
        proposed = np.full_like(original, 0x40)
        attrs = np.full(768, 7, dtype=np.uint8)
        for ages, rmse in [(np.ones(768), 24), (np.zeros(768), 0)]:
            selected, _ = choose_omissions(original, proposed, attrs, ages, 2, rmse, 1)
            self.assertFalse(selected.any())

    def test_reference_and_global_budget_and_forced_exact_frame(self):
        states = np.zeros((3, 3840), dtype=np.uint8)
        states[:, 3072:] = 7
        states[1:, 0:10] = 0x40
        vectors, residual, filtered, stats = predict(states, [(0, 0)], budget=3)
        self.assertEqual(stats['max_logical_changes_per_frame'], 3)
        self.assertEqual(stats['maximum_consecutive_inexact_frames'], 1)
        self.assertEqual(np.count_nonzero(states[1, :3072] != filtered[1, :3072]), 3)
        # The three inexact cells must be repaired on the next frame.
        inexact = states[1, :3072] != filtered[1, :3072]
        np.testing.assert_array_equal(filtered[2, :3072][inexact], states[2, :3072][inexact])
        np.testing.assert_array_equal(filtered[:, 3072:], states[:, 3072:])
        np.testing.assert_array_equal(motion.decode(motion.encode(vectors, residual, 8, [(0, 0)], 2)), filtered)

    def test_zero_error_control_reproduces_exact_motion_search(self):
        rng = np.random.default_rng(733)
        states = rng.integers(0, 128, (3, 3840), dtype=np.uint8)
        offsets = [(0, 0), (1, 0), (-1, 1)]
        expected_vectors, expected_delta = motion.predict(states, 8, offsets, 8)
        vectors, delta, filtered, _ = predict(states, offsets, maximum_changed=0)
        np.testing.assert_array_equal(vectors, expected_vectors)
        np.testing.assert_array_equal(delta, expected_delta)
        np.testing.assert_array_equal(filtered, states)

    def test_three_frame_error_cap_forces_repair_without_drift(self):
        states = np.zeros((6, 3840), dtype=np.uint8)
        states[:, 3072:] = 7
        states[1:, 0] = 0x40
        vectors, residual, filtered, stats = predict(states, [(0, 0)], budget=1, max_inexact=3)
        self.assertEqual(stats['maximum_consecutive_inexact_frames'], 3)
        self.assertEqual(stats['logical_changes_per_frame'], [0, 1, 1, 1, 0, 0])
        np.testing.assert_array_equal(filtered[1:4, 0], [0, 0, 0])
        np.testing.assert_array_equal(filtered[4:], states[4:])
        np.testing.assert_array_equal(filtered[:, 3072:], states[:, 3072:])
        np.testing.assert_array_equal(motion.decode(motion.encode(vectors, residual, 8, [(0, 0)], 2)), filtered)


if __name__ == '__main__':
    unittest.main()
