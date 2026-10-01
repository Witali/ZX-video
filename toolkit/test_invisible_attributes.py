"""Hidden attributes: future visibility, BRIGHT, physical parity and Z80 cost."""
import unittest
import struct

import numpy as np

from invisible_attribute_writes import colours, retain_runs, attribute_tstates, transform_states, transform_stream, verify_rgb
from dynamic_row_dictionary import decode_check
from probe_cell_codebook import mask
from verify_cell_codebook_z80 import Harness, independent
import five_level_dither as five


class InvisibleAttributeTests(unittest.TestCase):
    def test_retain_only_until_next_original_write(self):
        # A seemingly unused INK becomes visible before the next write.
        attrs=np.array([[2],[2],[3],[3]],dtype=np.uint8)
        ink=np.array([[False],[True],[False],[False]])
        paper=np.ones_like(ink)
        out=retain_runs(attrs,ink,paper,np.array([1],dtype=np.uint8))
        np.testing.assert_array_equal(out[:,0],[2,2,2,2])
        # Without that later visible use both writes disappear.
        out=retain_runs(attrs,np.zeros_like(ink),paper,np.array([1],dtype=np.uint8))
        np.testing.assert_array_equal(out[:,0],[1,1,1,1])
        # Freezing an original write changes later physical history, which
        # must be replanned rather than mixing independently encoded blocks.
        out=retain_runs(attrs,np.zeros_like(ink),paper,np.array([1],dtype=np.uint8),
            np.array([True,False,False,False]))
        np.testing.assert_array_equal(out[:,0],[2,2,2,2])

    def test_bright_and_exhaustive_colours(self):
        for old in range(128):
            for new in range(128):
                attrs=np.array([[new]],dtype=np.uint8)
                for ink,paper in ((True,False),(False,True),(True,True)):
                    out=int(retain_runs(attrs,np.array([[ink]]),np.array([[paper]]),np.array([old]))[0,0])
                    a,b=colours(out),colours(new)
                    self.assertTrue((not ink or a[0]==b[0]) and (not paper or a[1]==b[1]))
        self.assertEqual(colours(0),colours(64))
        self.assertNotEqual(colours(7),colours(71))

    def test_parity_histories_and_rgb(self):
        states=np.zeros((8,4608),dtype=np.uint8)
        for i in range(8):
            levels=np.zeros((96,128),dtype=np.uint8)
            # Frame4 reveals INK on the same physical screen as frame2.
            if i==4:levels[12:16,:4]=4
            states[i,:3840]=np.frombuffer(five.pack_levels(levels),dtype=np.uint8)
            states[i,3840:]=1
            states[i,3936]=2 if 2<=i<=4 else (3 if i>4 else 1)
        out=transform_states(states,2,8)
        self.assertEqual(out[2,3936],2)
        self.assertEqual(out[3,3936],1)
        self.assertEqual(out[5,3936],1)
        self.assertEqual(verify_rgb(states,out,2,8)['visible_pixel_changes'],0)
        np.testing.assert_array_equal(states[:2],out[:2])

    def test_native_attribute_cost_delta(self):
        for group in (0,19,51,71):
            for old_value,new_value in ((1,0),(255,0),(255,0x55)):
                measured=[]
                for value in (old_value,new_value):
                    cells=[group*8+i for i in range(8) if value&(1<<i)]
                    bits=mask(cells,576)
                    payload=bytes(72)+bits+bytes([71])*len(cells)
                    before={5:bytes(6912),7:bytes(6912)}
                    expected={k:bytearray(v) for k,v in before.items()}
                    for c in cells:expected[7][6240+c]=71
                    h=Harness(bytes(2048),bytes(512),before[7]+before[5],True,
                        front_reuse=True,fast_masks=True,partial_rows=True,inline_cells=True)
                    result=h.run('draw',payload,0x6441,0xc0)
                    expected={k:bytes(v) for k,v in expected.items()}
                    independent(h,payload,0x6441,0xc0,before,expected,result['tstates'])
                    measured.append((result['tstates'],attribute_tstates(bits)))
                self.assertEqual(measured[1][0]-measured[0][0],measured[1][1]-measured[0][1])
                self.assertLess(measured[1][0],measured[0][0])

    def test_stream_restoration_and_block_mapping(self):
        states=np.zeros((6,4608),dtype=np.uint8);states[:,3840:]=1
        states[2:4,3936]=2;states[4:6,3936]=3
        raw=b'CB46'+struct.pack('<HH',4,256)+bytes(2048)
        for f in range(2,6):
            packet=bytes(72)+mask([0],576)+bytes([states[f,3936]])
            raw+=struct.pack('<H',len(packet))+packet
        rows=dict(tables_hex=bytes(512).hex())
        for bits in range(16):
            frozen={2+i for i in range(4) if bits&(1<<i)}
            changed=transform_states(states,2,6,frozen)
            coded,mapping,details=transform_stream(raw,states,changed,2,6,frozen)
            self.assertEqual(len(raw)-len(coded),sum(d['removed'] for d in details))
            self.assertEqual(mapping[-1],len(coded))
            self.assertTrue(np.all((np.diff(mapping)==0)|(np.diff(mapping)==1)))
            self.assertTrue(decode_check(coded,changed,2,6,rows)['both_screens_exact'])
            self.assertEqual(verify_rgb(states,changed,2,6)['visible_pixel_changes'],0)
            if bits==15:
                self.assertEqual(raw,coded)
                np.testing.assert_array_equal(states,changed)


if __name__=='__main__':unittest.main()
