"""Boundary, caller-state and real AY interrupt checks for the experimental core."""
import unittest

import ay_interrupt
import bank_local_zx0 as machine
import playback_schedule
from benchmark_bank_local_zx0 import Harness, STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
from zx0_speed import Token, encode


class LocalZX0Tests(unittest.TestCase):
    def test_literals_matches_slots_and_unchanged_protected_banks(self):
        for slot in machine.BANKS:
            for size in (1, 255, 256, 257, 8192):
                raw = bytes(i%251 for i in range(size))
                # The longest literal-only compressed block exceeds 8 KiB;
                # stored and compressed forms exercise distinct entry paths.
                for stored in (False, True):
                    tokens = ([Token(0, size)] if size <= 251 else
                        [Token(0, 251), Token(251, size-251, 251)])
                    payload = raw if stored else encode(raw, tokens)
                    h = Harness(); h.begin(payload, raw, slot=slot, screen_bit=8, stored=stored)
                    for target in sorted({min(size,n) for n in (1,127,255,256,257,4095,8191,8192)}):
                        # Paging away while suspended must not change decoder state.
                        h.cpu.port_7ffd = 0x16
                        h.cpu.port_7ffd = h.page
                        h.run(target)
                    self.assertLessEqual(h.finish()['private_stack_bytes'], machine.STACK_TOP-machine.STACK_BOTTOM)
                    h.run(size)
        with self.assertRaises(ValueError): Harness().begin(bytes(8193), bytes(8192))

    def test_truncated_and_extra_compressed_input_fail(self):
        raw = bytes(range(100))*5
        payload = encode(raw,[Token(0,100),Token(100,400,100)])
        for bad in (payload[:-1],payload+b'!'):
            h = Harness(); h.begin(bad, raw)
            with self.assertRaises((AssertionError, RuntimeError)):
                h.run(len(raw)); h.finish()

    def test_ay_interrupt_at_every_decoder_instruction(self):
        self.exercise_irq()

    def test_dynamic_input_ay_interrupt_at_every_decoder_instruction(self):
        self.exercise_irq(dynamic=True)

    def exercise_irq(self,*,dynamic=False):
        raw = bytes(range(256))*32
        payload = encode(raw,[Token(0,300),Token(300,len(raw)-300,256)])
        h = Harness(dynamic_input=dynamic)
        h.begin(payload,raw,slot=3,screen_bit=8,input_offset=259 if dynamic else 0)
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        cpu=h.cpu
        for i,v in enumerate(a.resolve()): cpu.write8(0x9400+i,v)
        cpu.pc,cpu.sp=a.labels['setup_clock'],STACK; cpu.push(STOP)
        while cpu.pc!=STOP: cpu.step()
        cpu.write8(a.labels['audio_enabled'],1)
        names=('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b','alt_c',
               'alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls=0; private_min=machine.STACK_TOP
        def irq(cpu):
            nonlocal calls,private_min
            cpu.guarding=False
            word(cpu,a.labels['audio_remaining'],65535)
            index=cpu.read8(a.labels['audio_read_index'])
            slot=ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot,1); cpu.write8(slot+1,8); cpu.write8(slot+2,calls&15)
            cpu.write8(a.labels['audio_write_index'],(index+1)&31)
            before={n:getattr(cpu,n) for n in names}; started,pc=cpu.tstates,cpu.pc
            private=cpu.sp<=machine.STACK_TOP
            cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
            while cpu.pc!=pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal'])
                if private:
                    private_min=min(private_min,cpu.sp)
                    self.assertGreaterEqual(cpu.sp,machine.STACK_BOTTOM)
                cpu.step()
            self.assertEqual(before,{n:getattr(cpu,n) for n in names})
            self.assertEqual(cpu.ay[8],calls&15)
            self.assertEqual(cpu.tstates-started,583)
            calls+=1
            self.assertEqual(word(cpu,a.labels['elapsed_fields']),calls&65535)
            self.assertEqual(word(cpu,a.labels['audio_underruns']),0)
            cpu.guarding=True
            return cpu.tstates-started
        for target in (1,127,256,257,8064,8191,8192): h.run(target,irq)
        h.finish()
        self.assertGreater(calls,5000)
        self.assertGreater(machine.STACK_TOP-private_min,24)


if __name__=='__main__': unittest.main()
