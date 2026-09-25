"""CPU-only checkpoint checks; excludes IRQ, ULA, disk and full playback."""
import unittest

import compiled_masks_z80 as compiled
from frame_metadata_z80 import FLAGS, MASKS, expected_tstates as old_tstates
from probe_motion_metadata import transform
from validate_fast_sparse import CPU

INPUT, STACK, STOP = 0xa6a0, 0x9df0, 0x9df0


class GuardedCPU(CPU):
    allowed_writes = None

    def write8(self, address, value):
        if self.allowed_writes is not None:
            if not any(start <= address < end for start, end in self.allowed_writes):
                raise AssertionError(f'unexpected write: {address:04x}')
        super().write8(address, value)


class CompiledMaskTests(unittest.TestCase):
    def setUp(self):
        regions, self.labels, rows, self.expected = compiled.build()
        self.cpu = GuardedCPU(b'', b'')
        self.cpu.port_7ffd = 0x17
        self.rows = {row['address']: row for row in rows}
        for address, data in regions:
            self.install(address, data)

    def install(self, address, data):
        self.cpu.allowed_writes = None
        for offset, value in enumerate(data):
            self.cpu.write8(address + offset, value)

    def read(self, address, length):
        return bytes(self.cpu.read8(address + i) for i in range(length))

    def run_code(self, entry, outputs):
        cpu = self.cpu
        cpu.allowed_writes = outputs + [(STACK - 32, STACK)]
        cpu.pc, cpu.sp = entry, STACK
        cpu.push(STOP)
        before = cpu.tstates
        for _ in range(100000):
            if cpu.pc == STOP:
                self.assertEqual(cpu.sp, STACK)
                self.assertEqual(cpu.port_7ffd, 0x17)
                return cpu.tstates - before
            row, previous = self.rows[cpu.pc], cpu.tstates
            cpu.step()
            self.assertEqual(cpu.tstates - previous, row['tstates'], row)
        self.fail('Z80 routine did not return')

    def initialize(self):
        return self.run_code(self.labels['initialize'], [(compiled.TABLE, compiled.END)])

    def test_generated_tables_and_initialization_cycles(self):
        # Setup 27 T, 256 patterns: 740 + 10*popcount + 14*(last bit zero), RET 10.
        self.assertEqual(self.initialize(), 201509)
        for address, expected in self.expected:
            self.assertEqual(self.read(address, len(expected)), expected)

    def test_all_presence_patterns_and_decoder_cycles(self):
        self.initialize()
        for mask in range(256):
            with self.subTest(mask=mask):
                source = bytes((i % 255 + 1) if mask & (128 >> (i % 8)) else 0
                               for i in range(480))
                encoded = transform(source, 480, 4)
                self.install(INPUT, encoded)
                self.cpu.set_hl(INPUT)
                ticks = self.run_code(self.labels['decode'], [(MASKS, MASKS + 480),
                                                              (FLAGS, FLAGS + 64)])
                self.assertEqual(self.read(MASKS, 480), source)
                self.assertEqual(self.read(FLAGS + 60, 4), bytes(4))
                self.assertEqual(self.read(INPUT, len(encoded)), encoded)
                self.assertEqual(self.cpu.hl(), INPUT + len(encoded))
                self.assertEqual(ticks, compiled.expected_tstates(encoded))
                self.assertLessEqual(ticks, old_tstates(encoded))


if __name__ == '__main__':
    unittest.main()
