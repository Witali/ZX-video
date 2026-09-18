"""Check field addresses and preservation of complete serialized FMR1 groups."""
import unittest

import numpy as np

import probe_fine_motion as motion
from probe_motion_residual_order import decode, encode, field_order


class MotionResidualOrderTests(unittest.TestCase):
    def test_manual_cell_layout(self):
        self.assertEqual(field_order(4)[:10].tolist(), [0, 32, 64, 96, 3072, 1, 33, 65, 97, 3073])
        self.assertEqual(field_order(8)[:20].tolist(),
                         [x + y * 32 for y in range(8) for x in range(2)] + [3072, 3073, 3104, 3105])
        for size in (4, 8, 16):
            np.testing.assert_array_equal(np.sort(field_order(size)), np.arange(3840))

    def test_serialized_inverse_including_partial_last_group(self):
        rng = np.random.default_rng(994)
        delta = np.zeros((9, 3840), dtype=np.uint8)
        delta[:, ::7] = rng.integers(1, 256, size=delta[:, ::7].shape, dtype=np.uint8)
        vectors = np.zeros((9, 192), dtype=np.uint8)
        stream = motion.encode(vectors, delta, 8, [(0, 0)], 8)
        for size in (4, 8, 16):
            np.testing.assert_array_equal(decode(encode(stream, size)), stream)
        with self.assertRaises(ValueError):
            decode(encode(stream, 8)[:-1])


if __name__ == '__main__':
    unittest.main()
