"""Unrolled CB46 cells: sparse/dense masks, both screens, IRQs and exact cycles."""
import unittest

from probe_cell_codebook import mask
from verify_cell_codebook_z80 import Harness,independent


class InlineCellTests(unittest.TestCase):
    def test_exact_pixels_and_seventeen_tstates_per_changed_cell(self):
        self.cases=[]
        table=bytes((i*37+i//8)%256 for i in range(2048))
        rows=bytes((i*53)%256 for i in range(512))
        for count in (0,1,4,9,31,256,576):
            for target in (5,7):
                for shift in (0,3):
                    # Coprime permutation crosses byte groups, screen bands,
                    # sparse masks, mode-byte refills and the final cell.
                    cells=sorted((i*137+shift)%576 for i in range(count))
                    attrs=list(range(0,576,7));modes=bytearray((count+3)//4);body=bytearray()
                    for i,cell in enumerate(cells):
                        mode=(i+shift)%4;modes[i//4]|=mode<<((i%4)*2)
                        body+=bytes([cell%256]*4) if mode==0 else bytes([cell%256]) if mode==1 else b'' if mode==2 else bytes([i%4,cell%256])
                    packet=mask(cells,576)+mask(attrs,576)+modes+body+bytes(i%128 for i in attrs)
                    before={7:bytes([165])*6912,5:bytes([60])*6912};initial=before[7]+before[5]
                    old=Harness(table,rows,initial,True,front_reuse=True,fast_masks=True,partial_rows=True)
                    new=Harness(table,rows,initial,True,front_reuse=True,fast_masks=True,partial_rows=True,inline_cells=True)
                    high=0xc0 if target==7 else 0x40;source=0x6441
                    a=old.run('draw',packet,source,high);b=new.run('draw',packet,source,high)
                    self.assertEqual(b['tstates']-a['tstates'],-17*count)
                    expected={k:bytes(old.c.banks[k][:6912]) for k in before}
                    self.assertTrue(all(bytes(new.c.banks[k][:6912])==v for k,v in expected.items()))
                    independent(new,packet,source,high,before,expected,b['tstates'])
                    if count==576:independent(new,packet,source,high,before,expected,b['tstates'],interrupts=True)
                    self.cases.append(dict(cells=count,target=target,shift=shift,before=a['tstates'],after=b['tstates'],delta=b['tstates']-a['tstates']))


if __name__=='__main__':unittest.main()
