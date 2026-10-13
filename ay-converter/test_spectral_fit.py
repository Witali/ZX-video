"""Independent square harmonics, integer controls, pauses and invalid inputs."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import spectral_fit as fit
from simulation_refine import spectra


class SpectralFitTests(unittest.TestCase):
    def test_dictionary_matches_independent_bandlimited_square(self):
        periods, frequencies, basis, hz, useful = fit.square_dictionary(2048)
        for wanted in (137., 441., 1000.):
            period = round(1773450 / (16 * wanted)); frequency = 1773450 / (16 * period)
            time = np.arange(30 * 441) / 22050
            # A directly sampled discontinuous square aliases its unlimited
            # harmonics back into the test band. The real renderer filters
            # those edges; synthesize the independent Fourier series instead.
            square = sum(2 / (3 * np.pi * h) * np.sin(2 * np.pi * h * (time * frequency + .123))
                         for h in range(1, int(10584 / frequency) + 1, 2))
            observed = spectra(square, np.array([15]), 2048)[0, useful]
            expected = basis[period - 14]
            cosine = observed @ expected / np.sqrt((observed @ observed) * (expected @ expected))
            self.assertGreater(cosine, .99)
            self.assertAlmostEqual(float(np.linalg.norm(observed) / np.linalg.norm(expected)), 1, delta=.04)

    def test_real_integer_states_and_exact_pauses(self):
        root = Path(__file__).resolve().parents[1]; temporary = root / '.tmp'; temporary.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary, prefix='fit-test-') as directory:
            Path(directory).resolve().relative_to(root)
            time = np.arange(16 * 441) / 22050
            source = .15 * np.where((time * 317.3) % 1 < .5, 1., -1.)
            source[:3 * 441] = 0; source[-3 * 441:] = 0
            raw, meta = fit.fit(source, 'node', directory)
            rows = np.frombuffer(raw, np.uint8).reshape(-1, 11)
            self.assertEqual(len(rows), 16)
            self.assertTrue(np.all(rows[:, 1:6:2] <= 15) and np.all(rows[:, 8:11] <= 15))
            self.assertTrue(np.all(rows[:3, 8:11] == 0) and np.all(rows[-3:, 8:11] == 0))
            periods = rows[:, :6:2].astype(int) + 256 * rows[:, 1:6:2].astype(int)
            active = rows[:, 8:11] > 0
            realized = 1773450 / (16 * periods)
            self.assertTrue(np.any(abs(realized[active] - 317.3) < 3))
            self.assertFalse(meta['source_samples_added_to_output'])

    def test_invalid_inputs_fail_before_generating_dictionary(self):
        for source, options in ((np.zeros(442), {}), (np.array([np.nan] * 441), {}),
                                (np.zeros(441), dict(window=1024)), (np.zeros(441), dict(output_gain=0)),
                                (np.zeros(441), dict(weight=2)), (np.zeros(441), dict(continuity=-1))):
            with self.assertRaises(ValueError): fit.fit(source, 'missing-node', 'unused', **options)


if __name__ == '__main__': unittest.main()
