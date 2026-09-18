import unittest

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
import test_causal_tiles as causal_tests
from test_causal_tiles import OFFSETS, predict, group
from validate_fast_sparse import CPU


class UnrolledMotionTests(unittest.TestCase):
    def test_rotate_a_opcode_for_every_byte_and_flag_state(self):
        cpu = CPU(b'', b'')
        for opcode in (0x07, 0x0f):
            cpu.write8(0x8000, opcode)
            for value in range(256):
                for zero in (False, True):
                    for carry in (False, True):
                        cpu.a, cpu.z, cpu.carry, cpu.pc = value, zero, carry, 0x8000
                        ticks = cpu.tstates; cpu.step()
                        expected = ((value << 1) | (value >> 7)) & 255 if opcode == 7 else (value >> 1) | ((value & 1) << 7)
                        expected_carry = bool(value & (128 if opcode == 7 else 1))
                        self.assertEqual((cpu.a, cpu.z, cpu.carry, cpu.pc, cpu.tstates-ticks),
                                         (expected, zero, expected_carry, 0x8001, 4))

    def test_all_vectors_causal_masks_and_instruction_timing(self):
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        old = Harness(tables, mapping, OFFSETS, skip_empty=True)
        new = Harness(tables, mapping, OFFSETS, skip_empty=True, unrolled_motion=True)
        rng = np.random.default_rng(816128)
        previous = bytes(3840)
        phases, dy_classes, seen = set(), set(), set()
        for frame in range(6):
            vectors = bytes((tile+frame*31) % 82 for tile in range(192))
            current = bytearray(predict(previous, vectors))
            for address in range(3840):
                if frame == 0 or (address+frame) % 7 == 0:
                    current[address] ^= int(rng.integers(1, 256))
            current = bytes(current)
            bits, encoded, v, bm, at = group(previous, [vectors], [current], tables, mapping)
            results = []
            for h in (old, new):
                h.begin(encoded, v, bm, at)
                results.append(h.run(0, current))
                self.assertEqual(h.position(), bits)
            expected_delta = sum(machine.motion_tstates(v, OFFSETS, unrolled=True)
                                 -machine.motion_tstates(v, OFFSETS) for v in vectors if v)
            self.assertEqual(results[1]['total_tstates']-results[0]['total_tstates'], expected_delta)
            self.assertLess(expected_delta, 0)
            for v in vectors:
                seen.add(v)
                if 0 < v < 81:
                    phases.add(2*((-OFFSETS[v][0]) % 4)); dy_classes.add(OFFSETS[v][1] % 4)
            previous = current
        self.assertEqual(seen, set(range(82)))
        self.assertEqual(phases, {0, 2, 4, 6}); self.assertEqual(dy_classes, {0, 1, 2, 3})

    def test_irq_preserves_alternate_output_pointer(self):
        causal_tests.CausalTileTests.exercise_irq(self, True, unrolled_motion=True)


if __name__ == '__main__':
    unittest.main()
