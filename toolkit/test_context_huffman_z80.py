import json
from pathlib import Path
import unittest
from unittest.mock import patch

import ay_interrupt
from build_zxv_trd import MiniAssembler
import playback_schedule
from benchmark_context_huffman import Harness, INPUT, STOP, word
from probe_context_values import pack
from probe_motion_entropy import codes_for
from validate_fast_sparse import CPU
from summarize_context_cpu import queue_bound, minimum_capacity


class ContextHuffmanZ80Tests(unittest.TestCase):
    def test_idealized_queue_hand_cases(self):
        self.assertEqual(queue_bound([1, 11, 1], 1, 10),
                         dict(prefilled_frames=1, max_lateness_tstates=1, first_late_frame=1))
        self.assertEqual(queue_bound([1, 11, 1], 2, 10)['max_lateness_tstates'], 0)
        self.assertEqual(queue_bound([0]*5, 1, 10)['max_lateness_tstates'], 0)
        # Unused early CPU time cannot be saved once the output queue is full.
        self.assertEqual(queue_bound([0, 0, 0, 11], 1, 10)['first_late_frame'], 3)
        self.assertEqual(minimum_capacity([1, 11, 1], 10), 2)
        self.assertEqual(minimum_capacity([0, 0, 0, 11], 10), 2)

    def drive(self, tables, mapping, pairs, values, variant):
        h = Harness(tables, mapping, variant)
        contexts = [len(tables)-1 if attribute else mapping[prediction] for attribute, prediction in pairs]
        bits, encoded = pack(values, contexts, [codes_for(255, t) for t in tables])
        h.begin(encoded)
        measured = 0
        for i in range(0, len(values), 32):
            result = h.run(pairs[i:i+32], values[i:i+32])
            measured += result['bits']
        self.assertEqual(measured, bits)
        self.assertEqual(word(h.cpu, h.labels['source']), INPUT+len(encoded))
        before = word(h.cpu, h.labels['source']), h.cpu.read8(h.labels['reservoir'])
        self.assertEqual(h.run([], b'')['total_tstates'], 27)
        self.assertEqual(before, (word(h.cpu, h.labels['source']), h.cpu.read8(h.labels['reservoir'])))
        return h

    def test_short_codes_context_changes_empty_call_and_saved_registers(self):
        tables = [bytes([0, 1, 2, 2]+[0]*252), bytes([0, 2, 1, 2]+[0]*252)]
        mapping = bytes(256)
        pairs = [(i % 2, i % 256) for i in range(293)]
        values = bytes(1+i % 3 for i in range(len(pairs)))
        for variant in ('compact', 'direct', 'unrolled'):
            with self.subTest(variant=variant):
                self.drive(tables, mapping, pairs, values, variant)

    def test_all_movie_codes_and_predictor_map_entries(self):
        profile = json.loads((Path(__file__).parent/'prediction_context_profile.json').read_text())
        candidate = next(row for row in profile['rows'] if row['name'] == 'exact_predicted_byte')['clustered_huffman'][0]
        self.assertEqual(candidate['bitmap_contexts'], 64)
        tables, mapping = [bytes(t) for t in candidate['tables']], bytes(candidate['context_map'])
        pairs, values = [], bytearray()
        for context, table in enumerate(tables):
            pair = (1, 0) if context == len(tables)-1 else (0, mapping.index(context))
            for value, size in enumerate(table):
                if size:
                    pairs.append(pair); values.append(value)
        for predicted in range(256):
            pairs.append((0, predicted))
            values.append(next(v for v, n in enumerate(tables[mapping[predicted]]) if n))
        for variant in ('compact', 'direct', 'unrolled'):
            for offset in range(0, len(values), 512):
                with self.subTest(variant=variant, offset=offset):
                    self.drive(tables, mapping, pairs[offset:offset+512], bytes(values[offset:offset+512]), variant)

    def test_reject_incomplete_tree_and_truncated_input(self):
        with self.assertRaises(ValueError):
            Harness([bytes([0, 2]+[0]*254)]*2, bytes(256), 'unrolled')
        tables = [bytes([0, 1, 2, 2]+[0]*252)]*2
        h = Harness(tables, bytes(256), 'unrolled')
        h.begin(b'')
        with self.assertRaises(RuntimeError):
            h.run([(0, 0)], b'\x01')

    def test_sla_every_register_value_and_carry(self):
        cpu = CPU(b'', b'')
        for register in range(8):
            cpu.write8(0x8000, 0xcb); cpu.write8(0x8001, 0x20+register)
            for value in range(256):
                for old_carry in (False, True):
                    cpu.set_hl(0xa400)
                    cpu.put(register, value)
                    cpu.pc, cpu.z, cpu.carry = 0x8000, False, old_carry
                    before = cpu.tstates
                    cpu.step()
                    self.assertEqual((cpu.reg(register), cpu.z, cpu.carry, cpu.tstates-before),
                                     ((value*2) & 255, not (value & 127), bool(value & 128), 15 if register == 6 else 8))

    def test_existing_ay_irq_after_every_decoder_instruction(self):
        profile = json.loads((Path(__file__).parent/'prediction_context_profile.json').read_text())
        candidate = next(row for row in profile['rows'] if row['name'] == 'exact_predicted_byte')['clustered_huffman'][0]
        tables, mapping = [bytes(t) for t in candidate['tables']], bytes(candidate['context_map'])
        self.exercise_ay_irq(tables, mapping, lambda: Harness(tables, mapping, 'unrolled'),
                             'benchmark_context_huffman.PAIRS')

    def exercise_ay_irq(self, tables, mapping, harness_factory, pairs_variable):
        pairs, values, contexts = [], bytearray(), []
        # Exercise maximum-depth codes, both entries and unaligned refills.
        attribute_context = len(tables)-1
        for context in list(range(min(15, attribute_context)))+[attribute_context]:
            pairs.append((1, 0) if context == attribute_context else (0, mapping.index(context)))
            values.append(max(range(256), key=lambda v: tables[context][v]))
            contexts.append(context)
        _, encoded = pack(values, contexts, [codes_for(255, t) for t in tables])
        h = harness_factory()
        h.begin(encoded)
        a = MiniAssembler(0xa500)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True,
                                     memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0xb900)  # Leave the new fixed root lookup intact.
        cpu = h.cpu
        for i, b in enumerate(a.resolve()):
            cpu.write8(0xa500+i, b)
        cpu.pc = a.labels['setup_clock']; cpu.push(STOP)
        while cpu.pc != STOP:
            cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        word(cpu, a.labels['audio_remaining'], 65535)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry',
                 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l',
                 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls = 0

        def interrupt(cpu):
            nonlocal calls
            cpu.guarding = False
            count = calls % 12
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot, count)
            expected = list(cpu.ay)
            for register in range(count):
                value = (calls+register) & 15
                cpu.write8(slot+1+register*2, register)
                cpu.write8(slot+2+register*2, value)
                expected[register] = value
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {name: getattr(cpu, name) for name in names}
            start, return_pc = cpu.tstates, cpu.pc
            cpu.push(return_pc); cpu.pc = 0xbdbd
            cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != return_pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal'])
                cpu.step()
            self.assertEqual({name: getattr(cpu, name) for name in names}, before)
            self.assertEqual(list(cpu.ay), expected)
            elapsed = cpu.tstates-start
            self.assertEqual(elapsed, 116+17+(367+83*count if count else 377))
            calls += 1
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            self.assertTrue(cpu.iff1)
            cpu.guarding = True
            return elapsed

        # The normal CPU fixture puts pairs at A000; relocate them for this
        # IRQ fixture because the real AY queue owns A000..A3FF.
        with patch(pairs_variable, 0x9400):
            h.run(pairs, bytes(values), interrupt)
        self.assertGreater(calls, 1000)


if __name__ == '__main__':
    unittest.main()
