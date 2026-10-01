"""Native CB44 mode boundaries, immutable front reads and absolute cycle deltas."""
import unittest

from build_zxv_trd import spectrum_bitmap_offset
from probe_cell_codebook import mask
from verify_cell_codebook_z80 import Harness,independent


class FrontCellZ80Tests(unittest.TestCase):
    def test_modes_both_screens_and_counted_tstates(self):
        self.case_results=[]
        table=bytes([255])*2048;rows=bytearray(512);rows[1]=rows[257]=255
        for count in (0,1,3,4,5,7,8,9,575,576):
            for target in (7,5):
                old=bytearray();new=bytearray();old_modes=bytearray((count+7)//8);new_modes=bytearray((count+3)//4)
                from_book=from_literal=0
                for i in range(count):
                    mode=i%2;value=b'\0' if mode else b'\1'*4
                    old_modes[i//8]|=mode<<(i%8);old+=value
                    if i%3==0:
                        from_book+=mode;from_literal+=1-mode;mode=2;value=b''
                    new_modes[i//4]|=mode<<((i%4)*2);new+=value
                prefix=mask(list(range(count)),576)+bytes(72)
                old=prefix+old_modes+old;new=prefix+new_modes+new
                before={target:bytes(6912),12-target:bytes([255])*6144+bytes(768)}
                expected={bank:bytearray(value) for bank,value in before.items()}
                for cell in range(count):
                    y,x=divmod(cell,32)
                    for line in range(8):expected[target][spectrum_bitmap_offset(x,(y+3)*8+line)]=255
                expected={k:bytes(v) for k,v in expected.items()}
                initial=before[7]+before[5];high=0xc0 if target==7 else 0x40
                baseline=Harness(table,bytes(rows),initial,True)
                candidate=Harness(table,bytes(rows),initial,True,front_reuse=True)
                a=baseline.run('draw',old,0x6441,high);b=candidate.run('draw',new,0x6441,high)
                delta=-16+13*count+16*((count+3)//4-(count+7)//8)+18*(from_book-from_literal)
                self.assertEqual(b['tstates']-a['tstates'],delta)
                self.case_results.append(dict(cells=count,target=target,baseline_tstates=a['tstates'],
                    candidate_tstates=b['tstates'],delta_tstates=delta,front_from_book=from_book,front_from_literal=from_literal))
                self.assertTrue(all(bytes(candidate.c.banks[k][:6912])==v for k,v in expected.items()))
                independent(candidate,new,0x6441,high,before,expected,b['tstates'])
                if count==576:independent(candidate,new,0x6441,high,before,expected,b['tstates'],interrupts=True)


if __name__=='__main__':unittest.main()
