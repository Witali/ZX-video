"""Check splice dependencies, frame/tick boundaries and preservation of EOF."""
import struct
import unittest

import numpy as np

import build_long_video_trd as video
from prepare_edited_movie import edit, frame_map, legacy_stream
from repack_edited_fragments import splice_arrays
from probe_fast_fragments import encode
from probe_fragment_channels import split, restore
from probe_hybrid_tiles import OFFSETS


class MovieEditTests(unittest.TestCase):
    def test_splice_preserves_every_tick_and_last_frame(self):
        states = np.arange(6*3840, dtype=np.uint8).reshape(6, 3840)
        ticks = [video.AyFrame((100+i, 200+i, 300+i), (i % 16, 8, 3), i % 32).serialize()
                 for i in range(36)]
        kept, sound, indices = edit(states, b''.join(ticks), [[1, 4]])
        self.assertEqual(indices.tolist(), [0, 4, 5])
        self.assertTrue(np.array_equal(kept, states[[0, 4, 5]]))
        self.assertEqual(sound, b''.join(ticks[:6]+ticks[24:]))
        self.assertEqual(sound[-9:], ticks[-1])
        with self.assertRaises(ValueError):
            edit(states, b''.join(ticks[:-1]), [[1, 4]])

    def test_invalid_edits_are_rejected(self):
        for cuts in ([[0, 6]], [[-1, 2]], [[2, 2]], [[1, 7]], [[2, 4], [3, 5]], [[1.5, 2]]):
            with self.subTest(cuts=cuts), self.assertRaises(ValueError):
                frame_map(6, cuts)

    def test_splice_rebuilds_legacy_delta(self):
        states = np.zeros((6, 3840), dtype=np.uint8)
        states[1:4] = 85  # Deleted predecessor differs from the retained one.
        states[4:, :3072] = 255
        sound = video.AyFrame((200, 300, 400), (1, 2, 3), 7).serialize()*36
        kept, audio, _ = edit(states, sound, [[1, 4]])
        stream, packets = legacy_stream(kept, audio)
        video.verify_video(stream, [s.tobytes() for s in kept])
        self.assertEqual(len(packets), 3)
        self.assertEqual(int.from_bytes(stream[8:10], 'little'), 3)
        self.assertEqual(packets[1].ay_state, audio[54:63])

    def test_fsf_splice_does_not_depend_on_deleted_screen(self):
        rng = np.random.default_rng(70919)
        states = rng.integers(0, 256, (6, 3840), dtype=np.uint8)
        states[:, 3072:] &= 127
        residual = states.copy()
        residual[1:] ^= states[:-1]
        vectors = np.zeros((6, 192), dtype=np.uint8)
        selected = np.zeros((6, 192), dtype=bool)
        indices = frame_map(6, [[1, 4]])
        kept, vv, rr, chosen, boundaries = splice_arrays(states, vectors, residual, selected, indices)
        self.assertEqual(boundaries.tolist(), [1])
        self.assertTrue(np.array_equal(rr[1, 3072:], states[4, 3072:] ^ states[0, 3072:]))
        header = (b'FPR1'+bytes(range(16))+b'FMO1\x08FMR1\x08'+bytes([len(OFFSETS)])
                  +struct.pack('<I', len(kept))+b''.join(struct.pack('<bb', *o) for o in OFFSETS))
        interleaved, _ = encode(header, kept, vv, rr, bytes(256), [bytes([8]*256)]*2, chosen)
        data, _ = split(interleaved, kept, vv, rr)
        rebuilt, actual = restore(data)
        self.assertEqual(actual, kept.tobytes())
        self.assertEqual(rebuilt, interleaved)


if __name__ == '__main__':
    unittest.main()
