"""Trajectory persistence, supported attacks, silent choices and real bus audit."""
import unittest
import numpy as np
import coherent_ym3812 as c
import experimental_ym3812 as opl
from test_experimental_ym3812 import audit


class CoherentTests(unittest.TestCase):
    def test_weak_one_field_octave_excursion_is_rejected(self):
        emission = np.array([[0, 1], [0, 1], [.01, 0], [0, 1], [0, 1]], float)
        frequency = np.tile([440., 880.], (5, 1)); levels = np.full((5, 2), 30)
        self.assertTrue(np.array_equal(c.path(emission, frequency, levels, np.zeros((5, 2)), .01), np.zeros(5)))

    def test_supported_persistent_attack_is_retained(self):
        emission = np.array([[0, 1], [0, 1], [1, 0], [1, 0], [1, 0]], float)
        frequency = np.tile([440., 880.], (5, 1)); levels = np.full((5, 2), 12)
        self.assertTrue(np.array_equal(c.path(emission, frequency, levels, np.ones((5, 2)), .01), [0, 0, 1, 1, 1]))

    def test_quiet_lattice_state_and_native_register_schedule(self):
        emission = np.array([[0, 1], [1, 0], [1, 0], [0, 1]], float)
        frequency = np.full((4, 2), 440.); levels = np.tile([24, 64], (4, 1))
        selected = c.path(emission, frequency, levels, np.zeros((4, 2)), .001)
        self.assertTrue(np.array_equal(selected, [0, 1, 1, 0]))
        fnum, block = opl.frequency_code(np.array([440.]))
        controls = dict(fnum=np.full((4, 9), fnum[0], np.uint16), block=np.full((4, 9), block[0], np.uint8),
                        patch=np.zeros((4, 9), np.uint8), level=np.full((4, 9), 64, np.uint8))
        controls['level'][:, 0] = levels[np.arange(4), selected]
        data, writes = opl.smooth_vgm(controls)
        self.assertEqual(audit(data, controls)['writes'], writes)

    def test_bad_lattice_inputs(self):
        for strength in (-1, float('nan')):
            with self.assertRaises(ValueError): c.path(np.zeros((2, 2)), np.ones((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)), strength)
        with self.assertRaises(ValueError): c.path(np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)), .01)


if __name__ == '__main__': unittest.main()
