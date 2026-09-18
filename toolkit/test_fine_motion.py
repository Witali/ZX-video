"""Decode handcrafted odd-pixel motion and validate edge/attribute handling."""
import struct
import unittest

import numpy as np

from probe_fine_motion import decode, encode, predict, shifted_candidates
from analyze_fine_motion_residuals import analyze


class FineMotionTests(unittest.TestCase):
    def test_single_pixel_shift_crosses_packed_byte(self):
        states = np.zeros((2, 3840), dtype=np.uint8)
        states[0, 0] = 3  # x=3
        states[0, 3072] = 7
        states[1, 1] = 0xc0  # x=4 after moving one logical pixel right
        states[1, 3072] = 7
        vectors = np.zeros((2, 192), dtype=np.uint8)
        vectors[1, 0] = 1
        residual = states.copy()
        residual[1] = 0
        stream = encode(vectors, residual, 8, [(0, 0), (1, 0)], 1)
        np.testing.assert_array_equal(decode(stream), states)

    def test_hand_written_zero_predictor_with_attributes(self):
        header = b'FMR1' + struct.pack('<BBIbb', 16, 1, 2, 0, 0)
        mask = bytes([128]) + bytes(383) + bytes([128]) + bytes(95)
        # First frame one changed bitmap byte and one attribute, then zero
        # predictor clears the bitmap while retaining the preceding attribute.
        stream = header + struct.pack('<H', 1) + bytes(48) + mask + b'\x40\x47'
        stream += struct.pack('<H', 1) + bytes([1]) * 48 + bytes(480)
        states = decode(stream)
        self.assertEqual(states[0, 0], 0x40)
        self.assertEqual(states[1, 0], 0)
        self.assertEqual(states[:, 3072].tolist(), [0x47, 0x47])
        statistics = analyze(stream)
        self.assertEqual(statistics['frames'], 2)
        self.assertEqual(statistics['nonzero_value_bytes'], 2)
        self.assertEqual(statistics['zero_order_entropy_bits'], 1)
        self.assertEqual(statistics['raw_nibble_saving_estimate_bytes'], 1)

    def test_search_round_trip_and_zero_padded_edges(self):
        rng = np.random.default_rng(5)
        states = rng.integers(0, 128, size=(3, 3840), dtype=np.uint8)
        offsets = [(0, 0), (-1, -1), (1, 1)]
        states[1, :3072] = shifted_candidates(states[0, :3072], offsets)[1]
        for size in (4, 8, 16):
            vectors, residual = predict(states, size, offsets, 8)
            self.assertTrue(np.any(vectors[1] == 1))
            np.testing.assert_array_equal(decode(encode(vectors, residual, size, offsets, 2)), states)

    def test_invalid_index_and_truncation(self):
        header = b'FMR1' + struct.pack('<BBIbbH', 16, 1, 1, 0, 0, 1)
        for stream in (b'', header, header + bytes([2]) * 48 + bytes(480)):
            with self.assertRaises(ValueError):
                decode(stream)


if __name__ == '__main__':
    unittest.main()
