import unittest

from causal_tile_z80 import static_stripe_delta_tstates,validate_static_stripes
from frame_output_pipeline import Harness


class StaticStripeTests(unittest.TestCase):
    def test_idle_and_fill_escapes_preserve_values_cache_and_cycles(self):
        for cache in (False,True):
            for edges in ((),(0,),(176,),(0,176)):
                vectors,masks = bytearray(192),bytearray(384)
                for first in edges: vectors[first:first+16] = bytes([88])*16
                masks[32] = 128
                expected = bytearray(3840); expected[256] = 1
                group = (1,128*cache,8,bytes(vectors),bytes(masks),bytes(96),b'\1',bytes(16*len(edges)))
                options = dict(raw_attributes=True,fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True)
                old = Harness([bytes([8]*256)]*2,bytes(256),**options)
                new = Harness([bytes([8]*256)]*2,bytes(256),skip_static_stripes=True,**options)
                before = old.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
                after = new.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
                delta = static_stripe_delta_tstates(vectors,masks)
                self.assertEqual(after['total_tstates']-before['total_tstates'],delta)
                self.assertEqual(after['stages']['reconstruct']-before['stages']['reconstruct'],delta)
                for bank in (5,7): self.assertEqual(old.cpu.banks[bank][:6912],new.cpu.banks[bank][:6912])
                self.assertEqual(old.cpu.banks[5][0x3400:0x3800],new.cpu.banks[5][0x3400:0x3800])
                if not edges: self.assertEqual(delta,-2516)
                if len(edges) == 2: self.assertEqual(delta,588)

    def test_reject_unproven_zero_edge_marker(self):
        for first in (0,176):
            vectors,masks = bytearray(192),bytearray(384)
            vectors[first+15] = 88
            with self.assertRaises(ValueError): validate_static_stripes(vectors,masks)
            vectors[first+15] = 0; masks[first*2+31] = 1
            with self.assertRaises(ValueError): validate_static_stripes(vectors,masks)
            vectors[first] = 88
            validate_static_stripes(vectors,masks)  # First nonzero vector uses the full path.

    def test_real_ay_irq_at_static_handler_and_dispatch(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,noops=True,
            static=True,empty_noops=True)


if __name__ == '__main__': unittest.main()
