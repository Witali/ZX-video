import unittest

import numpy as np

from probe_context_masks import MODES, permute, unpermute, split, encode, decode
import test_prediction_values as prediction_fixture


class ContextMaskTests(unittest.TestCase):
    def test_known_split_positions(self):
        mask = np.zeros(3840, dtype=np.uint8)
        mask[[0, 16, 20, 36, 3839]] = 1
        encoded = permute(np.packbits(mask).tobytes(), 1, 1)
        self.assertEqual(np.flatnonzero(np.unpackbits(np.frombuffer(encoded, dtype=np.uint8))).tolist(),
                         [0, 16, 3072, 3076, 3839])

    def test_all_modes_random_masks_and_complete_container(self):
        rng = np.random.default_rng(217)
        for n in (1, 3, 8):
            masks = rng.integers(0, 256, n*480, dtype=np.uint8).tobytes()
            for mode in range(len(MODES)):
                self.assertEqual(unpermute(permute(masks, n, mode), n, mode), masks)
        _, _, raw = prediction_fixture.PredictionValuesTests().fixture()
        header, groups = split(raw)
        for mode in range(len(MODES)):
            changed = encode(header, groups, mode)
            self.assertEqual(decode(changed), raw)
            for bad in (changed[:-1], changed+b'!', changed[:4]+b'\xff'+changed[5:]):
                with self.assertRaises(ValueError):
                    decode(bad)


if __name__ == '__main__':
    unittest.main()
