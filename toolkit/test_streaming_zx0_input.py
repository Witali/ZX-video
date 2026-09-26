"""Test sector-frontier suspension with poisoned input and real AY IRQ code."""
import unittest

import ay_interrupt
import playback_schedule
from benchmark_context_huffman import word
from benchmark_streaming_zx0_input import Harness,STACK,STOP
from build_zxv_trd import MiniAssembler
import streaming_local_zx0 as machine
from zx0_speed import Token,encode


class StreamingInputTests(unittest.TestCase):
    def test_zero_output_begin_can_wait_for_a_split_length_header(self):
        raw=bytes(i%251 for i in range(7900));payload=encode(raw,[Token(0,len(raw))])
        h=Harness();h.begin(payload,raw,input_offset=255)
        c=h.cpu;h.run(0)
        self.assertEqual(c.produced,0);self.assertTrue(c.read8(h.labels['input_needed']))
        h.supply();h.run(0)
        self.assertEqual(c.produced,0);self.assertFalse(c.read8(h.labels['input_needed']))
        self.assertFalse(c.read8(h.labels['finished']))
        c.port_7ffd=0x16;c.port_7ffd=h.page
        h.decode()

    def test_long_literals_matches_offsets_and_final_pages(self):
        fixtures=[]
        for n in (1,127,255,256,257,511,4096,7900):
            raw=bytes(i%251 for i in range(n));fixtures.append((raw,encode(raw,[Token(0,n)])))
        raw=bytes(range(256))*32
        fixtures.append((raw,encode(raw,[Token(0,300),Token(300,7892,256)])))
        # Alternating literals/old and new offsets; short runs exercise the
        # bit refill while long matches exercise wrapped output and EOF.
        raw=bytes(range(128))*64
        fixtures.append((raw,encode(raw,[Token(0,128),Token(128,128,128),
            Token(256,128),Token(384,128,256),Token(512,7680,128)])))
        for raw,payload in fixtures:
            for offset in (0,1,252,253,255,256,259,8192-len(payload)):
                if offset+len(payload)>8192:continue
                for preload in (False,True):
                    with self.subTest(n=len(raw),offset=offset,preload=preload):
                        h=Harness();h.begin(payload,raw,input_offset=offset,slot=3,screen_bit=8,preload=preload)
                        result=h.decode(quantum=127)
                        self.assertEqual(result['input_waits'],0 if preload else result['supplied_pages']-1)
                        self.assertLessEqual(result['private_stack_bytes'],machine.STACK_TOP-machine.STACK_BOTTOM)

    def test_no_implicit_supply_and_pending_eof(self):
        found_pending_eof=False
        raw=bytes(range(128))*64
        payload=encode(raw,[Token(0,128),Token(128,len(raw)-128,128)])
        for offset in range(256):
            h=Harness();h.begin(payload,raw,input_offset=offset)
            c=h.cpu;h.run(len(raw))
            if c.read8(h.labels['input_needed']):
                before=c.input_reads;produced=c.produced
                # Resuming without a supplied page must simply suspend again.
                h.run(len(raw));self.assertEqual(c.input_reads,before);self.assertEqual(c.produced,produced)
                if c.produced==len(raw):
                    found_pending_eof=True;self.assertFalse(c.read8(h.labels['finished']))
                h.supply();h.run(len(raw))
            h.finish()
        self.assertTrue(found_pending_eof)

    def test_truncated_input_fails(self):
        raw=bytes(range(100))*5;payload=encode(raw,[Token(0,100),Token(100,400,100)])
        for bad in (payload[:-1],payload+b'!'):
            h=Harness();h.begin(bad,raw)
            with self.assertRaises((AssertionError,RuntimeError)):h.decode()

    def test_ay_irq_at_every_instruction_through_input_suspensions(self):
        raw=bytes(range(256))*4
        payload=encode(raw,[Token(0,600),Token(600,424,256)])
        h=Harness();h.begin(payload,raw,input_offset=253,slot=4,screen_bit=8)
        a=MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a);a.label('elapsed_fields');a.word(0);a.label('fatal');a.emit(0x76)
        c=h.cpu
        for i,v in enumerate(a.resolve()):c.write8(0x9400+i,v)
        c.pc,c.sp=a.labels['setup_clock'],STACK;c.push(STOP)
        while c.pc!=STOP:c.step()
        c.write8(a.labels['audio_enabled'],1)
        names=('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b','alt_c',
            'alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls=0;private_min=machine.STACK_TOP
        def irq(c):
            nonlocal calls,private_min
            c.guarding=False;word(c,a.labels['audio_remaining'],65535)
            index=c.read8(a.labels['audio_read_index']);slot=ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            c.write8(slot,1);c.write8(slot+1,8);c.write8(slot+2,calls&15)
            c.write8(a.labels['audio_write_index'],(index+1)&31)
            before={n:getattr(c,n) for n in names};started,pc=c.tstates,c.pc;private=c.sp<=machine.STACK_TOP
            c.push(pc);c.pc=0xbdbd;c.iff1=False;c.tstates+=19
            while c.pc!=pc:
                self.assertNotEqual(c.pc,a.labels['fatal'])
                if private:
                    private_min=min(private_min,c.sp);self.assertGreaterEqual(c.sp,machine.STACK_BOTTOM)
                c.step()
            self.assertEqual(before,{n:getattr(c,n) for n in names})
            self.assertEqual(c.ay[8],calls&15);self.assertEqual(c.tstates-started,583)
            calls+=1;self.assertEqual(word(c,a.labels['elapsed_fields']),calls&65535)
            self.assertEqual(word(c,a.labels['audio_underruns']),0)
            c.guarding=True;return c.tstates-started
        result=h.decode(127,irq)
        self.assertGreater(result['input_waits'],0)
        self.assertEqual(calls,sum(h.histogram.values())-len(h.slices))
        self.assertLess(private_min,machine.STACK_TOP-24)


if __name__=='__main__':unittest.main()
