import struct
import unittest

import numpy as np

import probe_fast_fragments as fast
import probe_spatial_contexts as spatial
from probe_motion_entropy import Reader
from probe_motion_metadata import transform
from probe_motion_residual_order import field_order
from test_hybrid_tiles import header
from benchmark_causal_tiles import Harness
import test_causal_tiles as causal_tests


class FastFragmentTests(unittest.TestCase):
    def test_target_selection_keeps_cheap_frames_and_accounts_for_dispatch(self):
        vectors = np.zeros((3, 192), dtype=np.uint8)
        vectors[1, 0] = 82
        gains = np.full((3, 192), -1)
        gains[:, :2] = [100, 200]
        prof = dict(estimated_gains=gains, extra_bits=np.full((3, 192), 8))
        selected, info = fast.select_target(prof, vectors, [10, 501, 1000], 300)
        self.assertFalse(selected[0].any())
        self.assertEqual(np.flatnonzero(selected[1]).tolist(), [0, 1])
        self.assertEqual(np.flatnonzero(selected[2]).tolist(), [0, 1])
        self.assertEqual(info['estimated_max_frame_tstates'], 700)
        self.assertEqual(info['estimated_frames_over_target'], 1)

    def run_z80(self, data, states, *, enabled=True):
        r = Reader(data)
        _, _, remaining, mapping, tables = spatial.read_header(r, magic=b'FHF1')
        h = Harness(tables, mapping, spatial.OFFSETS, hybrid=True, skip_empty=True,
                    intra_above=True, intra_extended=True, fast_fragments=enabled)
        index, rows = 0, []
        while remaining:
            n, _, bits, v, bm, at, encoded = spatial.read_group(r, remaining, fast_fragments=True)
            h.begin(encoded, v, bm, at)
            for i in range(n):
                rows.append(h.run(i, states[index+i].tobytes()))
            self.assertEqual(h.position(), bits)
            remaining -= n; index += n
        r.end()
        return rows

    def fixture(self, count=3):
        rng = np.random.default_rng(8588)
        states = rng.integers(0, 256, (count, 3840), dtype=np.uint8)
        order = field_order(8).reshape(192, 20)[:, :16]
        patterns = [bytes(range(16)), bytes([0x12, 0xab])*8,
                    b''.join(bytes([0x15, 0x51]) if r in (0, 2, 5) else bytes([0x6c, 0xc6]) for r in range(8)), bytes([0x39])*16]
        selected = np.zeros((count, 192), dtype=bool)
        for frame in range(count):
            for tile in range(0, 192, 3):
                states[frame, order[tile]] = np.frombuffer(patterns[(tile//3+frame) % 4], dtype=np.uint8)
                selected[frame, tile] = True
        vectors = np.zeros((count, 192), dtype=np.uint8)
        residual = states.copy(); residual[1:] ^= states[:-1]
        # Intra tiles follow reconstructed fragment rows/columns.
        for frame in range(count):
            for tile in range(1, 192, 3):
                mode = 82+(tile//3+frame) % 3
                vectors[frame, tile] = mode
                for address in order[tile]:
                    y, x = divmod(int(address), 32)
                    source = (address-32 if y else None) if mode == 82 else ((address-1 if x else None) if mode == 83 else (address-64 if y >= 2 else None))
                    residual[frame, address] = states[frame, address] ^ (states[frame, source] if source is not None else 0)
        return states, vectors, residual, selected

    def test_all_fragment_modes_and_causal_neighbours(self):
        states, vectors, residual, selected = self.fixture(9)
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        data, detail = fast.encode(header(9), states, vectors, residual, mapping, tables, selected, cap=4500)
        actual, rows = spatial.decode(data, fast_fragments=True)
        self.assertEqual(actual, states.tobytes()); self.assertEqual(rows, detail['frames'])
        self.assertEqual(set(detail['fast_kinds']), {85, 86, 87, 88})
        self.run_z80(data, states)
        self.assertGreater(len(detail['groups']), 2)
        self.assertLessEqual(max(g['encoded_bytes'] for g in detail['groups']), 4500)
        for bad in (data[:-1], data+b'!', b'FHS1'+data[4:]):
            with self.assertRaises(ValueError):
                spatial.decode(bad, fast_fragments=True)

    def test_control_is_the_original_stream_except_magic(self):
        states, vectors, residual, selected = self.fixture()
        selected[:] = False
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        data, _ = fast.encode(header(3), states, vectors, residual, mapping, tables, selected)
        old, _ = spatial.encode(header(3), states, vectors, residual, 0, mapping, tables)
        self.assertEqual(b'FHS1'+data[4:], old)
        self.assertEqual(spatial.decode(data, fast_fragments=True)[0], states.tobytes())
        before = self.run_z80(data, states, enabled=False)
        after = self.run_z80(data, states)
        for frame, (old, new) in enumerate(zip(before, after)):
            self.assertEqual(new['total_tstates']-old['total_tstates'], 27*int(np.count_nonzero(vectors[frame] >= 82)))

    def test_inline_padding_and_fast_masks_are_validated(self):
        states = np.zeros((1, 3840), dtype=np.uint8)
        order = field_order(8).reshape(192, 20)[:, :16]
        states[0, 0] = 255
        states[0, order[1]] = 255
        selected = np.zeros((1, 192), dtype=bool); selected[0, 1] = True
        table = bytes([1]+[0]*254+[1])
        data, _ = fast.encode(header(1), states, np.zeros((1, 192), dtype=np.uint8), states.copy(), bytes(256), [table]*2, selected)
        self.assertEqual(spatial.decode(data, fast_fragments=True)[0], states.tobytes())
        rows = self.run_z80(data, states)
        self.assertEqual(rows[0]['fast_unaligned'], 1)
        r = Reader(data); spatial.read_header(r, magic=b'FHF1')
        _, _, _, _, _, _, payload = spatial.read_group(r, 1, fast_fragments=True)
        start = r.pos-len(payload)
        bad = bytearray(data); bad[start] |= 1
        with self.assertRaisesRegex(ValueError, 'padding'):
            spatial.decode(bytes(bad), fast_fragments=True)
        v = transform(bytes([85])+bytes(191), 192, 2)
        m = transform(bytes([128])+bytes(479), 480, 4)
        malformed = struct.pack('<HHHBI', 1, len(v), len(m), 0, 128)+v+m+bytes(16)
        with self.assertRaisesRegex(ValueError, 'corrections'):
            spatial.read_group(Reader(malformed), 1, fast_fragments=True)

    def test_irq_preserves_palette_selector_and_mixed_input(self):
        states, vectors, residual, selected = self.fixture(2)
        tables = [bytes([8]*256)]*2
        data, _ = fast.encode(header(2), states, vectors, residual, bytes(256), tables, selected)
        causal_tests.CausalTileTests.exercise_irq(self, True, spatial_data=data, spatial_extended=True, fast_fragments=True)


if __name__ == '__main__':
    unittest.main()
