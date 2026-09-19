import unittest

import numpy as np

import ay_interrupt
import playback_schedule
import compact_screen_z80 as machine
from benchmark_compact_screen import Harness, STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler


class CompactScreenTests(unittest.TestCase):
    def test_all_values_rows_banks_and_source_page_boundaries(self):
        rng = np.random.default_rng(256192)
        for first, rows in ((0, 96), (0, 1), (7, 2), (12, 72), (95, 1)):
            variants = [Harness(first=first, rows=rows, paired=p, unrolled_attrs=u)
                        for p, u in ((False, False), (False, True), (True, False), (True, True))]
            for index in range(3):
                state = np.zeros(3840, dtype=np.uint8)
                state[first*32:(first+rows)*32] = rng.integers(0, 256, rows*32, dtype=np.uint8)
                state[3072:] = np.arange(768, dtype=np.uint16).astype(np.uint8)
                outputs = [h.run(state.tobytes(), index) for h in variants]
                self.assertEqual(len({r['output_sha256'] for r in outputs}), 1)
                self.assertEqual(outputs[-1]['tstates']-outputs[0]['tstates'], -8*32*rows-3156)
                self.assertEqual(outputs[1]['tstates']-outputs[0]['tstates'], -3156)
                self.assertEqual(outputs[2]['tstates']-outputs[0]['tstates'], -8*32*rows)

    def test_crop_rejects_nonzero_omitted_rows_and_invalid_ranges(self):
        for first, rows in ((-1, 10), (0, 0), (95, 2)):
            with self.assertRaises(ValueError):
                Harness(first=first, rows=rows)
        h = Harness(first=12, rows=72)
        for offset in (0, 383, 2688, 3071):
            state = bytearray(3840); state[offset] = 1
            with self.assertRaises(ValueError):
                h.run(state, 0)

    def test_real_ay_irq_preserves_every_instruction_boundary(self):
        # Two rows cross a compact-source page and a native screen band.
        # Repeated LDIR is stepped one transfer at a time in this fixture.
        for paired, attrs in ((False, False), (True, True)):
            h = Harness(first=7, rows=2, paired=paired, unrolled_attrs=attrs)
            a = MiniAssembler(0x9400)
            ay_interrupt.emit(a)
            playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
            ay_interrupt.emit_variables(a)
            a.label('elapsed_fields'); a.word(0)
            a.label('fatal'); a.emit(0x76)
            self.assertLess(h.labels['end'], 0x9400)
            self.assertLess(a.pc, 0x9800)
            cpu = h.cpu
            for i, value in enumerate(a.resolve()):
                cpu.write8(0x9400+i, value)
            cpu.pc, cpu.sp = a.labels['setup_clock'], STACK
            cpu.push(STOP)
            while cpu.pc != STOP:
                cpu.step()
            cpu.write8(a.labels['audio_enabled'], 1)
            names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry', 'alt_a',
                     'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l', 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
            calls = 0

            def interrupt(cpu):
                nonlocal calls
                cpu.guarding = False
                word(cpu, a.labels['audio_remaining'], 65535)
                index = cpu.read8(a.labels['audio_read_index'])
                slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
                cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
                cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
                before = {name: getattr(cpu, name) for name in names}
                start, pc = cpu.tstates, cpu.pc
                cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
                while cpu.pc != pc:
                    self.assertNotEqual(cpu.pc, a.labels['fatal']); cpu.step()
                self.assertEqual(before, {name: getattr(cpu, name) for name in names})
                self.assertEqual(cpu.ay[8], calls & 15)
                self.assertEqual(cpu.tstates-start, 116+17+367+83)
                calls += 1
                self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
                self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
                cpu.guarding = True
                return cpu.tstates-start

            state = bytearray(3840)
            state[7*32:9*32] = bytes(range(64))
            state[3072:] = bytes(range(256))*3
            for frame in range(2):
                result = h.run(state, frame, interrupt)
                self.assertEqual(result['tstates'], machine.expected_tstates(7, 2, paired=paired, unrolled_attrs=attrs))
            self.assertGreater(calls, 2000)


if __name__ == '__main__':
    unittest.main()
