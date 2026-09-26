"""Contiguous prefixes, real queue consumption and IRQ-safe peek paging."""
import unittest
from benchmark_context_huffman import word
from test_fap3_disk import DiskCPU,install
from packet_prefix_guard import build,ORIGIN
import pipelined_frame_z80 as video
from test_slot_queue import QueueHarness
from test_direct_slot_input import fixture as producer_fixture
from zx0_speed import Token,encode

QUEUE=dict(count=0xe100,phase=0xe101,read_slot=0xe102,position=0xe104,lengths=0xe110)
ZX0=dict(slice_output=0x8f00)
AUDIO=dict(audio_read_index=0x9550,audio_write_index=0x9551)
READ,CALLER,PENDING,MARKER=0xdc06,0xde80,0xde90,0x9510
BANKS=(0,1,3,4)


def setup(c,count=1,phase=2,position=0,produced=8192,length=294,slot=0,occupied=25,audio=AUDIO,zx0=ZX0):
    c.port_7ffd=0x17;c.sp=0x9df0;c.write8(video.SHADOW,0x17);c.iff1=True
    code,m=build(QUEUE,zx0,audio,READ);install(c,ORIGIN,code)
    install(c,CALLER,bytes([0xcd,ORIGIN&255,ORIGIN>>8,0,0,0x32,PENDING&255,PENDING>>8]))
    install(c,READ,bytes([0x3e,0x78,0x32,MARKER&255,MARKER>>8,0xc9]))
    c.write8(QUEUE['count'],count);c.write8(QUEUE['phase'],phase);c.write8(QUEUE['read_slot'],slot)
    word(c,QUEUE['position'],position);word(c,QUEUE['lengths']+2*slot,produced)
    word(c,zx0['slice_output'],(0xe000+produced)&65535)
    if position<=8190:c.banks[BANKS[slot]][8192+position:8194+position]=length.to_bytes(2,'little')
    c.write8(audio['audio_read_index'],31);c.write8(audio['audio_write_index'],(31+occupied)&31)
    c.write8(PENDING,0);c.write8(MARKER,0);c.pc=CALLER
    return m


class PrefixTests(unittest.TestCase):
    def execute(self,**options):
        c=DiskCPU(b'',b'');regions,_,rows=video.build_video(dict(saved_page=0x9350,screen_base=0x9351),{},
            dict(elapsed_fields=0x9540),irq_safe_paging=True)
        for address,code in regions:install(c,address,code)
        m=setup(c,**options);timing={r['address']:r['tstates'] for r in rows+m['instruction_listing']}
        old=bytes(c.banks[7][0x2100:0x2118]);path=[];total=0
        while c.pc!=CALLER+8:
            pc=c.pc;before=c.tstates
            if pc==READ:self.assertEqual(c.port_7ffd&7,7)
            path.append(pc);c.step();t=c.tstates-before;total+=t
            if pc in timing:self.assertEqual(t,timing[pc])
            self.assertTrue(c.iff1);self.assertLess(len(path),200)
        accepted=READ in path
        self.assertEqual(c.read8(PENDING),int(accepted));self.assertEqual(c.read8(MARKER),0x78 if accepted else 0)
        self.assertEqual(c.sp,0x9df0);self.assertEqual(c.port_7ffd,0x17)
        self.assertEqual(bytes(c.banks[7][0x2100:0x2118]),old)
        return accepted,total-13-(30 if accepted else 0),path,m

    def test_boundaries_and_no_peek_before_header_is_ready(self):
        cases=[(dict(produced=295),False,False),(dict(produced=296),True,True),
            (dict(produced=4705,length=4703),True,True),(dict(produced=4704,length=4703),False,True),
            (dict(position=7896),True,True),(dict(position=8190),False,False),
            (dict(position=8191),False,False),(dict(position=800,produced=700),False,False),
            (dict(occupied=26),False,True)]
        for count in (0,1):
            for slot in range(4):
                for options,want,peek in cases:
                    with self.subTest(count=count,slot=slot,options=options):
                        accepted,_,path,m=self.execute(count=count,slot=slot,**options)
                        self.assertEqual(accepted,want);self.assertEqual(m['peek'] in path,peek)
        for phase in (0,1):
            accepted,_,path,m=self.execute(count=0,phase=phase)
            self.assertFalse(accepted);self.assertNotIn(m['peek'],path)
        for length in (0,293,4704,65534,65535):
            self.assertFalse(self.execute(length=length)[0])

    def test_real_queue_partial_prefix_needs_no_disk_or_decode(self):
        self.real_queue_case(count=0,slot=0,position=0,produced=296,length=294)

    def test_real_queue_end_of_bank_and_slot_release(self):
        for count in (0,1):
            for slot in (0,3):
                for length in (294,4703):
                    with self.subTest(count=count,slot=slot,length=length):
                        self.real_queue_case(count=count,slot=slot,position=8192-length-2,produced=8192,length=length)

    def real_queue_case(self,count,slot,position,produced,length):
        packet=length.to_bytes(2,'little')+bytes(i%251 for i in range(length))
        raw=bytes(position)+packet+bytes(8192-position-len(packet))
        packed=encode(raw,[Token(0,len(raw))]);h=QueueHarness(producer_fixture([(packed,raw)]),1,demand_decode=True)
        c=h.cpu
        # Keep the actual demand queue and copy bridge, but publish a known
        # suspended prefix. Consumption must not enter any producer operation.
        phase=0 if count else 2
        c.port_7ffd=0x17;word(c,h.q['position'],position);c.write8(h.q['count'],count);c.write8(h.q['phase'],phase)
        c.write8(h.q['read_slot'],slot);c.write8(h.q['write_slot'],(slot+count)&3)
        c.banks[BANKS[slot]][8192:8192+produced]=raw[:produced]
        word(c,h.q['lengths']+2*slot,produced)
        word(c,h.h.decoder.labels['slice_output'],(0xe000+produced)&65535);word(c,h.h.decoder.labels['block_length'],8192)
        code,m=build(h.q,h.h.decoder.labels,AUDIO,READ);install(c,ORIGIN,code)
        # Stand-in parser consumes the same two real take calls as FAP3.
        body=bytes([0x11,0x00,0x64,0x01,2,0,0xcd])+h.q['take'].to_bytes(2,'little')
        body+=bytes([0x11,0x02,0x64,0x01])+length.to_bytes(2,'little')+bytes([0xcd])+h.q['take'].to_bytes(2,'little')+bytes([0xc9])
        install(c,READ,body);c.write8(AUDIO['audio_read_index'],0);c.write8(AUDIO['audio_write_index'],0)
        c.pc=ORIGIN;c.sp=0x9df0;c.push(0x5f00);before=len(c.reads);steps=0
        while c.pc!=0x5f00:
            self.assertNotIn(c.pc,(h.q['step'],h.q['run_decode'],h.h.p['begin'],h.h.p['step']))
            c.step();steps+=1;self.assertLess(steps,25000)
        self.assertEqual(c.a,1);self.assertEqual(word(c,h.q['position']),0 if count else position+len(packet))
        self.assertEqual(c.read8(h.q['count']),0);self.assertEqual(c.read8(h.q['phase']),phase)
        self.assertEqual(c.read8(h.q['read_slot']),(slot+count)&3)
        self.assertEqual(bytes(c.read8(0x6400+i) for i in range(len(packet))),packet)
        self.assertEqual(len(c.reads),before);self.assertEqual(c.port_7ffd&7,7);self.assertEqual(c.sp,0x9df0)

    def test_publication_and_ay_during_each_peek_instruction(self):
        from test_pipelined_frame import fixture
        from pipelined_frame_harness import Clock
        import ay_interrupt
        # Include both visits to the paging helper and all guard boundaries.
        _,_,path,_=self.execute(slot=3)
        for slow in (False,True):
            for ordinal in range(len(path)-3):
                h,_,ticks=fixture(1,irq_safe_paging=True);clock=Clock(h,ticks);c=h.cpu;c.guarding=False
                setup(c,slot=3,audio=h.audio)
                word(c,0xbdbe,0xbd00 if slow else 0xbd80)
                c.write8(video.ENABLED,1);c.write8(video.READY,1);word(c,video.DEADLINE,0)
                c.write8(h.audio['audio_enabled'],1);word(c,h.audio['audio_remaining'],6)
                for i,v in enumerate(ticks[0]):c.write8(ay_interrupt.QUEUE_BASE+31*32+i,v)
                count=0
                while c.pc!=CALLER+8:
                    if count==ordinal:clock.run_irq()
                    c.step();count+=1;self.assertLess(count,250)
                self.assertEqual(c.read8(PENDING),1);self.assertEqual(c.port_7ffd,0x1f)
                self.assertEqual(c.sp,0x9df0);self.assertEqual(clock.ticks,1)


if __name__=='__main__':unittest.main()
