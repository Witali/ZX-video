"""Partial row-pair mode: independent Z80 screens, boundaries, IRQ and cycles."""
import unittest
from build_zxv_trd import spectrum_bitmap_offset
from probe_cell_codebook import mask
from verify_cell_codebook_z80 import Harness,independent


class PartialRowTests(unittest.TestCase):
    def test_rows_modes_and_full_flag_timings(self):
        self.cases=[]
        table=bytes([255])*2048;rows=bytearray(512)
        rows[1]=240;rows[257]=15;rows[2]=rows[258]=165
        for count in (1,4,9,576):
            for row in range(4):
                for target in (5,7):
                    prefix=mask(list(range(count)),576)+bytes(72)
                    old_modes=bytearray((count+3)//4);new_modes=bytearray(len(old_modes))
                    old=bytearray();new=bytearray();books=partial=0
                    before={target:bytes([165])*6144+bytes(768),12-target:bytes([60])*6144+bytes(768)}
                    expected={k:bytearray(v) for k,v in before.items()}
                    for i in range(count):
                        mode=(i+3)%4;old_mode=mode
                        if mode==3:
                            old_mode=0;value=bytearray([2]*4);value[row]=1
                            old+=value;new+=bytes([row,1]);partial+=1
                            raster=bytearray([165]*8);raster[2*row:2*row+2]=bytes([240,15])
                        elif mode==0:old+=b'\1'*4;new+=b'\1'*4;raster=bytes([240,15])*4
                        elif mode==1:old+=b'\0';new+=b'\0';raster=bytes([255])*8;books+=1
                        else:raster=bytes([60])*8
                        old_modes[i//4]|=old_mode<<((i%4)*2);new_modes[i//4]|=mode<<((i%4)*2)
                        y,x=divmod(i,32)
                        for line,v in enumerate(raster):expected[target][spectrum_bitmap_offset(x,(y+3)*8+line)]=v
                    old=prefix+old_modes+old;new=prefix+new_modes+new
                    initial=before[7]+before[5];high=0xc0 if target==7 else 0x40
                    baseline=Harness(table,bytes(rows),initial,True,front_reuse=True,fast_masks=True)
                    candidate=Harness(table,bytes(rows),initial,True,front_reuse=True,fast_masks=True,partial_rows=True)
                    a=baseline.run('draw',old,0x6441,high);b=candidate.run('draw',new,0x6441,high)
                    self.assertEqual(b['tstates']-a['tstates'],7*books-131*partial)
                    expected={k:bytes(v) for k,v in expected.items()}
                    self.assertTrue(all(bytes(candidate.c.banks[k][:6912])==v for k,v in expected.items()))
                    independent(candidate,new,0x6441,high,before,expected,b['tstates'])
                    if count==576:independent(candidate,new,0x6441,high,before,expected,b['tstates'],interrupts=True)
                    self.cases.append(dict(cells=count,row=row,target=target,book_cells=books,partial_cells=partial,
                        before_tstates=a['tstates'],after_tstates=b['tstates'],delta_tstates=b['tstates']-a['tstates']))


if __name__=='__main__':unittest.main()
