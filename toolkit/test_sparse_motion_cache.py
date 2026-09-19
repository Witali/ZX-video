import unittest

import numpy as np

from probe_sparse_motion_cache import coverage, verify_cache, pack, unpack
from cell_audio_stream import pack as add_audio
from raw_attribute_stream import pack as attributes
from test_frame_output_pipeline import fixture


class SparseMotionCacheTests(unittest.TestCase):
    def test_all_vectors_and_edges_with_dirty_unused_slots(self):
        previous = np.random.default_rng(20260919).integers(1, 256, 3840, dtype=np.uint8).tobytes()
        for vector in range(1, 81):
            vectors = bytes([vector])*192
            for chunk in (8, 32):
                flags = coverage(vectors, chunk)
                self.assertGreater(verify_cache(previous, vectors, flags, chunk), 0)
        empty = coverage(bytes(192))
        self.assertFalse(empty.any())
        self.assertEqual(verify_cache(previous, bytes(192), empty, 8), 0)
        vectors = bytes([1])*192
        flags = coverage(vectors)
        flags[:] = 0
        with self.assertRaisesRegex(AssertionError, 'selective cache differs'):
            verify_cache(previous, vectors, flags, 8)

    def test_video_audio_roundtrip_and_truncated_input(self):
        states, source, _ = fixture(2)
        source, _ = attributes(source, states, [True, False])
        source = add_audio(source, b'\0'*12)
        for chunk, group in ((8, 1), (32, 1), (32, 4)):
            encoded, rows = pack(source, states, chunk, group)
            self.assertEqual(unpack(encoded, chunk, group), source)
            self.assertEqual(len(rows), 2)
            for bad in (encoded[:-1], encoded+b'!'):
                with self.assertRaises(ValueError):
                    unpack(bad, chunk, group)


if __name__ == '__main__':
    unittest.main()
