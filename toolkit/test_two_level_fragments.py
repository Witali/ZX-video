"""Independent pixel checks for the experimental palette/mask representation."""
import itertools
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from build_fap3_trd import Builder
from probe_two_level_fragments import pack_tile, unpack_tile, measure_zx0, sha


class TwoLevelTests(unittest.TestCase):
    def test_all_palettes_and_all_row_masks(self):
        # Exercise all 256 masks at every row and all six unordered palettes.
        for low, high in itertools.combinations(range(4), 2):
            for row in range(8):
                for mask in range(256):
                    masks = [0x55]*8
                    masks[row] = mask
                    encoded = bytes([low << 2 | high]+masks)
                    decoded = unpack_tile(encoded)
                    pixels = [value >> shift & 3 for value in decoded for shift in (6, 4, 2, 0)]
                    expected = [high if value & (128 >> x) else low for value in masks for x in range(8)]
                    self.assertEqual(pixels, expected)
                    self.assertEqual(pack_tile(decoded), encoded)

    def test_random_masks_roundtrip(self):
        rng = random.Random(20260924)
        for low, high in itertools.combinations(range(4), 2):
            for _ in range(100):
                encoded = bytes([low << 2 | high]+[rng.randrange(256) for _ in range(8)])
                self.assertEqual(pack_tile(unpack_tile(encoded)), encoded)

    def test_other_levels_and_bad_payloads(self):
        for fragment in (bytes(16), bytes([255])*16, bytes([0x1b])*16):
            self.assertIsNone(pack_tile(fragment))
        for encoded in (bytes(8), bytes(10), bytes(9), bytes([0x12])+bytes(8), bytes([0x0c])+bytes(8)):
            with self.assertRaises(ValueError):
                unpack_tile(encoded)
        with self.assertRaises(ValueError):
            pack_tile(bytes(15))

    def test_compression_framing_matches_trd_builder(self):
        # Catch accidental compression of startup tables or shifting chunk
        # boundaries by the header length. Identity compression isolates framing.
        raw = bytes(range(256))*71
        for header_size in (1741, 4813, 8192, 9001):
            fixture = SimpleNamespace(raw=raw, offsets=[header_size, len(raw)], compress=bytes)
            expected, blocks = Builder.stream(fixture, 0, 1)
            def skip_header(reader, **_):
                reader.take(header_size)
            with tempfile.TemporaryDirectory() as cache, \
                    patch('probe_two_level_fragments.read_header', side_effect=skip_header), \
                    patch('probe_two_level_fragments.compress_chunk', side_effect=lambda data, *args: data):
                measured = measure_zx0(raw, Path('unused'), Path(cache), 8192)
            self.assertEqual(measured['stream_sha256'], sha(expected))
            self.assertEqual(measured['stream_bytes'], len(expected))
            self.assertEqual(measured['block_count'], len(blocks))


if __name__ == '__main__':
    unittest.main()
