"""Verify predictor-conditioned residual semantics and legacy XOR decoding."""
import unittest

import numpy as np

import probe_fine_motion as motion
from probe_motion_alphabet import alphabets, decode, remap
from probe_motion_residual_order import encode as reorder


class MotionAlphabetTests(unittest.TestCase):
    def test_all_symbol_pairs_and_zero_code(self):
        original = np.zeros((1, 3840), dtype=np.uint8)
        predicted = original.copy()
        for p in range(4):
            for q in range(4):
                predicted[0, p * 4 + q] = p * 85
                original[0, p * 4 + q] = q * 85
        residual = original ^ predicted
        for _, symbols in alphabets(np.arange(16).reshape(4, 4)):
            converted = remap(original, residual, symbols)
            for p in range(4):
                for q in range(4):
                    code = converted[0, p * 4 + q] & 3
                    self.assertEqual(symbols[p, code], q)
                    self.assertEqual(code == 0, p == q)

    def test_serialized_prediction_and_attribute_xor(self):
        rng = np.random.default_rng(473)
        states = rng.integers(0, 128, (3, 3840), dtype=np.uint8)
        vectors, residual = motion.predict(states, 8, [(0, 0)], 8)
        for _, symbols in alphabets(np.arange(16).reshape(4, 4)):
            mapped = remap(states, residual, symbols)
            data = b'FPR1' + symbols.tobytes() + reorder(motion.encode(vectors, mapped, 8, [(0, 0)], 2), 8)
            np.testing.assert_array_equal(decode(data), states)
        with self.assertRaises(ValueError):
            motion.decode(b'', symbols=[[0, 0, 0, 0]] * 4)


if __name__ == '__main__':
    unittest.main()
