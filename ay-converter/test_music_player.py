"""Exercise real Z80 loop/bank/EOF paths, including six full data banks."""
import unittest

from music_player import BANKS, MAX_TICKS, TICKS_PER_BANK, build_disk
from verify_preview import extract_player, native_check


def fixture(ticks):
    return b''.join(bytes((i & 255, (i >> 8) & 15, 40, 2, 130, 0,
                          i % 32, 0x2a if i % 32 else 0x38,
                          i % 16, (i // 3) % 16, (i // 7) % 16)) for i in range(ticks))


class MusicPlayerTests(unittest.TestCase):
    def test_two_complete_loops_and_instruction_costs(self):
        for ticks in (1, TICKS_PER_BANK-1, TICKS_PER_BANK, TICKS_PER_BANK+1, MAX_TICKS):
            with self.subTest(ticks=ticks):
                raw = fixture(ticks)
                disk, meta = build_disk(raw)
                result = native_check(extract_player(disk), meta, raw)
                self.assertEqual(result['cycles_verified'], 2)
                self.assertEqual(result['register_writes'], ticks*22)
                active = list(BANKS[:(ticks+TICKS_PER_BANK-1)//TICKS_PER_BANK])
                self.assertEqual(result['bank_sequence'], active*2)
                histogram = result['deterministic_field_work_tstates']
                self.assertTrue(set(histogram) <= {974, 992, 1007, 1091, 1079})
                self.assertEqual(histogram[1079], 1)

    def test_once_mutes_and_full_capacity_guard(self):
        raw = fixture(TICKS_PER_BANK)
        disk, meta = build_disk(raw, loop=False)
        result = native_check(extract_player(disk), meta, raw)
        self.assertTrue(result['eof_mutes'])
        self.assertEqual(result['deterministic_field_work_tstates'][1007], 1)
        for bad in (b'', bytes(10), bytes((MAX_TICKS+1)*11), b'\0\xff'+bytes(9)):
            with self.assertRaises(ValueError):
                build_disk(bad)


if __name__ == '__main__':
    unittest.main()
