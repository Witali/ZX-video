import unittest
from hashlib import sha256

import ay_interrupt
import banked_zx0 as machine
import playback_schedule
import incremental_zx0
import zx0_codec
from benchmark_banked_zx0 import Harness, STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
from zx0_speed import Token, encode


class BankedZX0Tests(unittest.TestCase):
    def test_default_decoders_keep_previous_machine_code(self):
        a = MiniAssembler(0x7000)
        incremental_zx0.emit_decoder(a)
        incremental_zx0.emit_variables(a)
        for name in ('block_length', 'block_end'):
            a.label(name); a.word(0)
        a.label('block_stored'); a.emit(0)
        a.label('fatal'); a.emit(0x76)
        self.assertEqual(sha256(a.resolve()).hexdigest(),
            '7a7a8c1391106abdaf4e6a2126f067e42bfe506a4908ae5b88367573dbaab9fb')
        a = MiniAssembler(0x8000); zx0_codec.emit_decoder(a)
        self.assertEqual(sha256(a.resolve()).hexdigest(),
            'a9e31b3d78214b99a485fc7664cce77ab3938f425513c68df4d41e5b6c3e8609')

    def test_stored_source_and_history_boundaries_in_all_ring_banks(self):
        for size, start in ((1, 0x3fff), (255, 0x7ff0), (256, 0xbfff), (257, 0xfffe), (8192, 0xfff0)):
            raw = bytes(i % 256 for i in range(size))
            h = Harness(); h.begin(raw, raw, stored=True, ring_start=start, page=0x1f)
            for target in sorted({min(size, n) for n in (1, 127, 128, 255, 256, 257, 8064, 8191, 8192)}):
                h.run(target)
            self.assertLessEqual(h.finish()['private_stack_bytes'], machine.STACK_TOP-machine.STACK_BOTTOM)

    def test_literals_matches_every_output_byte_and_eof(self):
        literal = bytes(range(256))*32
        fixtures = [
            (literal, [Token(0, len(literal))]),
            (b'a'*8192, [Token(0, 1), Token(1, 8191, 1)]),
            (bytes(range(256))*32, [Token(0, 256), Token(256, 7936, 256)]),
        ]
        for index, (raw, tokens) in enumerate(fixtures):
            payload = encode(raw, tokens)
            h = Harness(); h.begin(payload, raw, ring_start=0x3ff1+index*16384)
            # The long match ending at 0000 must stop at every prior target.
            targets = range(1, 8193) if index == 1 else [1, 255, 256, 257, 4095, 8064, 8191, 8192]
            for target in targets:
                h.run(target)
            h.finish()
            h.run(8192)  # Exact already-produced target is a legal no-op.
            for bad in (payload[:-1], payload+b'!'):
                with self.assertRaises((AssertionError, RuntimeError)):
                    broken = Harness(); broken.begin(bad, raw)
                    broken.run(len(raw)); broken.finish()

    def test_irq_at_every_instruction_and_private_stack(self):
        self.exercise_irq()

    def exercise_irq(self,*,token_boundaries=False):
        raw = bytes(range(256))*32
        payload = encode(raw, [Token(0, 300), Token(300, len(raw)-300, 256)])
        h = Harness(fast_literal=True, fast_refill=True,token_boundaries=token_boundaries)
        h.begin(payload, raw, ring_start=0xffff)
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0x9800)
        cpu = h.cpu; cpu.guarding = False
        for i, value in enumerate(a.resolve()):
            cpu.write8(0x9400+i, value)
        cpu.pc, cpu.sp = a.labels['setup_clock'], STACK
        cpu.push(STOP)
        while cpu.pc != STOP:
            cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry', 'alt_a',
                 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l', 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls, private_min = 0, machine.STACK_TOP

        def interrupt(cpu):
            nonlocal calls, private_min
            cpu.guarding = False
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {name: getattr(cpu, name) for name in names}
            private = cpu.sp <= machine.STACK_TOP
            start, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal'])
                if private:
                    private_min = min(private_min, cpu.sp)
                    self.assertGreaterEqual(cpu.sp, machine.STACK_BOTTOM)
                cpu.step()
            self.assertEqual(before, {name: getattr(cpu, name) for name in names})
            self.assertEqual(cpu.ay[8], calls & 15)
            self.assertEqual(cpu.tstates-start, 583)
            calls += 1
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            cpu.guarding = True
            return cpu.tstates-start

        for target in (1, 127, 256, 257, 8064, 8191, 8192):
            h.run(target, interrupt)
        h.finish()
        self.assertGreater(calls, 5000)
        self.assertGreater(machine.STACK_TOP-private_min, 24)


if __name__ == '__main__':
    unittest.main()
