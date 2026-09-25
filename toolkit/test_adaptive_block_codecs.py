import random
import unittest
from itertools import product

import disk_layout
from benchmark_adaptive_zx0 import choose_cpu, stream_capacity
from probe_adaptive_block_codecs import geometry, rle_decode, rle_encode, selection


class AdaptiveCodecTests(unittest.TestCase):
    def test_cpu_selection_matches_exhaustive_search(self):
        rng = random.Random(442)
        for _ in range(30):
            groups = [[dict(name=str(n), bytes=rng.randrange(4, 30), tstates=rng.randrange(20, 100))
                       for n in range(3)] for _ in range(4)]
            capacity = sum(min(row['bytes'] for row in group) for group in groups)+10
            oracle = min((sum(r['tstates'] for r in rows), sum(r['bytes'] for r in rows))
                         for rows in product(*groups) if sum(r['bytes'] for r in rows) <= capacity)
            result = choose_cpu(groups, capacity)
            self.assertEqual((result['decoder_tstates'], result['stream_bytes']), oracle)
        with self.assertRaises(ValueError):
            choose_cpu([[dict(name='a', bytes=10, tstates=1)]], 9)

    def test_capacity_is_maximum_with_physical_holes(self):
        for start in (55, 59, 62):
            capacity = stream_capacity(start)
            self.assertLessEqual(geometry(capacity, start)['fixed_bootstrap_used_sectors'], 2544)
            self.assertGreater(geometry(capacity+1, start)['fixed_bootstrap_used_sectors'], 2544)

    def test_rle_literal_and_run_boundaries(self):
        rng = random.Random(982)
        for length in (0, 1, 2, 3, 127, 128, 129, 255, 256, 8192):
            for raw in (b'x'*length, bytes(i % 256 for i in range(length)), rng.randbytes(length)):
                self.assertEqual(rle_decode(rle_encode(raw), len(raw)), raw)
        raw = bytes(range(127))+b'x'*257+b'ab'+b'y'*3+bytes(range(128))
        self.assertEqual(rle_decode(rle_encode(raw), len(raw)), raw)

    def test_rle_rejects_malformed_or_wrong_length(self):
        for packed, length in ((b'\x80', 1), (b'\x02ab', 3), (b'\xffx', 127),
                               (b'\x00a', 2), (b'\x00a\x00b', 1)):
            with self.assertRaises(ValueError):
                rle_decode(packed, length)

    def test_geometry_includes_interleave_holes(self):
        for start in (55, 62, 63, 64):
            for size in (1, 255, 256, 257, 4095, 4096, 4097):
                result = geometry(size, start)
                physical = len(disk_layout.arrange(bytes((size+255)//256*256), start % 16))//256
                self.assertEqual(result['physical_video_sectors'], physical)
                self.assertEqual(result['fixed_bootstrap_used_sectors'], start-16+physical)
        self.assertEqual(geometry(641005, 55)['fixed_bootstrap_used_sectors'], 2543)

    def test_choice_obeys_slot_limit_tie_order_and_tag_cost(self):
        rows = [{'candidates': {'zx0': {'bytes': 4, 'slot_fits': True},
                                'other': {'bytes': 1, 'slot_fits': False}}},
                {'candidates': {'zx0': {'bytes': 2, 'slot_fits': True},
                                'other': {'bytes': 2, 'slot_fits': True}}},
                {'candidates': {'zx0': {'bytes': 5, 'slot_fits': True},
                                'other': {'bytes': 3, 'slot_fits': True}}}]
        result = selection(rows, ('zx0', 'other'), tag_bytes=1, mixed=True)
        self.assertEqual(result['selected_codecs'], ['zx0', 'zx0', 'other'])
        self.assertEqual(result['stream_bytes'], 24)
        self.assertIsNone(selection(rows, ('other',), tag_bytes=0))


if __name__ == '__main__':
    unittest.main()
