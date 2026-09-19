import unittest

import numpy as np

from benchmark_cell_screen import Harness
from probe_cell_output_masks import masks
import ay_interrupt
import playback_schedule
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler


class CellScreenTests(unittest.TestCase):
    def test_dense_sparse_and_n_minus_two_clearing(self):
        rng = np.random.default_rng(4221)
        states = np.zeros((6, 3840), dtype=np.uint8)
        states[0:2, 256:2816] = rng.integers(0, 256, (2, 2560), dtype=np.uint8)
        states[2:4] = states[:2]
        for col in (0, 7, 8, 15, 16, 23, 24, 31):
            for row in (8, 11, 12, 15, 31, 32, 63, 64, 84, 87):
                states[2:4, row*32+col] ^= 255
        states[:, 3072:] = np.arange(768, dtype=np.uint16).astype(np.uint8)
        packed, _, _ = masks(states, 18)
        h = Harness()
        for index, state in enumerate(states):
            h.run(state.tobytes(), packed[index].tobytes(), index)
        # A missing dirty cell must be detected by actual native output.
        changed = states[-1].copy(); changed[8*32] = 255
        with self.assertRaisesRegex(AssertionError, 'native screen differs'):
            h.run(changed.tobytes(), bytes(80), 6)

    def test_empty_masks_and_invalid_crop(self):
        h = Harness()
        self.assertEqual(h.run(bytes(3840), bytes(80), 0)['tstates'], 58784)
        state = bytearray(3840); state[255] = 1
        with self.assertRaises(ValueError):
            h.run(state, bytes(80), 1)
        with self.assertRaises(ValueError):
            masks(np.array([list(state)], dtype=np.uint8))

    def test_ay_irq_at_every_instruction_preserves_exx_and_map_copy(self):
        h = Harness()
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
        for row in range(8, 12):
            state[row*32] = row
        state[12*32:16*32] = bytes(range(128))
        state[3072:] = bytes(range(256))*3
        mask = bytes([128, 0, 0, 0])+b'\xff'*4+bytes(72)
        for index in range(2):
            h.run(state, mask, index, interrupt)
        self.assertGreater(calls, 5000)


if __name__ == '__main__':
    unittest.main()
