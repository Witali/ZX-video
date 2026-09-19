import unittest

import numpy as np

from benchmark_cell_screen import Harness
from probe_cell_output_masks import masks
import ay_interrupt
import playback_schedule
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
import cell_screen_z80 as machine


class CellScreenTests(unittest.TestCase):
    def test_unrolled_dispatch_every_mask_and_old_code(self):
        # This hash is of the unchanged generator's code in cell_output_cpu.json.
        import json
        from pathlib import Path
        baseline = json.loads(Path(__file__).with_name('cell_output_cpu.json').read_text(encoding='utf-8'))
        self.assertEqual(machine.build()[0], bytes.fromhex(baseline['code_hex']))
        h = Harness(fast_mask_dispatch=True)
        states = [bytearray(3840), bytearray(3840)]
        seen = set()
        for index in range(4):
            state = states[index % 2]
            mask = bytes((index*80+i) % 256 for i in range(80))
            seen.update(mask)
            for pos, flags in enumerate(mask):
                band, octet = divmod(pos, 4)
                for bit in range(8):
                    if flags & (128 >> bit):
                        for row in range(8+band*4, 12+band*4):
                            state[row*32+octet*8+bit] ^= (17+row+index) & 255
            state[3072:] = bytes([index+1])*768
            result = h.run(state, mask, index)
            self.assertLessEqual(result['tstates'], machine.expected_tstates(mask))
        self.assertEqual(seen, set(range(256)))

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
        fast = Harness(fast_mask_dispatch=True)
        self.assertEqual(fast.run(bytes(3840), bytes(80), 0)['tstates'], 26704)
        state = bytearray(3840); state[255] = 1
        with self.assertRaises(ValueError):
            h.run(state, bytes(80), 1)
        with self.assertRaises(ValueError):
            masks(np.array([list(state)], dtype=np.uint8))

    def test_ay_irq_at_every_instruction_preserves_exx_and_map_copy(self):
        self.exercise_irq()

    def test_ay_irq_preserves_unrolled_flags_in_alternate_af(self):
        self.exercise_irq(fast=True)

    def exercise_irq(self, fast=False):
        h = Harness(fast_mask_dispatch=fast)
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
