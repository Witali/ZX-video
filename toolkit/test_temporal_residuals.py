"""Independent format examples and temporal error/drift boundaries."""
import struct
import unittest

import numpy as np

from probe_temporal_residuals import decode, encode, temporal_filter


class TemporalResidualTests(unittest.TestCase):
    def test_hand_written_n2_stream_and_last_mask_bit(self):
        mask = bytes([128]) + bytes(478) + bytes([1])
        stream = b'TRS1' + struct.pack('<BIH', 2, 3, 2)
        stream += mask * 2 + bytes([0x40, 7, 0x80, 6])
        stream += struct.pack('<H', 1) + bytes(480)
        expected = np.zeros((3, 3840), dtype=np.uint8)
        expected[0, [0, 3839]] = [0x40, 7]
        expected[1, [0, 3839]] = [0x80, 6]
        expected[2] = expected[0]
        np.testing.assert_array_equal(decode(stream), expected)

    def test_n1_groups_share_history(self):
        rng = np.random.default_rng(139)
        states = rng.integers(0, 256, size=(5, 3840), dtype=np.uint8)
        states[2] = states[1]
        for distance in (1, 2):
            np.testing.assert_array_equal(decode(encode(states, distance, 2)), states)

    def test_hold_cap_forces_small_motion_to_be_drawn(self):
        states = np.zeros((4, 3840), dtype=np.uint8)
        states[:, 3072:] = 7
        states[1:, 0] = 0x40
        filtered, stats = temporal_filter(states, 1, 24, 1)
        self.assertEqual(filtered[:, 0].tolist(), [0, 0, 0x40, 0x40])
        self.assertEqual(stats['maximum_consecutive_inexact_holds'], 1)
        np.testing.assert_array_equal(states[:, 3072:], filtered[:, 3072:])

    def test_reference_bound_prevents_error_drift(self):
        states = np.zeros((3, 3840), dtype=np.uint8)
        states[:, 3072:] = 7
        states[:, 0] = [0, 0x40, 0x80]
        filtered, _ = temporal_filter(states, 1, 24, 0)
        self.assertEqual(filtered[:, 0].tolist(), [0, 0, 0x80])

    def test_bad_streams(self):
        header = b'TRS1' + struct.pack('<BI', 1, 1)
        for stream in (b'', header, header + b'\0\0' + bytes(480),
                       header + b'\1\0' + b'\x80' + bytes(479),
                       header + b'\1\0' + bytes(480) + b'\0'):
            with self.subTest(stream_length=len(stream)), self.assertRaises(ValueError):
                decode(stream)


if __name__ == '__main__':
    unittest.main()
