"""Check harmonic-group endpoints, bus timing and historical export identity."""
import unittest
import numpy as np
import experimental_ym3812 as opl
import grouped_ym3812 as groups
from test_experimental_ym3812 import audit


class GroupedTests(unittest.TestCase):
    def controls(self):
        fnum, block = opl.frequency_code(np.array([440., 550., 660., 440.]))
        return dict(fnum=np.tile(fnum[:, None], (1, 9)), block=np.tile(block[:, None], (1, 9)),
                    patch=np.tile(np.array([0, 14, 0, 14], np.uint8)[:, None], (1, 9)),
                    level=np.tile(np.array([16, 24, 64, 12], np.uint8)[:, None], (1, 9)))

    def test_historical_sine_export_is_byte_exact(self):
        controls = self.controls()
        self.assertEqual(groups.export(controls), opl.smooth_vgm(controls))

    def test_real_modulator_ramps_keep_every_target(self):
        controls = self.controls(); controls['patch'][:] = np.array([0, 21, 7, 14], np.uint8)[:, None]
        data, writes = groups.export(controls)
        self.assertEqual(audit(data, controls)['writes'], writes)
        a, samples, parsed = opl.replay(data); b, *_ = opl.replay(data)
        self.assertTrue(np.array_equal(a, b)); self.assertEqual((samples, parsed), (3528, writes))


if __name__ == '__main__': unittest.main()
