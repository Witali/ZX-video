"""Real-opcode boundary, pending-flag and IRQ-consumer tests of optional reads."""
import unittest
from benchmark_context_huffman import word
from test_fap3_disk import DiskCPU,install
from ready_packet_guard import build,ORIGIN,MAX_PACKET

QUEUE=dict(count=0xe100,read_slot=0xe101,position=0xe102,lengths=0xe110)
AUDIO=dict(audio_read_index=0x9500,audio_write_index=0x9501)
READ,CALLER,PENDING,MARKER=0x7100,0xde80,0xde90,0x9510


def fixture(count,available,occupied,slot=0,read_index=0):
    c=DiskCPU(b'',b'');c.port_7ffd=0x17;c.sp=0x9df0
    code,m=build(QUEUE,AUDIO,READ);install(c,ORIGIN,code)
    install(c,CALLER,bytes([0xcd,ORIGIN&255,ORIGIN>>8,0,0,0x32,PENDING&255,PENDING>>8]))
    # Deliberately return an arbitrary A; guard must publish its own success.
    install(c,READ,bytes([0x3e,0x78,0x32,MARKER&255,MARKER>>8,0xc9]))
    c.write8(QUEUE['count'],count);c.write8(QUEUE['read_slot'],slot)
    word(c,QUEUE['position'],1234);word(c,QUEUE['lengths']+2*slot,1234+available)
    c.write8(AUDIO['audio_read_index'],read_index)
    c.write8(AUDIO['audio_write_index'],(read_index+occupied)&31)
    c.write8(PENDING,0);c.pc=CALLER
    return c,m


class ReadyPacketTests(unittest.TestCase):
    def run_case(self,count,available,occupied,slot=0,read_index=0,consume_at=None):
        c,m=fixture(count,available,occupied,slot,read_index)
        descriptor=bytes(c.read8(0xe100+i) for i in range(32));path=[]
        timing={r['address']:r['tstates'] for r in m['instruction_listing']}
        while c.pc!=CALLER+8:
            if c.pc==consume_at:
                c.write8(AUDIO['audio_read_index'],(read_index+1)&31)
            pc=c.pc;before=c.tstates;path.append(pc);c.step()
            if pc in timing:self.assertEqual(c.tstates-before,timing[pc])
            self.assertLess(len(path),100)
        self.assertEqual(c.sp,0x9df0);self.assertEqual(c.port_7ffd,0x17)
        self.assertEqual(bytes(c.read8(0xe100+i) for i in range(32)),descriptor)
        called=READ in path
        self.assertEqual(c.read8(MARKER),0x78 if called else 0)
        self.assertEqual(c.read8(PENDING),int(called))
        overhead=c.tstates-13-(30 if called else 0) # common pending store; stub body+RET
        return called,overhead,path,m

    def test_bounds_and_cycles(self):
        cases=[(0,8192,0,False,66),(1,4704,0,False,213),
               (1,4705,26,False,271),(1,4705,25,True,291)]
        for count,available,occupied,want,ticks in cases:
            for slot in range(4):
                for read in (0,9,31):
                    with self.subTest(count=count,available=available,occupied=occupied,slot=slot,read=read):
                        called,overhead,_,_=self.run_case(count,available,occupied,slot,read)
                        self.assertEqual(called,want);self.assertEqual(overhead,ticks)

    def test_irq_consumption_can_only_free_capacity(self):
        # Change only shared read_index at every boundary of the real guard.
        # IRQ register preservation is independently tested by test_ay_interrupt.
        for occupancy in (25,26,31):
            _,_,path,_=self.run_case(1,MAX_PACKET,occupancy,3,31)
            for pc in path:
                called,_,_,_=self.run_case(1,MAX_PACKET,occupancy,3,31,pc)
                if occupancy==25:self.assertTrue(called)
                if occupancy==31:self.assertFalse(called)


if __name__=='__main__':unittest.main()
