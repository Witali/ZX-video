"""Native phase selection, n-2 dirty maps, guarded writes and IRQ boundaries."""
import unittest

import numpy as np

from benchmark_cell_screen import Harness
import cell_screen_z80 as machine
from dither_phase import dirty_maps
import test_cell_screen


class PhaseRendererTests(unittest.TestCase):
    def test_all_non_flash_attributes_and_packed_values(self):
        h = Harness(fast_mask_dispatch=True, gray_cells=True, phase_aligned=True)
        seen = set()
        for frame in range(13):
            state = np.zeros(3840, dtype=np.uint8)
            bitmap = state[:3072].reshape(24, 4, 32)
            attrs = state[3072:].reshape(24, 32)
            for cell in range(640):
                band, col = divmod(cell, 32)
                attr = cell % 128
                attrs[band+2, col] = attr
                for row in range(4):
                    value = (cell//128*4+row+frame*20) % 256
                    bitmap[band+2, row, col] = value
                    seen.add((attr, value))
            h.run(state.tobytes(), b'\xff'*80, frame)
        self.assertEqual(len(seen), 128*256)

    def test_sparse_masks_and_attribute_only_redraws(self):
        rng = np.random.default_rng(528)
        states = np.zeros((6, 3840), dtype=np.uint8)
        states[:2, 256:2816] = rng.integers(0, 256, (2, 2560), dtype=np.uint8)
        states[:2, 3072:] = 7
        states[2:4] = states[:2]
        # No compact pixel changes. Flip orientation in sparse cells in all
        # thirds and octets, requiring redraw against the same back screen.
        for cell in range(64, 704, 9):
            states[2:4, 3072+cell] = 56
        maps, _ = dirty_maps(states, aligned=True)
        h = Harness(fast_mask_dispatch=True, gray_cells=True, phase_aligned=True)
        for index, state in enumerate(states):
            h.run(state.tobytes(), maps[index].tobytes(), index)
        h = Harness(fast_mask_dispatch=True, gray_cells=True, phase_aligned=True)
        for index in range(2): h.run(states[index].tobytes(), maps[index].tobytes(), index)
        with self.assertRaisesRegex(AssertionError, 'native screen differs'):
            h.run(states[2].tobytes(), bytes(80), 2)

    def test_guards_and_integrated_code_budget(self):
        with self.assertRaises(ValueError): machine.build(phase_aligned=True)
        h = Harness(fast_mask_dispatch=True, gray_cells=True, phase_aligned=True)
        state = bytearray(3840); state[3072] = 128
        with self.assertRaisesRegex(ValueError, 'FLASH'): h.run(state, bytes(80), 0)
        self.assertEqual(len(h.cpu.phase_patches), 65)
        h.cpu.guarding = True
        h.cpu.target_bank = 7
        with self.assertRaisesRegex(AssertionError, 'outside back screen'):
            h.cpu.write8(h.labels['draw'], 0)
        _, labels, _, regions = machine.build(fast_mask_dispatch=True, gray_cells=True,
            phase_aligned=True, constant_attribute_borders=True, skip_black_borders=True,
            attribute_groups=True, preloaded_mask=True, page_entry=0x9780)
        self.assertLessEqual(labels['end'], 0x9360)
        self.assertEqual([(at, len(data)) for at, data in regions],
                         [(0x9e00, 512), (0xf900, 490), (0x9880, 128)])

    def test_ay_irq_at_every_instruction(self):
        # Reuse the independent full-register/alternate-register IRQ contract.
        test_cell_screen.CellScreenTests().exercise_irq(fast=True, gray_cells=True, phase_aligned=True)


if __name__ == '__main__':
    unittest.main()
