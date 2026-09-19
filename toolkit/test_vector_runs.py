import unittest

from vector_run_stream import encode_vectors,decode_vectors,transcode
from bulk_frame_stream import pack
from causal_tile_z80 import encoded_run_delta_tstates,noop_run_delta_tstates
from frame_output_pipeline import Harness as Pipeline,frames,display_screen
from frame_stream_harness import Harness
from test_frame_stream_z80 import source,ring
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from benchmark_context_huffman import word


class VectorRunTests(unittest.TestCase):
    def test_stream_roundtrip_and_invalid_runs(self):
        _,_,fap1,_ = source(3)
        old,_ = pack(fap1,stored_guards=False)
        for inplace in (False,True):
            for minimum in (1,4,16):
                new,_ = transcode(old,inplace=inplace,minimum=minimum)
                self.assertEqual(transcode(new,inverse=True)[0],old)
                for bad in (new[:-1],new+b'!',b'FAIL'+new[4:]):
                    with self.assertRaises(ValueError): transcode(bad,inverse=True)
        for first in (89,128,145,255):
            with self.assertRaises(ValueError): decode_vectors(bytes([first])+bytes(191),bytes(384))
        commands = bytes([88,144])+bytes(190)
        with self.assertRaises(ValueError): decode_vectors(commands,bytes(384))
        commands,_ = encode_vectors(bytes(192),bytes(384),inplace=True)
        with self.assertRaises(ValueError): decode_vectors(commands,b'\x80'+bytes(383),inplace=True)
        bad = bytearray(commands); bad[1] = 1
        with self.assertRaises(ValueError): decode_vectors(bytes(bad),bytes(384),inplace=True)

    def test_all_run_lengths_and_following_patch(self):
        for length in range(1,17):
            vectors,masks = bytearray(192),bytearray(384)
            expected,encoded = bytearray(3840),bytearray()
            tiles = {16,31,175}
            if length < 16: tiles.add(32+length)
            for tile in sorted(tiles):
                masks[tile*2] = 128; encoded.append(1)
                row,column = divmod(tile,16); expected[row*256+column*2] = 1
            group = (1,0,len(encoded)*8,bytes(vectors),bytes(masks),bytes(96),bytes(encoded),b'')
            baseline = Pipeline([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                fast_mask_dispatch=True,selective_cache=True)
            before = baseline.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
            for mode in (True,'inplace'):
                h = Pipeline([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                    fast_mask_dispatch=True,selective_cache=True,encoded_noop_runs=mode)
                after = h.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))
                self.assertEqual(after['total_tstates']-before['total_tstates'],
                    encoded_run_delta_tstates(vectors,masks,inplace=mode == 'inplace'))

    def test_integrated_zx0_motion_intra_fragments_and_ay(self):
        states,cells,fap1,ticks = source(4,constant_attribute_borders=True)
        old,_ = pack(fap1,stored_guards=False)
        tables,mapping,packets = frames(cells)
        r = Reader(old); read_header(r,magic=b'FAP3')
        options = dict(bulk=True,stored_guards=False,zero_copy=True,constant_attribute_borders=True,
            skip_black_borders=True,progress_frames=4)
        baseline = Harness(ring(old,509,True),tables,mapping,4,skip_noop_runs=True,**options)
        baseline.consume_header(old[:r.pos]); reference=[]
        for i in range(4):
            row = baseline.prepare(); baseline.publish(); baseline.drain_six(ticks[i*6:i*6+6])
            reference.append((row,bytes(baseline.cpu.ay),{b:bytes(baseline.cpu.banks[b][:6912]) for b in (5,7)}))
        for mode,minimum,scan in ((True,1,False),('inplace',1,False),('inplace',4,False),
                ('inplace',16,False),('inplace',16,True)):
            raw,_ = transcode(old,inplace=mode == 'inplace',minimum=minimum)
            h = Harness(ring(raw,509,True),tables,mapping,4,encoded_noop_runs=mode,skip_noop_runs=scan,**options)
            h.consume_header(raw[:r.pos])
            for i,(group,_) in enumerate(packets):
                after = h.prepare(); before,ay,screens = reference[i]
                commands,used = encode_vectors(group[3],group[4],inplace=mode == 'inplace',minimum=minimum)
                delta = (encoded_run_delta_tstates(group[3],group[4],commands=commands,inplace=mode == 'inplace',scan_uncoded=scan)
                    -noop_run_delta_tstates(group[3],group[4]))
                self.assertEqual(after['stages']['reconstruct']-before['stages']['reconstruct'],delta)
                self.assertEqual(after['tstates']-before['tstates'],delta)
                self.assertEqual(word(h.cpu,h.frame.recon['vectors']),word(h.cpu,h.frame.w['vector_pointer'])+used)
                h.publish(); h.drain_six(ticks[i*6:i*6+6])
                self.assertEqual(bytes(h.cpu.ay),ay)
                self.assertEqual(bytes(h.cpu.banks[5][0x2400:0x3300]),states[i].tobytes())
                for bank in (5,7): self.assertEqual(bytes(h.cpu.banks[bank][:6912]),screens[bank])

    def test_irq_inside_encoded_run_handler(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        for mode,scan in ((True,False),('inplace',False),('inplace',True)):
            FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,selective=True,encoded=mode,
                noops=scan,empty_noops=True)


if __name__ == '__main__': unittest.main()
