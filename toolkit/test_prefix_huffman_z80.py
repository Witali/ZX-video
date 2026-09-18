import json
from pathlib import Path
import unittest

from benchmark_prefix_huffman import Harness, INPUT, word
from probe_context_values import pack
from probe_motion_entropy import codes_for
import test_context_huffman_z80 as existing
from validate_fast_sparse import CPU


def candidate():
    profile = json.loads((Path(__file__).parent/'direct_values_profile.json').read_text())
    model = next(row for row in profile['rows'] if row['name'] == 'direct')
    row = next(row for row in model['groups'] if row['bitmap_contexts'] == 16)
    return [bytes(t) for t in row['tables']], bytes(row['context_map'])


class PrefixHuffmanZ80Tests(unittest.TestCase):
    def drive(self, tables, mapping, pairs, values):
        contexts = [len(tables)-1 if attr else mapping[pred] for attr, pred in pairs]
        bits, encoded = pack(values, contexts, [codes_for(255, t) for t in tables])
        h = Harness(tables, mapping); h.begin(encoded)
        for offset in range(0, len(values), 32):
            h.run(pairs[offset:offset+32], values[offset:offset+32])
        self.assertEqual(h.position(), bits)
        self.assertEqual(word(h.cpu, h.labels['source']), INPUT+bits//8)
        self.assertEqual(h.run([], b'')['total_tstates'], 27)
        self.assertEqual(h.position(), bits)
        return h

    def test_zero_short_codes_all_bit_positions_and_boundary(self):
        tables = [bytes([1, 2, 2]+[0]*253), bytes([2, 1, 2]+[0]*253)]
        for padding in range(8):
            values = bytes([0]*padding+[0, 1, 2]*40)
            pairs = [(0, 0)]*padding+[(i % 2, i % 256) for i in range(120)]
            self.drive(tables, bytes(256), pairs, values)
        self.drive([bytes([8]*256)]*2, bytes(256), [(i % 2, i) for i in range(256)], bytes(range(256)))

    def test_all_movie_codes_at_all_bit_offsets_and_all_predictors(self):
        tables, mapping = candidate()
        pairs, values = [], bytearray()
        h = Harness(tables, mapping)
        for context, table in enumerate(tables):
            pair = (1, 0) if context == len(tables)-1 else (0, mapping.index(context))
            for value, size in enumerate(table):
                if size:
                    # Explicit offset fixture avoids relying on accidental bit alignment.
                    code = codes_for(255, table)[value][0]
                    for offset in range(8):
                        encoded = (code << ((-offset-size) % 8)).to_bytes((offset+size+7)//8, 'big')
                        h.begin(encoded)
                        h.cpu.write8(h.labels['bit_page'], 0xf0+offset)
                        h.run([pair], bytes([value]))
                    pairs.append(pair); values.append(value)
        for prediction in range(256):
            pairs.append((0, prediction))
            values.append(next(v for v, n in enumerate(tables[mapping[prediction]]) if n))
        self.drive(tables, mapping, pairs, bytes(values))

    def test_invalid_layout_and_missing_lookahead(self):
        with self.assertRaises(ValueError):
            Harness([bytes([2]+[0]*255)]*2, bytes(256))
        tables = [bytes([8]*256)]*2
        h = Harness(tables, bytes(256)); h.begin(b'\0')
        h.cpu.input_end -= 1
        with self.assertRaisesRegex(RuntimeError, 'read past coded input'):
            h.run([(0, 0)], b'\0')
        full, _ = candidate()
        with self.assertRaises(ValueError):
            Harness(full+[full[0]]*7, bytes(256))
        with self.assertRaises(ValueError):
            h.begin(bytes(16384))

    def test_dec_ix_flags_and_wrap(self):
        cpu = CPU(b'', b'')
        cpu.write8(0x8000, 0xdd); cpu.write8(0x8001, 0x2b)
        for value in (0, 1, 127, 128, 255, 256, 32767, 32768, 65535):
            for z in (False, True):
                for carry in (False, True):
                    cpu.ix, cpu.pc, cpu.z, cpu.carry = value, 0x8000, z, carry
                    before = cpu.tstates
                    cpu.step()
                    self.assertEqual((cpu.ix, cpu.z, cpu.carry, cpu.tstates-before), ((value-1) & 65535, z, carry, 10))

    def test_existing_ay_irq_after_every_instruction(self):
        # Reuse the existing independent IRQ fixture with this decoder and
        # its actual 16-context tables and separate fixed lookup pages.
        tables, mapping = candidate()
        fixture = existing.ContextHuffmanZ80Tests()
        fixture.exercise_ay_irq(tables, mapping, lambda: Harness(tables, mapping),
                               'benchmark_prefix_huffman.PAIRS')


if __name__ == '__main__':
    unittest.main()
