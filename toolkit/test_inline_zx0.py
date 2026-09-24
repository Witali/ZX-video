"""Exact stream, suspension, instruction-cost and IRQ checks for inline matches."""
import unittest
from benchmark_banked_zx0 import Harness
import test_banked_zx0
from test_stream_reader_z80 import blocks
from stream_reader_harness import Harness as Reader
from zx0_speed import Token,encode


class InlineZX0Tests(unittest.TestCase):
    def compare(self, raw, tokens, targets, *, stored=False, start=0xffff):
        payload=raw if stored else encode(raw,tokens)
        results=[]
        for inline in (False,True):
            h=Harness(fast_literal=True,fast_refill=True,token_boundaries=True,inline_matches=inline,profile=True)
            h.begin(payload,raw,stored=stored,ring_start=start,page=0x1f)
            for target in targets: h.run(target)
            h.finish()
            counts=lambda name:sum(count for (pc,_),count in h.histogram.items() if pc==h.labels[name])
            results.append((h.total,counts('slice_sync_target'),counts('dzx0t_copy')))
        old,new=results
        self.assertEqual(old[1:],new[1:])
        # 3 extra absolute stores of target operands, 13 T each. Every
        # completed match avoids CALL 17 T and RET 10 T; copy bytes are exact.
        self.assertEqual(new[0]-old[0],39*old[1]-27*old[2])
        return results

    def test_boundaries_resume_and_exact_cycle_formula(self):
        for size in (1,255,256,257,8191,8192):
            raw=b'a'*size; tokens=[Token(0,1)]+([Token(1,size-1,1)] if size>1 else [])
            targets=sorted({min(size,n) for n in (1,2,127,255,256,257,512,4095,8191,8192)})
            for stored in (False,True): self.compare(raw,tokens,targets,stored=stored)
        raw=bytes(range(256))*32
        self.compare(raw,[Token(0,300),Token(300,len(raw)-300,256)],[1,128,256,300,301,8192],start=0x3fff)

    def test_many_short_matches_save_expected_tstates(self):
        raw=b'abc'*1000
        tokens=[Token(0,3)]+[Token(i,3,3) for i in range(3,len(raw),3)]
        old,new=self.compare(raw,tokens,[256,512,1024,2048,len(raw)])
        self.assertLess(new[0],old[0])

    def test_full_reader_multiple_blocks_and_ring_wrap(self):
        first=bytes(range(256))*32; second=b'z'*8192
        data,wanted=blocks([(first,None),(second,encode(second,[Token(0,1),Token(1,8191,1)]))]*5+[(b'final',None)])
        for start in (0x3fff,0xffff):
            h=Reader(data,ring_start=start,token_boundaries=True,unrolled_copy=True,inline_matches=True)
            position=0
            while position<len(wanted):
                count=min(257,len(wanted)-position)
                self.assertEqual(h.take(count),wanted[position:position+count]);position+=count
            self.assertEqual(h.cpu.consumed,len(data))

    def test_actual_ay_irq_at_every_instruction(self):
        test_banked_zx0.BankedZX0Tests().exercise_irq(token_boundaries=True,inline_matches=True)


if __name__=='__main__':unittest.main()
