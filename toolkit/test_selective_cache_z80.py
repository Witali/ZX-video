import unittest

import numpy as np

from benchmark_compact_screen import NativeCPU, STACK, STOP
from benchmark_context_huffman import word
from causal_tile_z80 import build, CODE, CACHE, CACHE_MAP
from frame_output_pipeline import Harness, frames, serialized_masks
from probe_spatial_contexts import OFFSETS
from probe_sparse_motion_cache import coverage
from raw_attribute_stream import pack
from test_frame_output_pipeline import fixture
import test_frame_output_pipeline as pipeline_tests


class SelectiveCacheTests(unittest.TestCase):
    def test_each_group_bit_and_copy_cursor_cycles(self):
        code, labels, listing, _ = build([bytes([8]*256)]*2, bytes(256), OFFSETS,
            hybrid=True, selective_cache=True)
        instructions = {r['address']: r for r in listing}
        for bits in (0, (1 << 24)-1, *[1 << i for i in range(24)]):
            cpu = NativeCPU(b'', b'')
            for i, value in enumerate(code): cpu.write8(CODE+i, value)
            original = bytes((i*71+29) & 255 for i in range(3072))
            for i, value in enumerate(original): cpu.write8(0x6400+i, value)
            for i in range(1024): cpu.write8(CACHE+i, 0xa5)
            for i, value in enumerate(bits.to_bytes(3, 'big')): cpu.write8(CACHE_MAP+i, value)
            word(cpu, labels['cache_mask_source'], CACHE_MAP)
            cpu.write8(labels['cache_mask_shift'], 128)
            cpu.set_hl(0x6400); cpu.set_de(CACHE+1)
            expected = bytearray(b'\xa5'*1024)
            total, source_group = 0, 0
            for rows in [12]+[8]*10+[4]:
                cpu.b, cpu.c = rows, 0x35
                cpu.pc, cpu.sp = labels['cache_copy'], STACK; cpu.push(STOP)
                start = cpu.tstates
                while cpu.pc != STOP:
                    before, pc = cpu.tstates, cpu.pc
                    cpu.step()
                    wanted = instructions[pc]['tstates']
                    self.assertIn(cpu.tstates-before, wanted if isinstance(wanted, list) else [wanted])
                total += cpu.tstates-start
                for group in range(source_group, source_group+rows//4):
                    if bits & (1 << (23-group)):
                        for row in range(group*4, group*4+4):
                            target = (row % 16)*64+1
                            expected[target:target+32] = original[row*32:row*32+32]
                source_group += rows//4
                self.assertEqual(cpu.hl(), 0x6400+source_group*128)
                self.assertEqual(cpu.de(), CACHE+(source_group % 4)*256+1)
                self.assertEqual(cpu.bc(), 0x35)
                self.assertEqual(cpu.sp, STACK)
                self.assertEqual(bytes(cpu.read8(CACHE+i) for i in range(1024)), expected)
            self.assertEqual(total, 3795+2305*bits.bit_count())
            self.assertEqual(word(cpu, labels['cache_mask_source']), CACHE_MAP+3)
            self.assertEqual(cpu.read8(labels['cache_mask_shift']), 128)

    def test_shared_pipeline_matches_baseline_and_exact_delta(self):
        states, stream, _ = fixture(4)
        stream, _ = pack(stream, states, [True, False, False, True])
        tables, mapping, packets = frames(stream)
        masks = serialized_masks(stream)
        old = Harness(tables, mapping, raw_attributes=True, decode_metadata=True, fast_mask_dispatch=True)
        new = Harness(tables, mapping, raw_attributes=True, decode_metadata=True,
                      fast_mask_dispatch=True, selective_cache=True)
        for i, ((group, mask), state) in enumerate(zip(packets, states)):
            flags = np.packbits(coverage(group[3], 32).reshape(24, 4).any(axis=1)).tobytes()
            before = old.run(group, mask, state.tobytes(), i, encoded_metadata=masks[i])
            after = new.run(group, mask, state.tobytes(), i, encoded_metadata=masks[i], cache_map=flags)
            delta = 3589-2305*(24-sum(v.bit_count() for v in flags)) if group[1] & 128 else 0
            self.assertEqual(after['total_tstates']-before['total_tstates'], delta)

    def test_irq_preserves_selective_copy_and_new_stack_depth(self):
        pipeline_tests.FrameOutputPipelineTests().exercise_irq(raw=True, fast=True, selective=True)


if __name__ == '__main__':
    unittest.main()
