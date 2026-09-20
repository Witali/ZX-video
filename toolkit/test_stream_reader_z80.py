import struct
import unittest

from benchmark_context_huffman import word
from stream_reader_harness import Harness
from zx0_speed import Token, encode
from validate_fast_sparse import CPU
from build_zxv_trd import MiniAssembler
import ay_interrupt
import playback_schedule
from stream_reader_harness import STACK, STOP


def blocks(items):
    out, raw = bytearray(), bytearray()
    for data, compressed in items:
        payload = data if compressed is None else compressed
        out += struct.pack('<HH', len(data), len(payload) | (0x8000 if compressed is None else 0))+payload
        raw += data
    return bytes(out), bytes(raw)


class StreamReaderTests(unittest.TestCase):
    def test_res_instruction_preserves_flags_and_exact_timing(self):
        for bit in range(8):
            for register in range(8):
                cpu = CPU(b'', b''); cpu.pc = 0x8000; cpu.set_hl(0x9100)
                cpu.write8(0x8000, 0xcb); cpu.write8(0x8001, 0x80+bit*8+register)
                cpu.put(register, 255); cpu.z, cpu.carry = True, True
                cpu.step()
                self.assertEqual(cpu.reg(register), 255 ^ (1 << bit))
                self.assertEqual((cpu.z, cpu.carry), (True, True))
                self.assertEqual(cpu.tstates, 15 if register == 6 else 8)

    def test_headers_stored_payload_and_ring_wraps(self):
        items = [(bytes((j*19+i) & 255 for j in range(n)), None)
                 for i, n in enumerate([1, 255, 256, 257]+[8192]*10+[17])]
        stream, expected = blocks(items)
        for start in (0x3fff, 0xfff0):
            h, position = Harness(stream, ring_start=start), 0
            self.assertEqual(h.take(0), b'')
            for count in (1, 3, 257, 4096, 7):
                self.assertEqual(h.take(count), expected[position:position+count]); position += count
            while position < len(expected):
                count = min(1023, len(expected)-position)
                self.assertEqual(h.take(count), expected[position:position+count]); position += count
            self.assertEqual(h.cpu.consumed, len(stream))
            self.assertEqual(h.blocks, len(items))
            self.assertEqual(word(h.cpu, h.r['block_left']), 0)

    def test_compressed_match_boundaries_and_lookahead(self):
        first, second = b'z'*8192, bytes(range(256))*32
        stream, expected = blocks([(first, encode(first, [Token(0, 1), Token(1, 8191, 1)])),
            (second, encode(second, [Token(0, 256), Token(256, 7936, 256)]))])
        h = Harness(stream)
        self.assertEqual(h.take(1), expected[:1])
        # Produce the complete first block before the consumer asks for it.
        word(h.cpu, h.z['slice_target'], 0)
        h.execute(h.z['slice_until'])
        position = 1
        for count in (1, 255, 256, 4096, 4096, 4096, 1024, 4096):
            if position == len(expected): break
            count = min(count, len(expected)-position)
            self.assertEqual(h.take(count), expected[position:position+count]); position += count
        self.assertEqual(position, len(expected))
        self.assertEqual(h.cpu.consumed, len(stream))

    def test_malformed_headers_and_truncated_ring(self):
        for raw_size, packed_size in ((0, 1), (8193, 1), (1, 0), (1, 16385), (1, 0x8002)):
            with self.assertRaises((AssertionError, RuntimeError)):
                Harness(struct.pack('<HH', raw_size, packed_size)+b'!').take(1)
        stream, _ = blocks([(b'abcdef', None)])
        with self.assertRaises((AssertionError, RuntimeError)):
            Harness(stream[:-1]).take(6)

    def test_ay_irq_after_every_instruction(self):
        self.check_ay_irq_after_every_instruction(False)

    def test_unrolled_ay_irq_after_every_instruction(self):
        self.check_ay_irq_after_every_instruction(True)

    def check_ay_irq_after_every_instruction(self,unrolled_copy):
        data = bytes(range(256))*2
        stream, expected = blocks([(data[:256], None),
            (data, encode(data, [Token(0, 256), Token(256, 256, 256)]))])
        h = Harness(stream, ring_start=0xffff,unrolled_copy=unrolled_copy)
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0x9800)
        cpu = h.cpu
        for i, value in enumerate(a.resolve()): cpu.write8(0x9400+i, value)
        cpu.pc, cpu.sp = a.labels['setup_clock'], STACK; cpu.push(STOP)
        while cpu.pc != STOP: cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        names = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b',
                 'alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls = 0

        def irq(cpu):
            nonlocal calls
            cpu.guarding = False
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*32
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {n:getattr(cpu,n) for n in names}
            start, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal']); cpu.step()
            self.assertEqual(before, {n:getattr(cpu,n) for n in names})
            self.assertEqual(cpu.tstates-start, 583)
            self.assertEqual(cpu.ay[8], calls & 15)
            calls += 1
            self.assertEqual(word(cpu,a.labels['audio_underruns']), 0)
            cpu.guarding = True
            return cpu.tstates-start

        self.assertEqual(h.take(len(expected), interrupt=irq), expected)
        self.assertGreater(calls, 1500)


if __name__ == '__main__':
    unittest.main()
