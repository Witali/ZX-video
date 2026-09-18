import struct
import unittest

import numpy as np

from probe_context_values import Decoder
from probe_direct_values import encode, decode
from probe_motion_entropy import huffman_lengths
import probe_fine_motion as motion
import probe_motion_alphabet as alphabet
import probe_motion_residual_order as ordering
import test_prediction_values as fixture


class DirectValueTests(unittest.TestCase):
    def source(self):
        raw, flat, _ = fixture.PredictionValuesTests().fixture()
        states = np.frombuffer(flat, dtype=np.uint8).reshape(3, 3840)
        offsets = [struct.unpack_from('<bb', raw, 35+2*i) for i in range(raw[30])]
        vectors = np.tile(np.arange(192, dtype=np.uint8) % 4, (3, 1))
        prediction = np.zeros_like(states)
        previous = np.zeros(3840, dtype=np.uint8)
        for frame in range(3):
            candidates = motion.tile_bytes(motion.shifted_candidates(previous[:3072], offsets), 8)
            prediction[frame, :3072] = motion.raster_bytes(candidates[vectors[frame], np.arange(192)][None], 8)[0]
            prediction[frame, 3072:] = previous[3072:]
            previous = states[frame]
        residual = states ^ prediction
        remapped = alphabet.remap(states, residual, np.frombuffer(raw[4:20], dtype=np.uint8).reshape(4, 4))
        direct = states.copy(); direct[:, 3072:] = residual[:, 3072:]
        order = ordering.field_order(8)
        return raw, flat, prediction[:, order], [m[:, order] for m in (remapped, residual, direct)], residual[:, order] != 0

    def test_every_value_kind_with_zero_targets_and_short_last_group(self):
        raw, states, prediction, matrices, active = self.source()
        mapping = np.arange(256, dtype=np.uint8) % 4
        labels = mapping[prediction]
        labels[:, np.arange(3840) % 20 >= 16] = 4
        for kind, values in enumerate(matrices):
            histogram = np.bincount(labels[active].astype(np.int32)*256+values[active], minlength=5*256).reshape(5, 256)
            tables = [huffman_lengths(dict(enumerate(row))) for row in histogram]
            if kind == 2:
                self.assertGreater(sum(bool(t[0]) for t in tables), 0)
            changed, _ = encode(raw, prediction, values, kind, mapping.tolist(), tables)
            self.assertEqual(decode(changed), (raw, states))
            for bad in (changed[:-1], changed+b'!', changed[:4]+b'\xff'+changed[5:]):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_zero_symbol_requires_explicit_opt_in(self):
        lengths = bytes([1]+[0]*6+[1]+[0]*248)
        with self.assertRaises(ValueError):
            Decoder([lengths])
        decoder = Decoder([lengths], allow_zero=True)
        decoder.begin(b'\x40', 2)
        self.assertEqual([decoder.value(0), decoder.value(0)], [0, 7])


if __name__ == '__main__':
    unittest.main()
