"""FHC1 spatial fusion: causal bytes, exact timing, mixed modes and AY IRQ."""
import struct
import unittest

import numpy as np

from benchmark_causal_tiles import Harness
import probe_fast_fragments as fast
import probe_spatial_contexts as spatial
from probe_motion_entropy import Reader
from probe_motion_metadata import transform
from probe_motion_residual_order import field_order
from test_hybrid_tiles import header
import test_causal_tiles as causal_tests


def fixture(count=4):
    rng = np.random.default_rng(821283)
    states = np.zeros((count, 3840), dtype=np.uint8)
    residual = np.zeros_like(states)
    vectors = np.zeros((count, 192), dtype=np.uint8)
    raw = np.zeros_like(vectors, dtype=bool)
    selected = np.zeros_like(raw)
    order = field_order(8).reshape(192, 20)[:, :16]
    masks = [1 << i for i in range(16)]+[65535 ^ (1 << i) for i in range(16)]+[255, 65280, 43690, 21845, 65535]
    for frame in range(count):
        previous = states[frame-1] if frame else np.zeros(3840, dtype=np.uint8)
        for tile in range(192):
            vector = 82+(tile+frame) % 3
            vectors[frame, tile] = vector
            raw[frame, tile] = (tile+frame) % 5 != 0
            mask = masks[(tile+frame*13) % len(masks)]
            for field, address in enumerate(order[tile]):
                y, x = divmod(int(address), 32)
                source = ((address-32 if y else None) if vector == 82 else
                          (address-1 if x else None) if vector == 83 else (address-64 if y >= 2 else None))
                predicted = int(states[frame, source]) if source is not None else 0
                value = predicted ^ (int(rng.integers(1, 256)) if mask & (32768 >> field) else 0)
                states[frame, address] = value; residual[frame, address] = value ^ predicted
            if tile % 13 == 0:
                vectors[frame, tile] = 0; raw[frame, tile] = False
                residual[frame, order[tile]] = states[frame, order[tile]] ^ previous[order[tile]]
            # Complete fragments share the input with marked and Huffman tiles.
            if tile % 11 == 0:
                selected[frame, tile] = True; raw[frame, tile] = False
        states[frame, 3072:] = rng.integers(0, 256, 768, dtype=np.uint8)
        residual[frame, 3072:] = states[frame, 3072:] ^ previous[3072:]
    return states, vectors, residual, selected, raw


class RawIntraTests(unittest.TestCase):
    def execute(self, data, states, *, enabled=True):
        reader = Reader(data)
        _, _, remaining, mapping, tables = spatial.read_header(reader, magic=b'FHC1')
        h = Harness(tables, mapping, spatial.OFFSETS, hybrid=True, skip_empty=True,
            intra_above=True, intra_extended=True, fast_fragments=True, unrolled_motion=True, raw_intra=enabled)
        first, result = 0, []
        while remaining:
            n, _, bits, v, bm, at, encoded = spatial.read_group(reader, remaining, fast_fragments=True, raw_intra=True)
            h.begin(encoded, v, bm, at)
            for i in range(n):
                result.append(h.run(i, states[first+i].tobytes()))
            self.assertEqual(h.position(), bits)
            first += n; remaining -= n
        reader.end()
        return result

    def test_sparse_dense_masks_boundaries_and_mixed_stream(self):
        states, vectors, residual, selected, raw = fixture(9)
        data, detail = fast.encode(header(9), states, vectors, residual, bytes(256),
            [bytes([8]*256)]*2, selected, cap=4500, raw_intra=raw)
        restored, rows = spatial.decode(data, fast_fragments=True, raw_intra=True)
        self.assertEqual(restored, states.tobytes()); self.assertEqual(rows, detail['frames'])
        cpu = self.execute(data, states)
        self.assertEqual(sum(r['raw_intra_tiles'] for r in cpu), detail['raw_intra_tiles'])
        self.assertEqual(sum(r['raw_intra_values'] for r in cpu), detail['raw_intra_values'])
        self.assertEqual(sum(r['values'] for r in cpu), sum(r['values'] for r in rows))
        self.assertGreater(len(detail['groups']), 2)

    def test_disabled_binary_and_added_dispatch(self):
        states, vectors, residual, selected, raw = fixture(2)
        raw[:] = False
        data, _ = fast.encode(header(2), states, vectors, residual, bytes(256), [bytes([8]*256)]*2,
                              selected, raw_intra=raw)
        control, _ = fast.encode(header(2), states, vectors, residual, bytes(256), [bytes([8]*256)]*2, selected)
        self.assertEqual(data[4:], control[4:])
        before, after = self.execute(data, states, enabled=False), self.execute(data, states)
        for i, (old, new) in enumerate(zip(before, after)):
            self.assertEqual(new['total_tstates']-old['total_tstates'],
                             18*int(((vectors[i] >= 82) & ~selected[i]).sum())+28*int(selected[i].sum()))
            for stage in set(old['stages']) | set(new['stages']):
                if stage != 'control':
                    self.assertEqual(old['stages'].get(stage, 0), new['stages'].get(stage, 0))

    def test_full_mask_exact_old_and_new_body_cycles(self):
        states = np.zeros((1, 3840), dtype=np.uint8)
        order = field_order(8).reshape(192, 20)[:, :16]
        states[0, order[16]] = np.arange(1, 17)
        vectors = np.zeros((1, 192), dtype=np.uint8); vectors[0, 16] = 82
        residual = states.copy()
        for address in order[16]:
            residual[0, address] ^= states[0, address-32]
        raw = np.zeros_like(vectors, dtype=bool); raw[0, 16] = True
        before, _ = fast.encode(header(1), states, vectors, residual, bytes(256), [bytes([8]*256)]*2,
                                np.zeros_like(raw), raw_intra=np.zeros_like(raw))
        after, _ = fast.encode(header(1), states, vectors, residual, bytes(256), [bytes([8]*256)]*2,
                               np.zeros_like(raw), raw_intra=raw)
        old = self.execute(before, states, enabled=False)[0]
        new = self.execute(after, states)[0]
        self.assertEqual(old['stages']['huffman'], 16*173)
        self.assertEqual(old['stages']['intra']+old['stages']['huffman'], 4301)
        self.assertEqual(new['stages']['raw_intra'], 1351)
        self.assertEqual(new['total_tstates']-old['total_tstates'], -2959)

    def test_padding_truncation_and_illegal_flags(self):
        states = np.zeros((1, 3840), dtype=np.uint8)
        states[0, 0:3] = 255
        vectors = np.zeros((1, 192), dtype=np.uint8); vectors[0, 1] = 82
        residual = states.copy(); residual[0, 34] = 255
        raw = np.zeros_like(vectors, dtype=bool); raw[0, 1] = True
        table = bytes([1]+[0]*254+[1])
        data, detail = fast.encode(header(1), states, vectors, residual, bytes(256), [table]*2,
                                  np.zeros_like(raw), raw_intra=raw)
        self.assertEqual(spatial.decode(data, fast_fragments=True, raw_intra=True)[0], states.tobytes())
        self.assertEqual(self.execute(data, states)[0]['raw_intra_unaligned'], 1)
        r = Reader(data); spatial.read_header(r, magic=b'FHC1')
        *_, encoded = spatial.read_group(r, 1, fast_fragments=True, raw_intra=True)
        bad = bytearray(data); bad[r.pos-len(encoded)] |= 1
        for invalid in (bytes(bad), data[:-1], data+b'!'):
            with self.assertRaises(ValueError):
                spatial.decode(invalid, fast_fragments=True, raw_intra=True)
        for vector, mask in ((128, 128), (209, 128), (213, 128), (210, 0)):
            vv = transform(bytes([vector])+bytes(191), 192, 2)
            mm = transform(bytes([mask])+bytes(479), 480, 4)
            group = struct.pack('<HHHBI', 1, len(vv), len(mm), 0, 8)+vv+mm+b'\0'
            with self.assertRaises(ValueError):
                spatial.read_group(Reader(group), 1, fast_fragments=True, raw_intra=True)

    def test_ay_irq_between_every_instruction(self):
        states, vectors, residual, selected, raw = fixture(1)
        data, _ = fast.encode(header(1), states, vectors, residual, bytes(256), [bytes([8]*256)]*2,
                              selected, raw_intra=raw)
        causal_tests.CausalTileTests().exercise_irq(True, spatial_data=data, spatial_extended=True,
                                               fast_fragments=True, unrolled_motion=True, raw_intra=True)


if __name__ == '__main__':
    unittest.main()
