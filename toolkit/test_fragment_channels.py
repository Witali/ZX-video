import unittest

import numpy as np

import probe_fragment_channels as channels
import probe_fast_fragments as fast
from probe_motion_residual_order import field_order
from test_hybrid_tiles import header
import test_fast_fragments as fixtures
import test_causal_tiles as causal_tests
from benchmark_causal_tiles import Harness
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, read_group, OFFSETS


class FragmentChannelTests(unittest.TestCase):
    def execute(self, data, states, *, split):
        reader = Reader(data)
        _, _, remaining, mapping, tables = read_header(reader, magic=b'FSF1' if split else b'FHF1')
        h = Harness(tables, mapping, OFFSETS, hybrid=True, skip_empty=True, intra_above=True,
                    intra_extended=True, fast_fragments=True, unrolled_motion=True, split_literals=split)
        index, rows = 0, []
        while remaining:
            n, _, bits, v, bm, at, encoded = read_group(reader, remaining, fast_fragments=True)
            literal = reader.take(sum(fast.SIZES.get(mode, 0) for mode in v)) if split else None
            h.begin(encoded, v, bm, at, literals=literal)
            for frame in range(n):
                rows.append(h.run(frame, states[index+frame].tobytes()))
            self.assertEqual(h.position(), bits)
            if split:
                self.assertEqual(h.literal_position(), len(literal))
            index += n; remaining -= n
        reader.end()
        return rows

    def test_mixed_groups_restore_exact_original_bytes_and_pixels(self):
        states, vectors, residual, selected = fixtures.FastFragmentTests().fixture(9)
        source, _ = fast.encode(header(9), states, vectors, residual, bytes(256), [bytes([8]*256)]*2,
                                selected, cap=4500)
        data, groups = channels.split(source, states, vectors, residual)
        restored, pixels = channels.restore(data)
        self.assertEqual(restored, source); self.assertEqual(pixels, states.tobytes())
        self.assertGreater(len(groups), 2)
        before, after = self.execute(source, states, split=False), self.execute(data, states, split=True)
        for old, new in zip(before, after):
            self.assertEqual(new['total_tstates']-old['total_tstates'], -54*old['fast_tiles'])
            for stage in set(old['stages']) | set(new['stages']):
                if stage != 'fast_fragment':
                    self.assertEqual(old['stages'].get(stage, 0), new['stages'].get(stage, 0))
        for invalid in (data[:-1], data+b'!', b'FHF1'+data[4:]):
            with self.assertRaises(ValueError):
                channels.restore(invalid)

    def test_partial_bits_and_empty_channel_extremes(self):
        order = field_order(8).reshape(192, 20)[:, :16]
        table = bytes([1]+[0]*254+[1])
        for all_fast, any_fast in ((False, False), (False, True), (True, True)):
            states = np.zeros((1, 3840), dtype=np.uint8)
            states[0, 0] = 255; states[0, order[1]] = 255
            if not all_fast:
                states[0, 3072] = 255
            vectors = np.zeros((1, 192), dtype=np.uint8)
            selected = np.full_like(vectors, all_fast, dtype=bool)
            selected[0, 1] = any_fast
            source, _ = fast.encode(header(1), states, vectors, states.copy(), bytes(256), [table]*2, selected)
            data, groups = channels.split(source, states, vectors, states.copy())
            restored, pixels = channels.restore(data)
            self.assertEqual(restored, source); self.assertEqual(pixels, states.tobytes())
            old = self.execute(source, states, split=False)[0]
            new = self.execute(data, states, split=True)[0]
            self.assertEqual(new['stages'].get('fast_fragment', 0)-old['stages'].get('fast_fragment', 0),
                             -54*old['fast_tiles']-10*old['fast_unaligned'])
            if all_fast:
                self.assertEqual(groups[0]['huffman_bits'], 0)
            elif any_fast:
                self.assertEqual(groups[0]['removed_alignment_bits'], 7)
                self.assertLess(len(data), len(source))
            else:
                self.assertEqual(groups[0]['literal_bytes'], 0)

    def test_irq_preserves_both_input_cursors(self):
        states, vectors, residual, selected = fixtures.FastFragmentTests().fixture(1)
        source, _ = fast.encode(header(1), states, vectors, residual, bytes(256), [bytes([8]*256)]*2, selected)
        data, _ = channels.split(source, states, vectors, residual)
        causal_tests.CausalTileTests().exercise_irq(True, spatial_data=data, spatial_extended=True,
            fast_fragments=True, unrolled_motion=True, split_literals=True)


if __name__ == '__main__':
    unittest.main()
