"""Known nibble streams, movie code lengths, memory bounds and opcode timing."""
import json
from pathlib import Path
import unittest

import numpy as np

from benchmark_huffman_z80 import (CheckedCPU, TABLE, build_decoder, run_group,
                                  transition_tables)
from probe_motion_entropy import codes_for, pack


class HuffmanZ80Tests(unittest.TestCase):
    def run_values(self, lengths, values, counts, known=None):
        tables, _ = transition_tables(lengths)
        code, _, checks = build_decoder()
        bits, encoded = pack(values, codes_for(255, lengths))
        if known is not None:
            self.assertEqual((bits, encoded), known)
        cpu = CheckedCPU(b'', b'')
        cpu.port_7ffd = 0x16
        for i, b in enumerate(tables):
            cpu.write8(TABLE+i, b)
        return run_group(cpu, encoded, bits, values, counts, code, checks)

    def test_handwritten_nibbles_and_empty_frames(self):
        lengths = bytes([0] + [4]*16 + [0]*239)
        self.run_values(lengths, bytes([1, 16, 2]), [1, 0, 2], (12, bytes([0x0f, 0x10])))
        self.run_values(lengths, bytes([16, 1]), [0, 2, 0], (8, b'\xf0'))
        elapsed, frames = self.run_values(lengths, b'', [0, 0], (0, b''))
        self.assertEqual((elapsed, frames), (27, [27, 0]))

    def test_movie_alphabet_every_symbol_and_unaligned_end(self):
        saved = json.loads((Path(__file__).parent / 'motion_entropy_measurements.json').read_text())
        lengths = bytes(next(row for row in saved['rows'] if row['name'] == 'huffman')['table'])
        symbols = bytes(i for i, n in enumerate(lengths) if n)
        self.run_values(lengths, symbols, [len(symbols)])
        rng = np.random.default_rng(195)
        values = rng.choice(np.frombuffer(symbols, dtype=np.uint8), size=1000).tobytes()
        self.run_values(lengths, values, [17, 500, 0, 483])
        # Every end alignment that actually occurs while cycling all symbols.
        for end in range(1, 17):
            self.run_values(lengths, symbols[:end], [end])

    def test_invalid_minimum_or_incomplete_tree(self):
        for lengths in (bytes([0, 1] + [0]*254), bytes([0, 4] + [0]*254)):
            with self.assertRaises(ValueError):
                transition_tables(lengths)

    def test_set_register_memory_flags_and_cycles(self):
        cpu = CheckedCPU(b'', b'')
        for bit in range(8):
            for register in range(8):
                cpu.write8(0x8000, 0xcb)
                cpu.write8(0x8001, 0xc0 + bit*8 + register)
                for value in range(256):
                    for flags in ((False, True), (True, False)):
                        cpu.set_hl(0xa400)
                        cpu.put(register, value)
                        cpu.pc, cpu.z, cpu.carry = 0x8000, *flags
                        before = cpu.tstates
                        cpu.step()
                        self.assertEqual((cpu.reg(register), cpu.z, cpu.carry, cpu.tstates-before),
                            (value | (1 << bit), *flags, 15 if register == 6 else 8))


if __name__ == '__main__':
    unittest.main()
