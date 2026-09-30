"""Check row-symbol shifts against the independent legacy pixel semantics."""
import unittest
import numpy as np
from probe_fine_motion import shifted_candidates, encode as encode_fmr, decode as decode_fmr
from probe_hybrid_tiles import OFFSETS
from row_aligned_motion import ALIGNED, shifted_rows, predict_rows
from build_long_video_trd import AyFrame
from encode_fap3 import encode


class RowMotionTests(unittest.TestCase):
    def test_all_vectors_and_black_edges(self):
        source = np.random.default_rng(3009).integers(0, 256, 3072, dtype=np.uint8)
        actual = shifted_rows(source)
        # Legacy pixel unpack/shift/repack is independent of symbol slicing.
        expected = shifted_candidates(source, OFFSETS)
        np.testing.assert_array_equal(actual, expected[[v for v, _, _ in ALIGNED]])
        self.assertEqual(len(ALIGNED), 27)

    def test_predictor_scalar_round_trip(self):
        random = np.random.default_rng(123)
        source = random.integers(0, 256, 3072, dtype=np.uint8)
        candidates = shifted_rows(source)
        states = []
        for shifted in candidates:
            states.extend([np.r_[source, np.zeros(768, dtype=np.uint8)],
                           np.r_[shifted, random.integers(0, 128, 768, dtype=np.uint8)]])
        states = np.array(states, dtype=np.uint8)
        vectors, residual = predict_rows(states)
        # Decode each selected vector through the scalar pixel implementation.
        packed = encode_fmr(vectors, residual, 8, OFFSETS, 16)
        np.testing.assert_array_equal(decode_fmr(packed), states)
        self.assertTrue(any(0 < v < 81 for v in vectors.ravel()))
        self.assertTrue(set(vectors.ravel()) <= {v for v, _, _ in ALIGNED})

    def test_repeated_symbols_need_no_motion_or_residual(self):
        states = np.full((3, 3840), 173, dtype=np.uint8)
        vectors, residual = predict_rows(states)
        self.assertFalse(np.any(vectors[1:]))
        self.assertFalse(np.any(residual[1:]))

    def test_fap3_cuts_repetition_and_bright(self):
        random = np.random.default_rng(49)
        states = np.zeros((5, 3840), dtype=np.uint8)
        states[:, 384:2688] = random.integers(0, 256, (5,2304), dtype=np.uint8)
        states[:, 3072:] = 1
        states[:, 3168:3744] = random.integers(0, 128, (5,576), dtype=np.uint8)
        states[1] = states[0]
        states[3, :3072] = shifted_rows(states[2, :3072])[1]
        states[3, :384] = 0; states[3, 2688:3072] = 0
        original = states.copy()
        audio = [AyFrame((100+i,200+i,300+i), (i%16,8,9), i%32) for i in range(30)]
        _, report = encode(states, audio, fragment_byte_slack=16, row_aligned_motion=True)
        self.assertTrue(report['exact_compact_frames'] and report['exact_ay_records'])
        self.assertTrue(report['row_aligned_motion'])
        self.assertLess(report['max_payload_bytes'], 4704)
        np.testing.assert_array_equal(states, original)


if __name__ == '__main__': unittest.main()
