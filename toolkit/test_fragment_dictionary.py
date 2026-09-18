import unittest

import numpy as np

import fragment_dictionary as words
from probe_fast_fragments import encode
from probe_motion_entropy import Reader
from probe_motion_residual_order import field_order
from probe_spatial_contexts import decode, read_header
from test_hybrid_tiles import header


class FragmentDictionaryTests(unittest.TestCase):
    def test_all_widths_and_escape_positions_with_causal_neighbours(self):
        order = field_order(8).reshape(192, 20)[:, :16]
        for bits in range(8, 13):
            with self.subTest(bits=bits):
                entries = (1 << bits)-1
                blob = b''.join(i.to_bytes(2, 'little') for i in range(entries))
                lookup = np.full(65536, entries, dtype=np.uint16)
                lookup[:entries] = np.arange(entries)
                dictionary = bits, blob, lookup
                states = np.zeros((9, 3840), dtype=np.uint8)
                vectors = np.zeros((9, 192), dtype=np.uint8)
                selected = np.zeros_like(vectors, dtype=bool); selected[:, 0] = True
                for frame in range(9):
                    indices = [0, 1, entries-1, 2, 3, 4, 5, 6]
                    if frame:
                        indices[frame-1] = 60000
                    tile = b''.join(i.to_bytes(2, 'little') for i in indices)
                    states[frame, order[0]] = np.frombuffer(tile, dtype=np.uint8)
                    self.assertEqual(len(words.pack(tile, dictionary)), bits+2*bool(frame))
                    # The next tile copies its corrected left neighbour.
                    vectors[frame, 1] = 83
                    for row in range(8):
                        states[frame, row*32+2:row*32+4] = states[frame, row*32+1]
                residual = states.copy(); residual[1:] ^= states[:-1]
                residual[:, order[1]] = 0
                tables = [bytes([8]*256)]*2
                data, details = encode(header(9), states, vectors, residual, bytes(256), tables,
                    selected, dictionary=dictionary, cap=100)
                actual, frames = decode(data, fast_fragments=True, fragment_dictionary=True)
                self.assertEqual(actual, states.tobytes())
                self.assertEqual(frames, details['frames'])
                self.assertEqual(details['fast_kinds'], {89: 9})
                for malformed in (data[:-1], data+b'!', b'FHF1'+data[4:]):
                    with self.assertRaises(ValueError):
                        decode(malformed, fast_fragments=True, fragment_dictionary=True)
                r = Reader(data); read_header(r, magic=b'FHD1')
                bad = bytearray(data); bad[r.pos] = 7
                with self.assertRaisesRegex(ValueError, 'width'):
                    decode(bytes(bad), fast_fragments=True, fragment_dictionary=True)
                bad = bytearray(data); bad[r.pos+3:r.pos+5] = bad[r.pos+1:r.pos+3]
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    decode(bytes(bad), fast_fragments=True, fragment_dictionary=True)

    def test_unprofitable_tile_stays_raw_and_training_is_deterministic(self):
        rng = np.random.default_rng(128)
        states = rng.integers(0, 256, (2, 3840), dtype=np.uint8)
        selected = np.ones((2, 192), dtype=bool)
        first = words.train(states, selected, 10)
        second = words.train(states, selected, 10)
        self.assertEqual(first[:2], second[:2])
        np.testing.assert_array_equal(first[2], second[2])
        entries = 1023
        lookup = np.full(65536, entries, dtype=np.uint16)
        dictionary = 10, first[1], lookup
        data, details = encode(header(2), states, np.zeros((2, 192), dtype=np.uint8),
            np.vstack([states[:1], states[1:] ^ states[:-1]]), bytes(256), [bytes([8]*256)]*2,
            selected, dictionary=dictionary)
        self.assertNotIn(89, details['fast_kinds'])
        self.assertEqual(decode(data, fast_fragments=True, fragment_dictionary=True)[0], states.tobytes())


if __name__ == '__main__':
    unittest.main()
