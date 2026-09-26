"""CPU and forced AY IRQ checks; excludes ULA, disk and full playback."""
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
    hl_flags=False

    def setUp(self):
        regions, self.labels, rows, self.expected = compiled.build(hl_flags=self.hl_flags)
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

    def run_code(self, entry, outputs, interrupt=None):
        cpu = self.cpu
        cpu.allowed_writes = outputs + [(STACK - 32, STACK)]
        cpu.pc, cpu.sp = entry, STACK
        cpu.push(STOP)
        before, irq_ticks = cpu.tstates, 0
        for _ in range(100000):
            if cpu.pc == STOP:
                self.assertEqual(cpu.sp, STACK)
                self.assertEqual(cpu.port_7ffd, 0x17)
                return cpu.tstates - before - irq_ticks
            row, previous = self.rows[cpu.pc], cpu.tstates
            cpu.step()
            expected = row['tstates']
            self.assertIn(cpu.tstates - previous, expected if isinstance(expected, list) else [expected], row)
            if interrupt and cpu.pc != STOP:
                irq_ticks += interrupt(cpu)
        self.fail('Z80 routine did not return')

    def initialize(self, interrupt=None):
        return self.run_code(self.labels['initialize'], [(compiled.TABLE, compiled.END)], interrupt)

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
                self.assertEqual(ticks, compiled.expected_tstates(encoded,hl_flags=self.hl_flags))
                self.assertLessEqual(ticks, old_tstates(encoded))

    def test_ay_irq_after_each_generator_and_decoder_instruction(self):
        import ay_interrupt
        import playback_schedule
        from build_zxv_trd import MiniAssembler
        from benchmark_context_huffman import word
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0x9800)
        self.install(0x9400, a.resolve())
        cpu = self.cpu
        cpu.pc, cpu.sp = a.labels['setup_clock'], STACK
        cpu.push(STOP)
        while cpu.pc != STOP:
            cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        names = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b',
                 'alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls = 0

        def interrupt(cpu):
            nonlocal calls
            allowed, cpu.allowed_writes = cpu.allowed_writes, None
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE + index * ay_interrupt.SLOT_BYTES
            for offset, value in enumerate((1, 8, calls & 15)):
                cpu.write8(slot + offset, value)
            cpu.write8(a.labels['audio_write_index'], (index + 1) & 31)
            saved = {name:getattr(cpu, name) for name in names}
            before, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal'])
                cpu.step()
            self.assertEqual(saved, {name:getattr(cpu, name) for name in names})
            self.assertEqual(cpu.ay[8], calls & 15)
            self.assertEqual(cpu.tstates - before, 583)
            calls += 1
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            cpu.allowed_writes = allowed
            return cpu.tstates - before

        self.assertEqual(self.initialize(interrupt), 201509)
        for address, expected in self.expected:
            self.assertEqual(self.read(address, len(expected)), expected)
        for mask in (0, 255, 85, 128, 1, 127):
            source = bytes((i % 255 + 1) if mask & (128 >> (i % 8)) else 0 for i in range(480))
            encoded = transform(source, 480, 4)
            self.install(INPUT, encoded); cpu.set_hl(INPUT)
            ticks = self.run_code(self.labels['decode'], [(MASKS, MASKS + 480), (FLAGS, FLAGS + 64)], interrupt)
            self.assertEqual(ticks, compiled.expected_tstates(encoded,hl_flags=self.hl_flags))
            self.assertEqual(self.read(MASKS, 480), source)
            self.assertEqual(cpu.hl(), INPUT + len(encoded))
        self.assertGreater(calls, 20000)


if __name__ == '__main__':
    unittest.main()
