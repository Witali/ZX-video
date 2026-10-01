"""Check speech-mode handling and real resonances without changing the player."""
import unittest
import numpy as np

from probe_lpc2 import formant_frames
from player import build_disk
import ay_interrupt


class MappingTests(unittest.TestCase):
    def test_known_resonances_remain_nonmusical_formants(self):
        coefficients = np.array([1.])
        for frequency, bandwidth in ((517, 70), (1473, 100), (2631, 130)):
            radius = np.exp(-np.pi*bandwidth/8000)
            coefficients = np.convolve(coefficients, [1, -2*radius*np.cos(2*np.pi*frequency/8000), radius*radius])
        coefficients = np.pad(coefficients, (0, 11-len(coefficients)))
        record = dict(coefficients=coefficients, mode=2, energy=20)
        frames, details = formant_frames([record]*5, .1*np.sin(np.arange(800)*.1))
        self.assertTrue(np.all(abs(np.array(details[0]['formants_hz'])-[517,1473,2631]) < 50))
        self.assertTrue(all(f.noise_period == 0 and all(1 <= p <= 4095 for p in f.periods) for f in frames))
        build_disk(b''.join(ay_interrupt.registers(f) for f in frames))

    def test_silence_and_unvoiced_consonants(self):
        records = [dict(coefficients=[1]+[0]*10, mode=mode, energy=energy)
                   for mode, energy in ((0,0), (0,20), (3,20), (2,20))]
        frames, _ = formant_frames(records, np.full(640, .1))
        self.assertEqual(frames[0].volumes, (0,0,0))
        for f in frames[1:3]:
            self.assertTrue(1 <= f.noise_period <= 31)
            self.assertEqual((f.volumes[0],f.volumes[2]), (0,0))
            self.assertGreater(f.volumes[1], 0)
        self.assertEqual(frames[3].noise_period, 0)


if __name__ == '__main__':
    unittest.main()
