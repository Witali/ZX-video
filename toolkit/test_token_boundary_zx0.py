import unittest
import json
from pathlib import Path

import banked_zx0

from benchmark_banked_zx0 import Harness
from benchmark_context_huffman import word
from stream_reader_harness import Harness as Reader
from test_stream_reader_z80 import blocks
from zx0_speed import Token,encode


class TokenBoundaryTests(unittest.TestCase):
    def test_recorded_variants_remain_byte_exact(self):
        for mode,name in ((False,'lean_frame_banked_cpu.json'),('decrement','token_boundary_banked_cpu.json'),
                (True,'token_boundary_fast_banked_cpu.json')):
            saved=json.loads(Path(__file__).with_name(name).read_text(encoding='utf-8'))
            code,_=banked_zx0.build(fast_literal=True,fast_refill=True,token_boundaries=mode)
            self.assertEqual(code,bytes.fromhex(saved['code_hex']))

    def test_each_requested_byte_long_matches_and_partial_last_blocks(self):
        for size in (1,255,256,257,8191,8192):
            for stored in (False,True):
                raw = b'a'*size
                tokens = [Token(0,1)]+([Token(1,size-1,1)] if size>1 else [])
                payload = raw if stored else encode(raw,tokens)
                h = Harness(fast_literal=True,fast_refill=True,token_boundaries=True)
                h.begin(payload,raw,stored=stored,ring_start=0xffff,page=0x1f)
                for target in range(1,size+1):
                    h.run(target)
                    self.assertGreaterEqual(h.cpu.produced,target)
                h.finish(); h.run(size)
                for bad in (payload[:-1],payload+b'!'):
                    if not bad: continue
                    with self.assertRaises((ValueError,AssertionError,RuntimeError)):
                        broken = Harness(fast_literal=True,fast_refill=True,token_boundaries=True)
                        broken.begin(bad,raw,stored=stored)
                        broken.run(size); broken.finish()

    def test_reader_mixed_blocks_boundary_headers_and_extra_bytes(self):
        first,second = b'z'*8192,bytes(range(256))*32
        items = [(first,encode(first,[Token(0,1),Token(1,8191,1)])),
            (second,encode(second,[Token(0,256),Token(256,7936,256)])),
            (second[:257],None),(b'abcdef',encode(b'abcdef',[Token(0,6)]))]*5
        stream,expected = blocks(items)
        for start in (0x3fff,0xffff):
            h = Reader(stream,ring_start=start,token_boundaries=True); position=0
            self.assertEqual(h.take(0),b'')
            for n in (1,1,255,256,257,4096,4096):
                self.assertEqual(h.take(n),expected[position:position+n]); position += n
            while position<len(expected):
                n = min(1023,len(expected)-position)
                self.assertEqual(h.take(n),expected[position:position+n]); position += n
            self.assertEqual(h.cpu.consumed,len(stream))
            self.assertEqual(h.blocks,len(items))
            self.assertEqual(word(h.cpu,h.r['block_left']),0)

    def test_real_ay_irq_after_each_decoder_instruction(self):
        from test_banked_zx0 import BankedZX0Tests
        BankedZX0Tests().exercise_irq(token_boundaries=True)

    def test_latency_bound_with_long_copies_and_window_crossings(self):
        from audit_token_boundary_latency import bound_trace
        for raw,tokens in ((b'a'*8192,[Token(0,1),Token(1,8191,1)]),
                (bytes(range(256))*32,[Token(0,256),Token(256,7936,256)]),
                (bytes(range(256))*32,[Token(0,8192)])):
            payload=encode(raw,tokens)
            h=Harness(fast_literal=True,fast_refill=True,token_boundaries=True)
            h.begin(payload,raw,ring_start=0xfff4); trace=[]
            h.run(len(raw),copy_trace=trace); h.finish()
            for quota in (1,256):
                bound=bound_trace(trace,quota)['bound_tstates']
                h.begin(payload,raw,ring_start=0xfff4)
                while h.cpu.produced<len(raw): h.run(min(h.cpu.produced+quota,len(raw)))
                for row in h.finish()['slices'][1:]: self.assertLessEqual(row['tstates']+17,bound)

    def test_integrated_fap3_video_progress_and_ay(self):
        from bulk_frame_stream import pack
        from frame_output_pipeline import frames
        from frame_stream_harness import Harness as Player
        from probe_motion_entropy import Reader as Cursor
        from probe_spatial_contexts import read_header
        from test_frame_stream_z80 import source,ring
        states,cells,fap1,ticks = source(4,constant_attribute_borders=True)
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,_ = frames(cells); cursor = Cursor(raw); read_header(cursor,magic=b'FAP3')
        options = dict(bulk=True,stored_guards=False,zero_copy=True,skip_noop_runs=True,
            constant_attribute_borders=True,skip_black_borders=True,progress_frames=4)
        old = Player(ring(raw,509,True),tables,mapping,4,**options)
        new = Player(ring(raw,509,True),tables,mapping,4,token_boundaries=True,**options)
        for h in (old,new): h.consume_header(raw[:cursor.pos])
        for i in range(4):
            results=[]
            for h in (old,new):
                results.append(h.prepare()); h.publish(); h.drain_six(ticks[i*6:i*6+6])
                self.assertEqual(bytes(h.cpu.banks[5][0x2400:0x3300]),states[i].tobytes())
            for phase in ('packet','metadata','reconstruct','output','audio','handoff'):
                self.assertEqual(results[0]['stages'][phase],results[1]['stages'][phase])
            self.assertEqual(old.cpu.ay,new.cpu.ay)
            for bank in (5,7): self.assertEqual(old.cpu.banks[bank][:6912],new.cpu.banks[bank][:6912])
        self.assertEqual(new.cpu.consumed,len(new.cpu.ring_data))


if __name__ == '__main__': unittest.main()
