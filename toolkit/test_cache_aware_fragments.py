import unittest

import numpy as np

from probe_cache_aware_fragments import choose


class CacheAwareSelectionTests(unittest.TestCase):
    def test_each_frame_has_its_own_delivery_limit(self):
        vectors = np.zeros((3, 192), dtype=np.uint8)
        gains = np.zeros((3, 192), dtype=np.int64)
        gains[:, :2] = [100, 200]
        extra = np.full_like(gains, 8)
        costs = np.array([500, 500, 500])
        selected, report = choose(gains, extra, vectors, costs, [500, 300, 200], 0)
        self.assertEqual([np.flatnonzero(row).tolist() for row in selected], [[], [1], [0, 1]])
        self.assertEqual(report['estimated_total_tstates'], 1000)
        self.assertEqual(report['estimated_frames_over_target'], 0)
        scalar, _ = choose(gains, extra, vectors, costs, 300, 0)
        broadcast, _ = choose(gains, extra, vectors, costs, [300]*3, 0)
        np.testing.assert_array_equal(scalar, broadcast)
        with self.assertRaises(ValueError):
            choose(gains, extra, vectors, costs, [500, 0, 200], 0)

    def test_cache_removal_competes_with_ordinary_choices(self):
        vectors = np.zeros((3, 192), dtype=np.uint8)
        vectors[1:, :3] = 1
        gains = np.zeros((3, 192), dtype=np.int64)
        gains[1:, :3] = 10; gains[1:, 3] = 200
        extra = np.full((3, 192), 20, dtype=np.int64)
        extra[1, :3] = 1; extra[2, :3] = 100
        selected, report = choose(gains, extra, vectors, np.array([200, 500, 500]), 300, 200)
        self.assertFalse(selected[0].any())
        self.assertEqual(np.flatnonzero(selected[1]).tolist(), [0, 1, 2])
        self.assertEqual(np.flatnonzero(selected[2]).tolist(), [3])
        self.assertEqual(report['forced_no_cache_winning_frames'], 1)
        self.assertEqual(report['cache_frames_before'], 2)
        self.assertEqual(report['cache_frames_after'], 1)
        self.assertEqual(report['estimated_total_tstates'], 770)
        self.assertEqual(report['estimated_added_bits'], 23)


if __name__ == '__main__':
    unittest.main()
