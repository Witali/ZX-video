"""Alternate-HL mask cursor, full mask patterns and both real IRQ handlers."""
import compiled_masks_z80 as compiled
import test_compiled_masks_z80 as original
from benchmark_context_huffman import word
from probe_motion_metadata import transform
from test_fap3_disk import install


class HLMaskTests(original.CompiledMaskTests):
    hl_flags=True

    def setUp(self):
        super().setUp()
        for i,name in enumerate(('alt_b','alt_c','alt_d','alt_e','alt_h','alt_l')):
            setattr(self.cpu,name,0x91+7*i)
        self.cpu.ix=0xbeef

    def run_code(self,*args,**kwargs):
        names=('alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','ix')
        before={k:getattr(self.cpu,k) for k in names}
        ticks=super().run_code(*args,**kwargs)
        self.assertEqual(before,{k:getattr(self.cpu,k) for k in names})
        return ticks

    def test_layout_and_complete_loop_costs(self):
        old,ol,_,_=compiled.build();new,nl,_,_=compiled.build(hl_flags=True)
        self.assertEqual(sum(map(lambda v:len(v[1]),new))-sum(map(lambda v:len(v[1]),old)),7)
        self.assertEqual(nl['end']-ol['end'],7)
        for mask in range(256):self.assertEqual(compiled.group_tstates(mask,hl_flags=True),compiled.group_tstates(mask)-8)
        for value in (0,1,255):
            encoded=transform(bytes([value])*480,480,4)
            self.assertEqual(compiled.expected_tstates(encoded,hl_flags=True),compiled.expected_tstates(encoded)-499)

    def test_publication_and_ay_at_every_decoder_boundary(self):
        import ay_interrupt
        import pipelined_frame_z80 as video
        from pipelined_frame_harness import Clock
        from test_pipelined_frame import fixture
        source=bytes((i%255+1) if i%8 in (0,2,4,6) else 0 for i in range(480))
        encoded=transform(source,480,4)
        for slow in (False,True):
            h,_,_=fixture(1,irq_safe_paging=True);ticks=[];clock=Clock(h,ticks);c=h.cpu;c.guarding=False
            c.port_7ffd=0x17;c.write8(video.SHADOW,0x17)
            regions,m,_,generated=compiled.build(hl_flags=True)
            for address,data in regions+generated:install(c,address,data)
            install(c,0x6400,encoded);c.set_hl(0x6400)
            c.alt_h,c.alt_l=0xa1,0x52;c.ix=0xcafe
            saved=tuple(getattr(c,k) for k in ('alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','ix'))
            word(c,0xbdbe,0xbd00 if slow else 0xbd80)
            c.write8(video.ENABLED,1);c.write8(video.READY,1);word(c,video.DEADLINE,0)
            c.write8(h.audio['audio_enabled'],1)
            c.pc=m['decode'];c.sp=0x9df0;c.push(0x5f00);calls=groups=0
            while c.pc!=0x5f00:
                groups+=c.pc==m['groups'];c.step()
                if c.pc==0x5f00:break
                tick=bytes([1,8,calls&15]);ticks.append(tick)
                index=c.read8(h.audio['audio_read_index']);install(c,ay_interrupt.QUEUE_BASE+index*32,tick)
                c.write8(h.audio['audio_write_index'],(index+1)&31);word(c,h.audio['audio_remaining'],65535)
                clock.run_irq();calls+=1;self.assertLess(calls,10000)
            self.assertEqual(groups,68);self.assertEqual(clock.ticks,calls)
            self.assertEqual(len(clock.publications),1);self.assertEqual(c.port_7ffd,0x1f)
            self.assertEqual(c.hl(),0x6400+len(encoded));self.assertEqual(c.sp,0x9df0)
            self.assertEqual(saved,tuple(getattr(c,k) for k in ('alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','ix')))
            self.assertEqual(bytes(c.read8(compiled.MASKS+i) for i in range(480)),source)
            self.assertEqual(bytes(c.read8(compiled.FLAGS+60+i) for i in range(4)),bytes(4))


if __name__=='__main__':
    import unittest
    unittest.main()
