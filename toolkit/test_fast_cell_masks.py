"""Exact sparse mask skipping, inlined attributes and instruction-count deltas."""
import unittest

from verify_cell_codebook_z80 import Harness, independent


def delta(packet):
    bitmap, attrs = packet[:72], packet[72:144]
    zb, za = bitmap.count(0), attrs.count(0)
    carries = sum(value == 0 and (96+8*i)%256 == 248 for i,value in enumerate(attrs))
    changed = sum(value.bit_count() for value in attrs)
    return 3168-119*zb-139*za-carries-22*changed


class FastCellMaskTests(unittest.TestCase):
    def test_all_masks_both_screens(self):
        self.results=[]
        rows=bytes((i*37+19)%256 for i in range(512))
        table=bytes((i*23+i//8)%256 for i in range(2048))
        masks=[bytes(72),bytes([255])*72]
        masks += [bytes((i+start)%256 for i in range(72)) for start in (0,72,144,216)]
        for front in (False,True):
            for target in (7,5):
                for bitmap in masks:
                    attrs=bitmap[::-1];count=sum(v.bit_count() for v in bitmap)
                    modes=bytearray((count+(3 if front else 7))//(4 if front else 8));data=bytearray()
                    for i in range(count):
                        mode=i%(3 if front else 2)
                        modes[i//(4 if front else 8)] |= mode << ((i%(4 if front else 8))*(2 if front else 1))
                        data += bytes([(i*11)%256]) if mode==1 else bytes((i+j*31)%256 for j in range(4)) if mode==0 else b''
                    data += bytes((i*7)&127 for i in range(sum(v.bit_count() for v in attrs)))
                    packet=bitmap+attrs+modes+data
                    before={bank:bytes((i*29+bank*37)%256 for i in range(6912)) for bank in (5,7)}
                    initial=before[7]+before[5];high=0xc0 if target==7 else 0x40
                    old=Harness(table,rows,initial,True,front_reuse=front)
                    new=Harness(table,rows,initial,True,front_reuse=front,fast_masks=True)
                    a=old.run('draw',packet,0x6400,high);b=new.run('draw',packet,0x6400,high)
                    expected={k:bytes(old.c.banks[k][:6912]) for k in (5,7)}
                    self.assertEqual(b['tstates']-a['tstates'],delta(packet))
                    self.assertEqual(expected,{k:bytes(new.c.banks[k][:6912]) for k in (5,7)})
                    independent(new,packet,0x6400,high,before,expected,b['tstates'])
                    if bitmap==bytes([255])*72:
                        independent(new,packet,0x6400,high,before,expected,b['tstates'],interrupts=True)
                    self.results.append(dict(front_reuse=front,target=target,mask_start=bitmap[0],
                        bitmap_zero_groups=bitmap.count(0),attribute_zero_groups=attrs.count(0),
                        before_tstates=a['tstates'],after_tstates=b['tstates'],delta_tstates=delta(packet)))


if __name__=='__main__':unittest.main()
