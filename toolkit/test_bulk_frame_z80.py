import struct
import unittest

from bulk_frame_stream import pack
from test_frame_stream_z80 import source,ring
from frame_stream_harness import Harness
from frame_output_pipeline import frames
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from build_long_video_trd import expand_compact_screen
from benchmark_context_huffman import word


class BulkFrameZ80Tests(unittest.TestCase):
    def test_shared_cpu_bulk_packet_and_values_in_place(self):
        states,cells,fap1,ticks = source(4)
        raw,rows = pack(fap1)
        tables,mapping,groups = frames(cells)
        r = Reader(raw); read_header(r,magic=b'FAP2')
        for compressed in (False,True):
            h = Harness(ring(raw,509,compressed),tables,mapping,len(states),bulk=True,ring_start=0xffff)
            h.consume_header(raw[:r.pos])
            for i,state in enumerate(states):
                h.prepare(); h.publish(); h.drain_six(ticks[i*6:i*6+6])
                self.assertEqual(bytes(h.cpu.read8(0x6400+j) for j in range(3840)),state.tobytes())
                self.assertEqual(word(h.cpu,h.frame.w['coded_pointer']),0xa6a0+rows[i]['coded_offset'])
                self.assertEqual(word(h.cpu,h.frame.w['literal_pointer']),0xa6a0+rows[i]['literal_offset'])
                target = 7 if i % 2 == 0 else 5
                h.expected_screens[target] = b''.join(expand_compact_screen(state.tobytes()))
                for bank,wanted in h.expected_screens.items(): self.assertEqual(bytes(h.cpu.banks[bank][:6912]),wanted)
            self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))

    def test_zero_copy_metadata_matches_exact_cycle_delta(self):
        states,cells,fap1,ticks = source(3); raw,rows = pack(fap1)
        tables,mapping,_ = frames(cells); r = Reader(raw); read_header(r,magic=b'FAP2')
        old = Harness(ring(raw,509,True),tables,mapping,len(states),bulk=True)
        new = Harness(ring(raw,509,True),tables,mapping,len(states),bulk=True,zero_copy=True)
        for h in (old,new): h.consume_header(raw[:r.pos])
        for i,state in enumerate(states):
            before,after = old.prepare(),new.prepare()
            self.assertEqual(after['tstates']-before['tstates'],-4481)
            for h in (old,new): h.publish(); h.drain_six(ticks[i*6:i*6+6])
            for bank in (5,7): self.assertEqual(old.cpu.banks[bank][:6912],new.cpu.banks[bank][:6912])
            self.assertEqual(bytes(new.cpu.read8(0x6400+j) for j in range(3840)),state.tobytes())
            self.assertEqual(word(new.cpu,new.frame.w['native_pointer']),0xa6a0+rows[i]['coded_offset']-80)

    def test_bad_length_header_and_guard_rejected(self):
        _,cells,fap1,_ = source(1); raw,rows = pack(fap1)
        tables,mapping,_ = frames(cells); first = rows[0]
        bads = []
        for value in (0,295,4705,65535):
            bad = bytearray(raw); struct.pack_into('<H',bad,first['offset'],value); bads.append(bad)
        body = first['offset']+2
        for offset in (first['coded_offset']+first['coded_bytes'],first['payload_bytes']-1):
            bad = bytearray(raw); bad[body+offset] = 1; bads.append(bad)
        for offset,value in ((first['ay_bytes'],b'\x08'),(first['ay_bytes']+1,b'\x07\0'),
                (first['ay_bytes']+1,b'\x25\x02'),(first['ay_bytes']+3,b'\xff\xff')):
            bad = bytearray(raw); bad[body+offset:body+offset+len(value)] = value; bads.append(bad)
        for bad in bads:
            h = Harness(ring(bad),tables,mapping,1,bulk=True)
            h.consume_header(bad[:first['offset']])
            with self.assertRaises((AssertionError,RuntimeError)): h.prepare()
            self.assertFalse(any(h.cpu.banks[5][:6912])); self.assertFalse(any(h.cpu.banks[7][:6912]))


if __name__ == '__main__': unittest.main()
