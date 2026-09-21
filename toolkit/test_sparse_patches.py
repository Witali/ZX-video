import unittest
from collections import Counter
from hashlib import sha256

import numpy as np
import causal_tile_z80 as machine
from benchmark_causal_tiles import Harness, INPUT, STACK, STOP, word
from frame_output_pipeline import Harness as Pipeline, frames, serialized_masks
from probe_context_values import pack
from probe_motion_entropy import codes_for
from probe_sparse_motion_cache import coverage
from raw_attribute_stream import pack as pack_attributes
from test_causal_tiles import OFFSETS
from test_frame_output_pipeline import fixture
import test_frame_output_pipeline as pipeline_tests


class SparsePatchTests(unittest.TestCase):
    def test_every_mask_half_column_page_and_bit_cursor(self):
        seen = set()
        for width in (1, 8):
            table = bytes([1]+[0]*254+[1]) if width == 1 else bytes([8]*256)
            tables, mapping = [table]*3, bytes(i % 2 for i in range(256))
            variants = [Harness(tables, mapping, OFFSETS, hybrid=True, skip_empty=True,
                                sparse_patches=v) for v in (False, True)]
            for half in range(2):
                for mask in range(256):
                    masks = (mask, 129) if half == 0 else (129, mask)
                    tile = (mask*73+half*91) % 192
                    base = (tile//16)*256+2*(tile % 16)
                    seen.add(tile)
                    source = bytes((i*37+mask*13) & 255 for i in range(3840))
                    target = bytearray(source)
                    values, contexts = [], []
                    for j in range(16):
                        if masks[j//8] & (128 >> (j % 8)):
                            pos = base+(j//2)*32+j % 2
                            value = (255 if (j+mask) % 2 else 0) if width == 1 else (j*19+mask*3) & 255
                            target[pos] = value; values.append(value); contexts.append(mapping[source[pos]])
                    # Retain a non-byte-aligned prefix in the Huffman register.
                    prefix = mask % 8 if width == 1 else 0
                    bits, encoded = pack([0]*prefix+values, [0]*prefix+contexts,
                                         [codes_for(255, t) for t in tables])
                    counts = []
                    for sparse, h in enumerate(variants):
                        cpu = h.cpu; cpu.guarding = False
                        for address, data in ((machine.FRAME, source), (INPUT, encoded+b'\0')):
                            for i, value in enumerate(data): cpu.write8(address+i, value)
                        cpu.input_end = INPUT+len(encoded)+1
                        word(cpu, h.labels['target'], machine.FRAME+base)
                        cpu.b, cpu.c, cpu.ix, cpu.alt_c = *masks, INPUT, 0xf0+prefix
                        cpu.pc, cpu.sp = h.labels['patches_nonzero'], STACK
                        cpu.push(STOP); cpu.guarding = True; stages = Counter()
                        while cpu.pc != STOP:
                            row = h.instructions[cpu.pc]; before = cpu.tstates; cpu.step()
                            elapsed = cpu.tstates-before
                            self.assertIn(elapsed, row['tstates'] if isinstance(row['tstates'], list) else [row['tstates']])
                            stages[row['stage']] += elapsed
                        self.assertEqual(bytes(cpu.read8(machine.FRAME+i) for i in range(3840)), target)
                        self.assertEqual((cpu.ix-INPUT)*8+(cpu.alt_c & 7), bits)
                        self.assertEqual(cpu.sp, STACK)
                        expected = (20 if sparse else 24)+sum(machine.patch_half_tstates(m, n, sparse_patches=bool(sparse))
                                                             for n, m in enumerate(masks))
                        self.assertEqual(stages['patch'], expected, (sparse, masks))
                        counts.append(stages['huffman'])
                    self.assertEqual(*counts)
        self.assertEqual(seen, set(range(192)))

    def test_integrated_reconstruction_and_both_screens(self):
        states, stream, _ = fixture(4, constant_attribute_borders=True)
        stream, _ = pack_attributes(stream, states, [True, False, True, False])
        tables, mapping, packets = frames(stream); meta = serialized_masks(stream)
        opts = dict(raw_attributes=True, decode_metadata=True, fast_mask_dispatch=True,
                    selective_cache=True, constant_attribute_borders=True, skip_black_borders=True,
                    unrolled_cache=True, attribute_groups=True, attribute_flags=True, gray_cells=True)
        variants = [Pipeline(tables, mapping, sparse_patches=v, **opts) for v in (False, True)]
        for i, ((group, mask), state) in enumerate(zip(packets, states)):
            cache = np.packbits(coverage(group[3], 32).reshape(24, 4).any(axis=1)).tobytes()
            a, b = [h.run(group, mask, state.tobytes(), i, encoded_metadata=meta[i], cache_map=cache)
                    for h in variants]
            self.assertEqual(b['total_tstates']-a['total_tstates'], machine.patch_delta_tstates(group[3], group[4]))

    def test_irq_between_shift_and_last_patch_branch(self):
        pipeline_tests.FrameOutputPipelineTests().exercise_irq(raw=True, fast=True, selective=True, noops=True,
                                               constant=True, unrolled_cache=True, sparse_patches=True)

    def test_default_and_invalid_modes(self):
        args = ([bytes([8]*256)]*2, bytes(256), OFFSETS)
        self.assertEqual(machine.build(*args), machine.build(*args, sparse_patches=False))
        # Captured by executing causal_tile_z80.py from a8f28c2 with the
        # same synthetic tables. These protect the previous generated code.
        self.assertEqual(sha256(machine.build(*args)[0]).hexdigest(),
                         '72fdc10d746ba68e1a0c470aeafc6949f3d60ad70cb7d2ade8aa733e37ef6a31')
        full = dict(hybrid=True, skip_empty=True, intra_above=True, intra_extended=True,
                    fast_fragments=True, unrolled_motion=True, split_literals=True, raw_attributes=True,
                    selective_cache=True, skip_noop_runs=True, skip_static_stripes=True,
                    unrolled_cache=True, attribute_flags=True)
        self.assertEqual(sha256(machine.build(*args, **full)[0]).hexdigest(),
                         '373e515c065f17a2cc79cd22acc9a5a0fd5c1f5e5ae27e95885af848ce81471f')
        for opts in ({}, dict(hybrid=True), dict(skip_empty=True),
                     dict(hybrid=True, skip_empty=True, raw_kind=0)):
            with self.assertRaises(ValueError): machine.build(*args, sparse_patches=True, **opts)


if __name__ == '__main__': unittest.main()
