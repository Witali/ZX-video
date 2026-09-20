import unittest

import numpy as np
import cell_screen_z80 as machine
import test_cell_screen as existing
from benchmark_cell_screen import Harness
from frame_output_pipeline import Harness as Pipeline,frames,serialized_masks
from raw_attribute_stream import pack
from test_frame_output_pipeline import fixture
from probe_sparse_motion_cache import coverage


def sparse_cells(mask,first=0,count=20):
    return sum(sum(v.bit_count() for v in mask[i*4:i*4+4])
        for i in range(first,first+count) if mask[i*4:i*4+4]!=b'\xff'*4)


class GrayCellTests(unittest.TestCase):
    def test_every_mask_value_cell_column_and_native_bank(self):
        old=Harness(fast_mask_dispatch=True); new=Harness(fast_mask_dispatch=True,gray_cells=True)
        states=[bytearray(3840),bytearray(3840)]; seen_masks=set(); seen_values=set()
        for index in range(4):
            state=states[index%2]; mask=bytes((index*80+i)%256 for i in range(80))
            seen_masks.update(mask)
            for pos,flags in enumerate(mask):
                band,octet=divmod(pos,4)
                for bit in range(8):
                    if flags&(128>>bit):
                        col=octet*8+bit
                        for row in range(8+band*4,12+band*4):
                            v=(index*61+row*37+col*13)&255
                            state[row*32+col]=v; seen_values.add(v)
            state[3072:]=bytes([index+1])*768
            a,b=old.run(state,mask,index),new.run(state,mask,index)
            self.assertEqual(b['tstates']-a['tstates'],-35*sparse_cells(mask))
        self.assertEqual(seen_masks,set(range(256))); self.assertEqual(seen_values,set(range(256)))
        # Dense bands and empty frames keep exactly the previous cost.
        for index,mask in ((4,b'\xff'*80),(5,bytes(80))):
            state=states[index%2]
            self.assertEqual(new.run(state,mask,index)['tstates'],old.run(state,mask,index)['tstates'])

    def test_integrated_reconstruction_and_both_screens(self):
        states,stream,_=fixture(4,constant_attribute_borders=True)
        stream,_=pack(stream,states,[True,False,True,False]); tables,mapping,packets=frames(stream)
        meta=serialized_masks(stream)
        options=dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,selective_cache=True,
            constant_attribute_borders=True,skip_black_borders=True,unrolled_cache=True,
            attribute_groups=True,attribute_flags=True)
        old=Pipeline(tables,mapping,**options); new=Pipeline(tables,mapping,gray_cells=True,**options)
        for i,((group,mask),state) in enumerate(zip(packets,states)):
            cache=np.packbits(coverage(group[3],32).reshape(24,4).any(axis=1)).tobytes()
            a=old.run(group,mask,state.tobytes(),i,encoded_metadata=meta[i],cache_map=cache)
            b=new.run(group,mask,state.tobytes(),i,encoded_metadata=meta[i],cache_map=cache)
            self.assertEqual(b['total_tstates']-a['total_tstates'],-35*sparse_cells(mask,1,18))

    def test_irq_after_each_instruction_with_alternate_flags(self):
        existing.CellScreenTests().exercise_irq(fast=True,gray_cells=True)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError): machine.build(gray_cells=True)
        with self.assertRaises(ValueError): machine.expected_tstates(bytes(80),gray_cells=True)


if __name__=='__main__': unittest.main()
