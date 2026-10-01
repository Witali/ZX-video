"""Independent native execution of bank boundaries, EOF and the IRQ contract."""
import unittest

from player import BANKS, TICKS_PER_BANK, build_disk
from verify_preview import extract_player, native_check


def fixture(ticks):
    return b''.join(bytes((i & 255, (i >> 8) & 15, 40, 2, 130, 0,
                          i % 32, 0x2a if i % 32 else 0x38,
                          i % 16, (i // 3) % 16, (i // 7) % 16)) for i in range(ticks))


class PlayerTests(unittest.TestCase):
    def test_every_bank_boundary_and_eof(self):
        for ticks in (1, TICKS_PER_BANK-1, TICKS_PER_BANK, TICKS_PER_BANK+1,
                      2*TICKS_PER_BANK, 5*TICKS_PER_BANK):
            with self.subTest(ticks=ticks):
                raw = fixture(ticks)
                disk, meta = build_disk(raw)
                result = native_check(extract_player(disk), meta, raw)
                self.assertTrue(result['eof_mutes'])
                self.assertEqual(result['bank_sequence'], list(BANKS[:(ticks+TICKS_PER_BANK-1)//TICKS_PER_BANK]))
                self.assertTrue(set(result['deterministic_field_work_tstates']) <= {974, 992, 1007, 1091})
                if ticks % TICKS_PER_BANK == 0:
                    self.assertEqual(result['deterministic_field_work_tstates'][1007], 1)

    def test_reject_invalid_data(self):
        for raw in (b'', b'\0', bytes(11*(5*TICKS_PER_BANK+1)), b'\0\xff'+bytes(9)):
            with self.subTest(length=len(raw)):
                with self.assertRaises(ValueError):
                    build_disk(raw)

    def test_irq_preserves_registers_and_costs_18_tstates(self):
        from z80 import Z80Machine
        disk, meta = build_disk(fixture(1))
        m = Z80Machine()
        m.set_memory_block(0x8000, extract_player(disk))
        saved = dict(af=0x7139, bc=0x1234, de=0x2345, hl=0x3456,
                     alt_af=0x9173, alt_bc=0x4567, alt_de=0x5678, alt_hl=0x6789, ix=0x789a, iy=0x89ab)
        for name, value in saved.items():
            setattr(m, name, value)
        m.sp = 0xb7fe
        m.memory[0xb7fe:0xb800] = b'\x00\x5f'
        m.pc = meta['player_labels']['irq']; m.set_breakpoint(0x5f00); m.ticks_to_stop = 1000
        while m.pc != 0x5f00:
            self.assertFalse(m.run() & m._TICKS_LIMIT_HIT)
        self.assertEqual(1000-m.ticks_to_stop, 18)
        self.assertEqual(m.sp, 0xb800)
        self.assertEqual({name:getattr(m, name) for name in saved}, saved)


if __name__ == '__main__':
    unittest.main()
