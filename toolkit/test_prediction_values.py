import unittest

import numpy as np

import probe_fine_motion as motion
import probe_motion_alphabet as alphabet
import probe_motion_residual_order as ordering
from probe_motion_entropy import huffman_lengths
from probe_prediction_values import encode, decode


class PredictionValuesTests(unittest.TestCase):
    def fixture(self, blank=False):
        rng = np.random.default_rng(941)
        states = np.zeros((3, 3840), dtype=np.uint8) if blank else rng.integers(0, 256, (3, 3840), dtype=np.uint8)
        offsets = [(0, 0), (-1, 2), (3, -1)]
        vectors = np.tile(np.arange(192, dtype=np.uint8) % 4, (3, 1))
        prediction = np.zeros_like(states)
        previous = np.zeros(3840, dtype=np.uint8)
        for frame in range(3):
            candidates = motion.tile_bytes(motion.shifted_candidates(previous[:3072], offsets), 8)
            selected = candidates[vectors[frame], np.arange(192)]
            prediction[frame, :3072] = motion.raster_bytes(selected[None], 8)[0]
            prediction[frame, 3072:] = previous[3072:]
            previous = states[frame]
        symbols = np.array([[0, 2, 1, 3], [1, 2, 0, 3], [2, 3, 1, 0], [3, 2, 1, 0]], dtype=np.uint8)
        converted = alphabet.remap(states, states ^ prediction, symbols)
        raw = b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, converted, 8, offsets, 2), 8)
        order = ordering.field_order(8)
        prediction = prediction[:, order]
        values = converted[:, order]
        mapping = np.arange(256, dtype=np.uint8) % 4
        labels = mapping[prediction]
        labels[:, order >= 3072] = 4
        active = values != 0
        histogram = np.bincount(labels[active].astype(np.int32)*256+values[active], minlength=5*256).reshape(5, 256)
        tables = [huffman_lengths(dict(enumerate(row))) for row in histogram]
        data, _ = encode(raw, prediction, mapping.tolist(), tables)
        return raw, states.tobytes(), data

    def test_causal_decode_motion_edges_zero_predictor_and_partial_group(self):
        for blank in (False, True):
            with self.subTest(blank=blank):
                raw, states, encoded = self.fixture(blank)
                self.assertEqual(decode(encoded), (raw, states))

    def test_reject_malformed_stream(self):
        _, _, data = self.fixture()
        broken_map = bytearray(data)
        header_size = int.from_bytes(data[5:7], 'little')
        broken_map[7+header_size] = 4  # Attributes cannot be a bitmap context.
        broken_alphabet = bytearray(data)
        broken_alphabet[7+4] = 1
        for invalid in (data[:1], data[:-1], data+b'!', bytes(broken_map), bytes(broken_alphabet)):
            with self.subTest(length=len(invalid)):
                with self.assertRaises(ValueError):
                    decode(invalid)


if __name__ == '__main__':
    unittest.main()
