"""Check rolling state against an exhaustive horizon and detect boundary noise."""
import unittest
import numpy as np
from ima_codec import decode
from ima_waveform_encoder import encode_waveform
from analyze_ima_boundaries import boundary_metrics


class RollingLookahead(unittest.TestCase):
    def test_committing_prefix_retains_exact_decoder_and_filter_state(self):
        # Four samples, eight codes, width 4096: retain the entire search tree.
        # A shrinking horizon must reproduce the globally selected full path.
        # Distinct PDM/filter histories matter even at the same IMA state.
        rng = np.random.default_rng(19)
        a = np.eye(6)*.7
        l = rng.normal(0, .2, (16, 6))
        response = rng.normal(0, .2, (128*32, 16))
        endpoint = rng.normal(0, .1, (128*32, 6))
        features = [(a, l, response, endpoint, np.ones(16))]
        nxt = (np.arange(128)[:, None]+np.arange(32)[None, :]+1) % 32
        source = np.full(132, 128, dtype='u1')
        desired = rng.normal(0, .2, (4, 16))
        options = dict(width=4096, block_size=4, history_bins=10**12,
                       allowed_codes=np.arange(0, 16, 2), level_bounds=(4, 123))
        full = encode_waveform(source, desired, features, np.zeros(4, dtype=int), nxt, **options)
        for commit in (1, 2, 3, 4):
            rolled = encode_waveform(source, desired, features, np.zeros(4, dtype=int), nxt,
                                     commit_size=commit, **options)
            self.assertEqual(rolled, full)
            pcm, index = decode(rolled)
            self.assertEqual((pcm[-1], index[-1]), (0, 0))
            self.assertFalse(np.any(np.frombuffer(rolled, 'u1') & 0x11))

    def test_invalid_commit_rejected_before_encoding(self):
        for commit in (0, -1, 129):
            with self.assertRaises(ValueError):
                encode_waveform(None, None, None, None, None, block_size=128, commit_size=commit)

    def test_boundary_diagnostic_detects_error_bursts(self):
        rate = 44100
        time = np.arange(rate*2)/rate
        source = np.full(len(time), .25)
        phase = (time*8000).astype(int) % 128
        error = np.where(phase < 8, .04, .01)
        ticks = np.rint(np.arange(16001*16)*3546900/(8000*16)).astype(np.int64)
        burst = boundary_metrics(source, source+error, ticks, 128)
        uniform = boundary_metrics(source, source+.01, ticks, 128)
        self.assertGreater(burst['boundary_to_middle_ratio'], 14)
        self.assertAlmostEqual(uniform['boundary_to_middle_ratio'], 1., places=8)


if __name__ == '__main__':
    unittest.main()
