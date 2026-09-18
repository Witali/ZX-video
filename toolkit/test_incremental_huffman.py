"""Resume a bounded Huffman producer with clobbered registers and split input."""
import json
from pathlib import Path
import unittest

import ay_interrupt
from build_zxv_trd import MiniAssembler
import playback_schedule
from benchmark_incremental_huffman import Harness, Provider, INPUT, STOP, word
from probe_motion_entropy import codes_for, pack
from validate_fast_sparse import CPU


class IncrementalHuffmanTests(unittest.TestCase):
    def lengths(self):
        report = json.loads((Path(__file__).parent/'motion_entropy_measurements.json').read_text())
        return bytes(next(row for row in report['rows'] if row['name'] == 'huffman')['table'])

    def drive(self, values, sizes, quota, lengths=None, irq=False):
        lengths = lengths or self.lengths()
        bits, data = pack(values, codes_for(255, lengths))
        h = Harness(lengths, quota)
        interrupt = self.install_irq(h) if irq else None
        h.begin(len(values))
        cursor, received, calls = 0, bytearray(), []
        while True:
            if not h.get('input_left') and cursor < len(data):
                size = min(sizes[len(calls) % len(sizes)], len(data)-cursor)
                for i, b in enumerate(data[cursor:cursor+size]):
                    h.cpu.write8(INPUT+i, b)
                h.window(INPUT, size)
            chunk, result = h.run(interrupt)
            received += chunk
            cursor += result['input_bytes']
            calls.append(result)
            if result['status'] == 2:
                break
            self.assertLess(len(calls), len(data)*4+10)
        self.assertEqual(received, values)
        self.assertEqual(cursor, len(data))
        self.assertEqual(h.get('input_left'), 0)
        return h, calls

    def install_irq(self, h):
        # The existing memory-clock and AY handlers, relocated into unused
        # fixture space. Host publishes one record per injected interrupt;
        # this tests register/queue safety, not a real 50 Hz producer schedule.
        a = MiniAssembler(0xa500)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True,
                                     memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0xbd00)
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
            mode, cpu.mode = cpu.mode, None
            count = calls % 12
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE + index*ay_interrupt.SLOT_BYTES
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
            cpu.mode = mode
            return elapsed

        return interrupt

    def test_ay_irq_after_every_huffman_instruction(self):
        values = bytes(range(1, 256))
        _, control = self.drive(values, [1, 55, 128], 32)
        _, interrupted = self.drive(values, [1, 55, 128], 32, irq=True)
        self.assertEqual([row['tstates'] for row in interrupted],
                         [row['tstates'] for row in control])
        self.assertTrue(all(row['irq_tstates'] > 0 for row in interrupted))

    def test_quota_and_every_input_byte_boundary(self):
        values = bytes(range(1, 256))*2
        for quota in (1, 7, 32, 64):
            _, calls = self.drive(values, [1, 3, 19, 2, 128], quota)
            self.assertTrue(all(row['bytes'] <= quota for row in calls))
            self.assertTrue(any(row['status'] == 1 for row in calls))

    def test_fast_path_bound_with_longest_codes(self):
        lengths = self.lengths()
        symbols = bytes(i for i, n in enumerate(lengths) if n == max(lengths))
        values = (symbols*200)[:400]
        for quota in (1, 32, 64):
            _, calls = self.drive(values, [112, 56, 55, 1], quota, lengths)
            self.assertTrue(any(row['path'] == 'fast' for row in calls))

    def test_empty_and_low_nibble_resume(self):
        lengths = bytes([0]+[4]*16+[0]*239)
        h, calls = self.drive(b'', [1], 32, lengths)
        self.assertEqual(len(calls), 1)
        self.assertEqual(h.get('status'), 2)
        self.drive(bytes([1, 16, 2]), [1], 1, lengths)
        # Repeated request without input does not lose an unfinished code.
        h = Harness(self.lengths(), 32)
        h.begin(1)
        first, row = h.run()
        second, repeated = h.run()
        self.assertEqual((first, second, row['status'], repeated['status']), (b'', b'', 1, 1))

    def test_ix_absolute_load_store_flags_and_cycles(self):
        cpu = CPU(b'', b'')
        for instruction in (0x22, 0x2a):
            for value in (0, 1, 255, 256, 0x9fff, 0xffff):
                for z, carry in ((False, True), (True, False)):
                    for i, b in enumerate(bytes([0xdd, instruction, 0xff, 0xa4])):
                        cpu.write8(0x8000+i, b)
                    word(cpu, 0xa4ff, value)
                    cpu.ix = value if instruction == 0x22 else 0x1234
                    cpu.pc, cpu.z, cpu.carry = 0x8000, z, carry
                    before = cpu.tstates
                    cpu.step()
                    self.assertEqual(cpu.ix if instruction == 0x2a else word(cpu, 0xa4ff), value)
                    self.assertEqual((cpu.z, cpu.carry, cpu.tstates-before), (z, carry, 20))

    def test_interleaved_zx0_preserves_huffman_state(self):
        # Use a real saved optimal block from the checked-in storage report;
        # skip only when the developer has not reproduced the local cache.
        root = Path(__file__).parent.parent
        storage = json.loads((root/'toolkit/motion_entropy_huffman_zx0_measurements.json').read_text())
        first = storage['blocks'][0]
        cache = root/'.tmp/motion_entropy_zx0/optimal'
        if not (cache/(first['sha256']+'.zx0')).exists():
            self.skipTest('ZX0 experiment cache unavailable')
        raw = (root/'.tmp/motion_entropy/huffman.raw').read_bytes()[:8192]
        h = Harness(self.lengths(), 32)
        h.begin(17)
        h.set('phase', 1); h.set('byte', 0xa5)
        expected = bytes(h.cpu.read8(i) for i in range(*h.cpu.huffman_state))
        provider = Provider(h, raw, {'blocks': [first]}, cache)
        for end in (1, 127, 128, 129, 1024, 8192):
            provider.through(end)
            self.assertEqual(expected, bytes(h.cpu.read8(i) for i in range(*h.cpu.huffman_state)))
        self.assertEqual(bytes(h.cpu.read8(INPUT+i) for i in range(8192)), raw)
        self.assertEqual(len(provider.calls), 64)


if __name__ == '__main__':
    unittest.main()
