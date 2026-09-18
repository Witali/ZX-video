"""Independent half-pixel examples, integer controls and boundary conditions."""
import struct
import unittest

import numpy as np

import probe_fine_motion as integer
from probe_halfpel_motion import blend_table, decode, encode, offsets_for, predict, shifted_candidates


class HalfPixelTests(unittest.TestCase):
    def test_nonuniform_levels_and_ties(self):
        lower, upper = blend_table(), blend_table(True)
        self.assertEqual(lower[0, 3], 2)  # (0 + 4)/2 = 2, not level-index 1.5
        self.assertEqual(lower[1, 2], 1)
        self.assertEqual(upper[1, 2], 2)
        self.assertEqual(lower[2, 3], 2)
        self.assertEqual(upper[2, 3], 3)

    def test_positive_negative_half_shifts_and_zero_padding(self):
        source = np.zeros(3072, dtype=np.uint8)
        source[0] = 3  # x=3, y=0
        candidates = shifted_candidates(source, [(1, 0), (-1, 0), (1, 1)], blend_table())
        self.assertEqual(candidates[0, :2].tolist(), [2, 0x80])
        self.assertEqual(candidates[1, :2].tolist(), [0x0a, 0])
        self.assertEqual(candidates[2, :2].tolist(), [1, 0x40])
        self.assertEqual(candidates[2, 32:34].tolist(), [1, 0x40])

    def test_hand_written_stream_and_attribute_address(self):
        header = b'HMR1' + struct.pack('<BBBIbbbb', 0, 8, 2, 2, 0, 0, 1, 0)
        # First tile bitmap field 0 and attribute field 16, in tile order.
        masks = bytes([128, 0, 128]) + bytes(477)
        first = struct.pack('<H', 1) + bytes(192) + masks + bytes([3, 7])
        second = struct.pack('<H', 1) + bytes([1]) + bytes(191) + bytes(480)
        states = decode(header + first + second)
        self.assertEqual(states[0, :2].tolist(), [3, 0])
        self.assertEqual(states[1, :2].tolist(), [2, 0x80])
        self.assertEqual(states[:, 3072].tolist(), [7, 7])

    def test_integer_control_matches_existing_search(self):
        rng = np.random.default_rng(88)
        states = rng.integers(0, 128, (3, 3840), dtype=np.uint8)
        offsets = offsets_for(False)
        previous_vectors, previous_delta = integer.predict(states, 8, [(x//2, y//2) for x, y in offsets], 8)
        vectors, delta = predict(states, offsets)
        np.testing.assert_array_equal(vectors, previous_vectors)
        np.testing.assert_array_equal(delta, previous_delta)
        np.testing.assert_array_equal(decode(encode(vectors, delta, offsets, group_frames=2)), states)

    def test_both_rounding_modes_round_trip(self):
        rng = np.random.default_rng(221)
        states = rng.integers(0, 128, (3, 3840), dtype=np.uint8)
        offsets = offsets_for(True)
        for upper in (False, True):
            states[1, :3072] = shifted_candidates(states[0, :3072], [(1, -1)], blend_table(upper))[0]
            vectors, delta = predict(states, offsets, upper)
            self.assertTrue(np.any(vectors[1] >= 81))
            stream = encode(vectors, delta, offsets, upper, 2)
            np.testing.assert_array_equal(decode(stream), states)
            with self.assertRaises(ValueError):
                decode(stream[:-1])


if __name__ == '__main__':
    unittest.main()
