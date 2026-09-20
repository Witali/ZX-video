import random
import unittest

import banked_zx0
from benchmark_compact_screen import NativeCPU
from benchmark_context_huffman import word
from frame_output_pipeline import display_screen
from pipelined_frame_harness import Clock
from stream_reader_harness import Harness
import stream_reader_z80 as reader
from test_pipelined_frame import fixture
from test_stream_reader_z80 import blocks
from zx0_speed import Token,encode


class UnrolledCopyTests(unittest.TestCase):
    def test_all_remainders_counts_flags_and_instruction_timing(self):
        _,z=banked_zx0.build()
        rng=random.Random(73)
        counts=list(range(1,513))+[1023,1024,1025,4095,4096,4703,4704,8191,8192]
        counts += [rng.randrange(1,8193) for _ in range(24)]
        for fast in (False,True):
            code,_,labels,listing=reader.build(z,unrolled_copy=fast)
            self.assertLessEqual(labels['end'],0xdc00)
            allowed={r['address']:r['tstates'] for r in listing}
            cpu=NativeCPU(b'',b''); cpu.port_7ffd=0x17
            for i,v in enumerate(code): cpu.write8(reader.CODE+i,v)
            source=bytes(rng.randrange(256) for _ in range(8192))
            for i,v in enumerate(source): cpu.write8(0xe000+i,v)
            for count in counts:
                cpu.pc=labels['copy']; cpu.set_bc(count); cpu.set_hl(0xe000); cpu.set_de(0x8000)
                cpu.z=bool(count&1); cpu.carry=bool(count&2)
                start=cpu.tstates
                while cpu.pc!=labels['copy_end']:
                    pc,t=cpu.pc,cpu.tstates; cpu.step(); expected=allowed[pc]
                    self.assertIn(cpu.tstates-t,expected if isinstance(expected,list) else [expected])
                self.assertEqual(cpu.tstates-start,reader.copy_tstates(count,unrolled=fast))
                self.assertEqual((cpu.bc(),cpu.hl(),cpu.de()),(0,(0xe000+count)&65535,0x8000+count))
                self.assertEqual(bytes(cpu.read8(0x8000+i) for i in range(count)),source[:count])

    def test_continuous_stored_compressed_ring_and_block_boundaries(self):
        first=bytes(range(256))*32; second=b'z'*8192
        stream,expected=blocks([(first,None),
            (second,encode(second,[Token(0,1),Token(1,8191,1)]))]*5+[(b'end',None)])
        for start in (0x3fff,0xffff):
            h=Harness(stream,ring_start=start,token_boundaries=True,unrolled_copy=True)
            self.assertEqual(h.take(0),b'')
            pos=0; sizes=(1,2,15,16,31,32,33,255,256,257,4704)
            while pos<len(expected):
                for size in sizes:
                    n=min(size,len(expected)-pos)
                    if not n: break
                    self.assertEqual(h.take(n),expected[pos:pos+n]); pos+=n
            self.assertEqual(h.cpu.consumed,len(stream))
            self.assertEqual(word(h.cpu,h.r['block_left']),0)

    def test_scheduled_irq_masks_and_final_audio_drain(self):
        for policy in (False,True,'idle'):
            h,states,ticks=fixture(8,packet_ahead=policy,unrolled_copy=True)
            seen=0
            def observe(kind,clock):
                nonlocal seen
                if kind=='publish':
                    bank=7 if seen%2==0 else 5
                    self.assertEqual(bytes(h.cpu.banks[bank][:6912]),
                        display_screen(states[seen].tobytes(),black_borders=True))
                    seen+=1
            clock=Clock(h,ticks,lookahead=True,observer=observe)
            clock.prime(); clock.start()
            for _ in range(7): clock.play_one()
            clock.drain()
            self.assertEqual((seen,clock.ticks),(8,48))
            self.assertFalse(any(r['late_fields'] for r in clock.publications))
            self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))


if __name__=='__main__': unittest.main()
