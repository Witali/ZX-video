import unittest

from frame_output_pipeline import Harness
from causal_tile_z80 import noop_run_delta_tstates


class NoopRunTests(unittest.TestCase):
    def test_ay_irq_at_scanner_instruction_boundaries(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        mixed = FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,noops=True)
        empty = FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,noops=True,empty_noops=True)
        self.assertGreater(empty,mixed)

    def test_motion_intra_fragments_and_cache_preserved(self):
        import numpy as np
        from test_frame_output_pipeline import fixture
        from raw_attribute_stream import pack
        from frame_output_pipeline import frames,serialized_masks
        from probe_sparse_motion_cache import coverage
        states,data,_ = fixture(5)
        data,_ = pack(data,states,[True,False,False,True,False])
        tables,mapping,packets = frames(data); metadata = serialized_masks(data)
        old = Harness(tables,mapping,raw_attributes=True,decode_metadata=True,
            fast_mask_dispatch=True,selective_cache=True)
        new = Harness(tables,mapping,raw_attributes=True,decode_metadata=True,
            fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True)
        for i,((group,native),state) in enumerate(zip(packets,states)):
            cache = np.packbits(coverage(group[3],32).reshape(24,4).any(axis=1)).tobytes()
            before = old.run(group,native,state.tobytes(),i,encoded_metadata=metadata[i],cache_map=cache)
            after = new.run(group,native,state.tobytes(),i,encoded_metadata=metadata[i],cache_map=cache)
            self.assertEqual(after['total_tstates']-before['total_tstates'],noop_run_delta_tstates(group[3],group[4]))

    def test_all_run_lengths_stripe_edges_and_exit_kinds(self):
        for length in range(1,17):
            for following in ('patch','clear'):
                vectors, masks = bytearray(192),bytearray(384)
                encoded = bytearray(); expected = bytearray(3840)
                # Nonempty first/last tiles exercise entry and stripe exits;
                # a run of the selected length starts at the third stripe.
                # The cropped first/last stripes must remain black.
                selected = {16,31,175}
                if length < 16: selected.add(32+length)
                for tile in sorted(selected):
                    if following == 'clear': vectors[tile] = 81
                    else:
                        masks[tile*2] = 128; encoded.append(1)
                        row,column = divmod(tile,16); expected[row*256+column*2] = 1
                group = (1,0,len(encoded)*8,bytes(vectors),bytes(masks),bytes(96),bytes(encoded),b'')
                old = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                    fast_mask_dispatch=True,selective_cache=True)
                new = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                    fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True)
                before = old.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
                after = new.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
                self.assertEqual(after['total_tstates']-before['total_tstates'],noop_run_delta_tstates(vectors,masks))


if __name__ == '__main__': unittest.main()
