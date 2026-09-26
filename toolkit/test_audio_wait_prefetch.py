"""AY source pointer, queue-step clobbers, branch cost and idle HALT."""
import unittest
from audio_wait_prefetch import build,ORIGIN
from test_fap3_disk import DiskCPU,install
import ay_interrupt as audio
from build_zxv_trd import MiniAssembler
from test_ay_interrupt import TraceCPU
from benchmark_context_huffman import word


class AudioWaitTests(unittest.TestCase):
    def test_work_and_idle_paths_preserve_source_and_stack(self):
        for work,expected in ((0,80),(1,62)):
            code,m=build(0x7000,0x7100);c=DiskCPU(b'',b'');c.port_7ffd=0x17
            install(c,ORIGIN,code)
            # Simulate a queue step clobbering HL/BC/DE, returning its work flag.
            stub=bytes([0x21,0x34,0x12,0x01,0x78,0x56,0x11,0xbc,0x9a,0x3e,work,0xc9])
            install(c,0x7000,stub);install(c,0x7200,bytes([0xc3,ORIGIN&255,ORIGIN>>8]))
            c.pc=0x7200;c.sp=0x9df0;c.set_hl(0x6578)
            while c.pc!=0x7100:c.step()
            self.assertEqual(c.hl(),0x6578);self.assertEqual(c.sp,0x9df0)
            self.assertEqual(c.port_7ffd,0x17)
            self.assertEqual(c.tstates-(10+10+10+7+10),expected)

    def test_full_ay_queue_wrap_with_consumer_during_prefetch(self):
        def run(c,labels,name):
            c.pc=labels[name];c.push(0x5f00)
            while c.pc!=0x5f00:c.step()
            self.assertEqual(c.sp,0x9df0)
        for work in (0,1):
            a=MiniAssembler(0x6000);audio.emit(a,backpressure=True);audio.emit_variables(a)
            a.label('fatal');a.emit(0x76)
            c=TraceCPU(a.resolve(),b'');c.sp=0x9df0;c.port_7ffd=0x17;c.set_hl(10)
            run(c,a.labels,'audio_init');c.write8(a.labels['audio_enabled'],1)
            word(c,a.labels['audio_remaining'],37)
            for i in range(31):
                at=audio.QUEUE_BASE+32*i
                for j,v in enumerate((1,8,i&15)):c.write8(at+j,v)
            c.write8(a.labels['audio_write_index'],31)
            source=b''.join(bytes((1,9,i)) for i in range(6));address=0x6800
            for i,v in enumerate(source):c.write8(address+i,v)
            code,_=build(0x7000,a.labels['audio_enqueue_one']);install(c,ORIGIN,code)
            hook=a.labels['audio_enqueue_space']-5
            install(c,hook,bytes([0xc3,ORIGIN&255,ORIGIN>>8,0,0]))
            install(c,0x7000,bytes([0x21,0x34,0x12,0x01,0x78,0x56,0x11,0xbc,0x9a,0x3e,work,0xc9]))
            c.pc=a.labels['audio_enqueue_six'];c.set_hl(address);c.push(0x5f00);steps=0
            while c.pc!=0x5f00:
                # Interrupt within the helper's call, after registers have
                # been clobbered; consumer frees one slot for each retry.
                if c.pc==0x700b:
                    resume=c.pc;c.push(resume);c.pc=a.labels['audio_tick']
                    while c.pc!=resume:c.step()
                c.step();steps+=1
                self.assertLess(steps,10000)
            self.assertEqual(c.hl(),address+len(source));self.assertEqual(c.sp,0x9df0)
            while c.read8(a.labels['audio_enabled']):run(c,a.labels,'audio_tick')
            self.assertEqual(c.writes,[(8,i&15) for i in range(31)]+[(9,i) for i in range(6)])
            self.assertEqual(word(c,a.labels['audio_underruns']),0)


if __name__=='__main__':unittest.main()
