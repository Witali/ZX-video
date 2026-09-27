"""Resident AY machine code, bank limits, atomic publication and real IRQs."""
import random
import struct
import unittest

from ay_huffman_stream import encode
from benchmark_resident_audio_z80 import Harness, word
from benchmark_resident_audio_z80 import REGISTERS, STOP, STACK
import pipelined_frame_z80 as video
import resident_audio_z80 as resident


def record(mask, value):
    pairs = [(r, value(r)) for r in range(11) if mask & (1 << r)]
    return bytes([len(pairs)])+bytes(v for pair in pairs for v in pair)


def drain(h):
    while h.consumed < len(h.records):
        _, count = h.fill()
        if not count: raise AssertionError('no progress with empty queue')
        for _ in range(count): h.consume()
    h.finish()


class ResidentAudioZ80Tests(unittest.TestCase):
    def test_empty_constant_and_independent_initial_registers(self):
        for records in ([], [b'\0']*60, [record(2047, lambda r: 251-r)]*60):
            initial = bytes(range(101,112))
            h = Harness(encode(records, initial)[0])
            self.assertEqual(h.build['input_bits'], 0)
            drain(h)
            self.assertEqual(h.fill()[1], 0)
            h.finish()

    def test_every_mask_and_all_register_value_bytes(self):
        sequences = [
            [record(mask, lambda r: (r*19)&255) for mask in range(2048)],
            [record(2047, lambda r: (value+r*13)&255) for value in range(256)],
        ]
        for records in sequences:
            h = Harness(encode(records)[0])
            drain(h)
            self.assertEqual(h.cpu.published, len(records))

    def test_full_queue_returns_and_index_wraps_without_reading_more_input(self):
        rng = random.Random(481)
        records = [record(rng.randrange(2048), lambda r: rng.randrange(32)) for _ in range(120)]
        h = Harness(encode(records)[0])
        for _ in range(5): self.assertEqual(h.fill()[1], 6)
        self.assertEqual(h.fill()[1], 1)
        state = bytes(h.cpu.banks[4])
        pointer = word(h.cpu, h.labels['source'])
        self.assertEqual(h.fill()[1], 0)
        self.assertEqual(word(h.cpu, h.labels['source']), pointer)
        # Only the call result is mutable when no FIFO slot is available.
        now = bytearray(h.cpu.banks[4]); before = bytearray(state)
        now[h.labels['emitted']-resident.ORIGIN] = before[h.labels['emitted']-resident.ORIGIN]
        self.assertEqual(now, before)
        while h.consumed < len(records):
            h.consume()
            h.fill()
        h.finish()
        self.assertEqual(word(h.cpu, h.audio['audio_underruns']), 0)

    def test_24_bit_codes_and_refill_boundaries(self):
        # Complete canonical comb tree: lengths 1..23,24,24. The source
        # alternates the deepest values and includes a zero-bit mask context.
        values = list(range(25))*2
        lengths = list(range(1,24))+[24,24]
        bits = ''.join(format((1<<n)-2 if v<24 else (1<<n)-1, '0'+str(n)+'b')
                       for v in values for n in [lengths[v]])
        payload = int(bits+'0'*((-len(bits))%8), 2).to_bytes((len(bits)+7)//8, 'big')
        blob = bytearray(b'AYH1'+struct.pack('<II',len(values),len(bits))+bytes(11))
        contexts = [[(1,0)], [(0,0)], list(zip(range(25), lengths))]+[[]]*10
        for entries in contexts:
            blob.extend(struct.pack('<H',len(entries)))
            blob.extend(v for pair in entries for v in pair)
        blob.extend(payload)
        h = Harness(bytes(blob)); drain(h)
        self.assertEqual(h.records, [bytes([1,0,v]) for v in values])

    def test_payload_ending_at_ffff_wraps_pointer_without_an_extra_read(self):
        # Keep a complete eight-bit mask table with only mask zero used. Size
        # the validated payload to end exactly at the last byte of bank 4.
        count = 16384-(512+26+255*4)
        blob = bytearray(b'AYH1'+struct.pack('<II',count,count*8)+bytes(11))
        for entries in (list(zip(range(256),[8]*256)),[(0,0)],*([[]]*11)):
            blob.extend(struct.pack('<H',len(entries)))
            blob.extend(v for pair in entries for v in pair)
        blob.extend(bytes(count))
        h = Harness(bytes(blob)); c = h.cpu
        self.assertEqual(h.build['image_bytes'],16384)
        # Exercise just the final reader boundary; full-movie coverage is in
        # the separate benchmark. No data are rewritten, only reader state.
        word(c,h.labels['source'],65535); word(c,h.labels['remaining'],1)
        self.assertEqual(h.fill()[1],1)
        self.assertEqual(word(c,h.labels['source']),0)
        self.assertEqual(c.payload_reads,[65535])
        self.assertEqual(h.fill()[1],0)
        self.assertEqual(c.payload_reads,[65535])

    def test_real_irq_after_every_fill_instruction(self):
        rng = random.Random(4802)
        records = [record(mask, lambda r: rng.randrange(256))
                   for mask in [0,2047,1,64,896,7,512,0]*4]
        h = Harness(encode(records, bytes(range(11)))[0])
        while h.cpu.published < len(records):
            _, count = h.fill(h.interrupt)
            self.assertLessEqual(count, 6)
            self.assertGreater(count, 0)
        while h.consumed < len(records): h.consume()
        h.finish()
        self.assertGreater(h.cpu.irq_count, 1000)
        # Intentional stress: one IRQ per instruction is far above 50 Hz.
        # Empty IRQs are expected here; this is not an underrun/cadence test.
        self.assertGreater(word(h.cpu, h.audio['audio_underruns']), 0)

    def test_paging_wrapper_cost_and_all_caller_registers(self):
        records = [record(mask, lambda r: (mask+r)&255) for mask in [2047,0,64,256,1537,9]*4]
        blob = encode(records)[0]
        direct = Harness(blob)
        direct_cost = direct.fill()[0]
        for screen in (0,8):
            for bank in range(8):
                h = Harness(blob, paging=True)
                c = h.cpu
                for n, name in enumerate(REGISTERS):
                    if name not in ('port_7ffd','sp','z','carry','alt_z','alt_carry'):
                        setattr(c,name,(37*n+19)&255)
                c.z = c.carry = c.alt_z = c.alt_carry = True
                c.iff1 = True
                c.port_7ffd = 0x10|screen|bank
                c.write8(video.SHADOW,c.port_7ffd)
                elapsed, emitted = h.fill_wrapped()
                self.assertEqual(emitted,6)
                self.assertEqual(elapsed-direct_cost,436)
                self.assertEqual(h.bridge['overhead_tstates'],436)
                self.assertEqual(h.bridge['code_bytes'],35)
        h = Harness(blob,paging=True)
        h.cpu.port_7ffd = 0x17; h.cpu.write8(video.SHADOW,0x17)
        while h.cpu.published < len(records): h.fill_wrapped(h.interrupt)
        while h.consumed < len(records): h.consume()
        h.finish()
        self.assertGreater(h.cpu.irq_count,1000)

    def test_video_publication_during_both_paging_calls(self):
        # An IRQ may restart the paging merge, so injecting at every instruction
        # forever would prevent forward progress. Inject once per fresh fixture
        # at every paging instruction, for both calls, screen bits and all banks.
        blob = encode([b'\0']*6)[0]
        reference = Harness(blob,paging=True)
        points = sorted(pc for pc in reference.cpu.listing if video.PAGE <= pc < video.SAFE_PAGE_END)
        for screen in (0,8):
            for bank in range(8):
                for call_number in (0,1):
                    for point in points:
                        h = Harness(blob,paging=True); c = h.cpu
                        c.port_7ffd = 0x10|screen|bank; c.write8(video.SHADOW,c.port_7ffd)
                        before = {name:getattr(c,name) for name in REGISTERS}
                        before['port_7ffd'] ^= 8
                        c.iff1 = True
                        c.pc = h.bridge['labels']['fill']; c.push(STOP); c.mode = 'fill'
                        visits = 0
                        while True:
                            if c.pc == point:
                                if visits == call_number: break
                                visits += 1
                            c.step()
                        c.mode = None
                        c.write8(video.ENABLED,1); c.write8(video.READY,1)
                        # Isolate screen publication from AY record consumption.
                        c.write8(h.audio['audio_enabled'],0)
                        word(c,video.DEADLINE,0)
                        saved_sp, saved_pc = c.sp, c.pc
                        c.push(saved_pc); c.pc=0xbdbd; c.iff1=False; c.tstates+=19
                        return_pc = (video.PAGE_MERGE if video.PAGE_MERGE <= point < video.SAFE_PAGE_END else saved_pc)
                        while c.sp != saved_sp or c.pc != return_pc: c.step()
                        self.assertEqual(c.port_7ffd&8,screen^8)
                        c.mode = 'fill'
                        while c.pc != STOP:
                            c.step()
                            self.assertEqual(c.port_7ffd&8,screen^8)
                        c.mode = None
                        self.assertEqual({name:getattr(c,name) for name in REGISTERS},before)
                        self.assertEqual(c.read8(video.SHADOW),c.port_7ffd)
                        self.assertEqual(c.published,6)
                        self.assertEqual(c.sp,STACK)
                        self.assertTrue(c.iff1)

    def test_reject_oversized_bank_tick_counter_and_invalid_input(self):
        audio = Harness(encode([])[0]).audio
        rng = random.Random(249)
        records = [record(2047, lambda r: rng.randrange(256)) for _ in range(2000)]
        with self.assertRaisesRegex(ValueError, '16-KiB'):
            resident.build(encode(records)[0], audio)
        with self.assertRaisesRegex(ValueError, '16 bits'):
            resident.build(encode([b'\0']*65536)[0], audio)
        for batch in (0,32):
            with self.assertRaises(ValueError): resident.build(encode([])[0], audio, batch=batch)
        blob = encode([bytes([1,6,3]),bytes([1,6,18])])[0]
        with self.assertRaises(ValueError): resident.build(blob[:-1], audio)


if __name__ == '__main__': unittest.main()
