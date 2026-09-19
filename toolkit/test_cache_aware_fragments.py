import unittest

import numpy as np

from probe_cache_aware_fragments import choose


class CacheAwareSelectionTests(unittest.TestCase):
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
