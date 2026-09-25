import unittest
import ay_interrupt

from benchmark_context_huffman import word
from pipelined_frame_harness import Clock
import pipelined_frame_z80 as video
from stream_reader_harness import STACK,STOP
from test_pipelined_frame import fixture


class IrqSafePagingTests(unittest.TestCase):
    def test_publish_at_every_paging_instruction_and_bank(self):
        # Exercise both the ordinary and ROM-safe outer ISR stack layouts.
        for slow in (False,True):
            h,_,ticks=fixture(1,irq_safe_paging=True);clock=Clock(h,ticks);cpu=h.cpu
            points=sorted(pc for pc in h.instructions if video.PAGE<=pc<h.video['page_end'])
            for screen in (0,8):
                for old_bank in range(8):
                    for bank in range(8):
                        for point in points:
                            cpu.guarding=False;cpu.port_7ffd=0x10|screen|old_bank
                            cpu.write8(video.SHADOW,cpu.port_7ffd)
                            word(cpu,0xbdbe,0xbd00 if slow else 0xbd80)
                            cpu.write8(video.ENABLED,1);cpu.write8(video.READY,1)
                            cpu.write8(h.audio['audio_enabled'],1)
                            cpu.write8(h.audio['audio_read_index'],0);cpu.write8(h.audio['audio_write_index'],1)
                            word(cpu,h.audio['audio_remaining'],6);clock.ticks=0
                            for i,value in enumerate(ticks[0]): cpu.write8(ay_interrupt.QUEUE_BASE+i,value)
                            word(cpu,video.DEADLINE,0);word(cpu,h.audio['elapsed_fields'],0)
                            cpu.pc=video.PAGE;cpu.a=0x10|bank;cpu.sp=STACK;cpu.push(STOP)
                            cpu.iff1=True;cpu.phase='paging';cpu.guarding=True
                            foreground=0
                            while cpu.pc!=point:
                                t=cpu.tstates;cpu.step();foreground+=cpu.tstates-t
                            clock.run_irq()
                            self.assertEqual(clock.ticks,1)
                            self.assertEqual(cpu.port_7ffd&8,screen^8)
                            while cpu.pc!=STOP:
                                self.assertTrue(cpu.iff1)
                                t=cpu.tstates;cpu.step();foreground+=cpu.tstates-t
                                self.assertEqual(cpu.port_7ffd&8,screen^8)
                            self.assertEqual(cpu.port_7ffd,0x10|bank|(screen^8))
                            self.assertEqual(cpu.read8(video.SHADOW),cpu.port_7ffd)
                            self.assertEqual(cpu.sp,STACK)
                            self.assertGreaterEqual(foreground,92)

    def test_irq_without_publication_never_restarts(self):
        h,_,ticks=fixture(1,irq_safe_paging=True);clock=Clock(h,ticks);cpu=h.cpu
        points=sorted(pc for pc in h.instructions if video.PAGE<=pc<h.video['page_end'])
        for point in points:
            cpu.guarding=False;cpu.port_7ffd=0x17;cpu.write8(video.SHADOW,0x17)
            cpu.write8(video.ENABLED,1);cpu.write8(video.READY,0)
            cpu.pc=video.PAGE;cpu.a=0x13;cpu.sp=STACK;cpu.push(STOP);cpu.iff1=True
            cpu.phase='paging';cpu.guarding=True;elapsed=0
            while cpu.pc!=point:
                t=cpu.tstates;cpu.step();elapsed+=cpu.tstates-t
            clock.run_irq();self.assertEqual(cpu.pc,point)
            while cpu.pc!=STOP:
                t=cpu.tstates;cpu.step();elapsed+=cpu.tstates-t
            self.assertEqual(elapsed,92);self.assertEqual(cpu.port_7ffd,0x13)

    def test_unchanged_irq_branches_and_paging_cost(self):
        for safe in (False,True):
            h,_,ticks=fixture(1,irq_safe_paging=safe);clock=Clock(h,ticks);cpu=h.cpu
            for enabled,ready,deadline,wanted in ((0,0,0,58),(1,0,0,85),(1,1,100,179)):
                cpu.guarding=False;cpu.pc=0x93f0
                cpu.write8(video.ENABLED,enabled);cpu.write8(video.READY,ready)
                word(cpu,video.DEADLINE,deadline)
                self.assertEqual(clock.run_irq(),191+17+wanted)
            cpu.guarding=False;cpu.a=0x13;cpu.pc=video.PAGE;cpu.sp=STACK;cpu.push(STOP)
            cpu.phase='paging';cpu.guarding=True;t=cpu.tstates
            while cpu.pc!=STOP: cpu.step()
            self.assertEqual(cpu.tstates-t,92 if safe else 88)

    def test_complete_pipeline_irq_restart(self):
        h,states,ticks=fixture(8,bar=True,packet_ahead='idle',irq_safe_paging=True)
        clock=Clock(h,ticks,lookahead=True)
        clock.prime();clock.start()
        for _ in range(7): clock.play_one()
        clock.drain()
        self.assertEqual(clock.ticks,48)
        self.assertEqual(len(clock.publications),8)
        self.assertFalse(any(p['late_fields'] for p in clock.publications))
        self.assertEqual(bytes(h.cpu.banks[5][0x2400:0x3300]),states[-1].tobytes())


if __name__=='__main__': unittest.main()
