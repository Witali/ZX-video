import unittest

import numpy as np
from benchmark_cache_columns import Harness,copy_tstates
from frame_output_pipeline import Harness as Pipeline,frames,serialized_masks
from probe_sparse_motion_cache import coverage
from raw_attribute_stream import pack
from test_frame_output_pipeline import fixture,FrameOutputPipelineTests


class CacheColumnTests(unittest.TestCase):
    def test_each_group_and_pair_pattern(self):
        source=bytes((i*71+29)&255 for i in range(3072))
        for columns,unrolled in ((32,False),(16,False),(32,True)):
            h=Harness(columns,unrolled); width=32//columns
            h.run(np.zeros((24,width),dtype=np.uint8),source)
            h.run(np.ones((24,width),dtype=np.uint8),source)
            for group in range(24):
                for mask in range(1,1<<width):
                    flags=np.zeros((24,width),dtype=np.uint8)
                    flags[group]=[(mask>>(width-part-1))&1 for part in range(width)]
                    h.run(flags,source)

    def test_reconstruction_screens_and_total_delta(self):
        states,stream,_=fixture(4); stream,_=pack(stream,states,[True,False,False,True])
        tables,mapping,packets=frames(stream); masks=serialized_masks(stream)
        options=dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,selective_cache=True)
        old=Pipeline(tables,mapping,**options)
        machines=[(16,False,Pipeline(tables,mapping,cache_columns=16,**options)),
                  (32,True,Pipeline(tables,mapping,unrolled_cache=True,**options))]
        for i,((group,mask),state) in enumerate(zip(packets,states)):
            fine=coverage(group[3],8).reshape(24,4,4).any(axis=1); whole=fine.any(axis=1)
            before=old.run(group,mask,state.tobytes(),i,encoded_metadata=masks[i],cache_map=np.packbits(whole).tobytes())
            for columns,unrolled,h in machines:
                flags=fine.reshape(24,32//columns,columns//8).any(axis=2)
                after=h.run(group,mask,state.tobytes(),i,encoded_metadata=masks[i],cache_map=np.packbits(flags).tobytes())
                delta=copy_tstates(flags,columns,unrolled)-copy_tstates(whole) if group[1]&128 else 0
                self.assertEqual(after['total_tstates']-before['total_tstates'],delta)

    def test_irq_at_every_boundary_halves(self):
        FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,cache_columns=16)

    def test_irq_at_every_boundary_unrolled(self):
        FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,unrolled_cache=True)


if __name__=='__main__': unittest.main()
