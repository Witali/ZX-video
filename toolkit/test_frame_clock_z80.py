import struct
import unittest

from frame_stream_harness import Harness
from frame_clock_harness import Clock, FIELD
from frame_output_pipeline import frames
from test_frame_stream_z80 import source, ring
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from benchmark_context_huffman import word


class FrameClockTests(unittest.TestCase):
    def test_fixed_six_field_deadlines_and_exact_scheduled_ay(self):
        self.exercise(False)

    def test_bounded_idle_lookahead_preserves_packets_and_deadlines(self):
        self.exercise(True)

    def exercise(self,lookahead):
        count = 8
        _, cells, raw, ticks = source(count)
        tables, mapping, _ = frames(cells)
        r = Reader(raw); read_header(r,magic=b'FAP1')
        header = raw[:r.pos]
        empty = struct.pack('<BHHH',0,8,0,0)+bytes(3+192+8+80)
        data = header+b''.join(b''.join(ticks[i*6:i*6+6])+empty for i in range(count))
        h = Harness(ring(data,509,True),tables,mapping,count,ring_start=0x3fff)
        h.consume_header(header); h.prepare()
        clock = Clock(h,ticks,lookahead=lookahead)
        initial = clock.start()
        self.assertGreater(initial['idle_tstates'],0)
        for i in range(1,count):
            result = clock.play_one()
            self.assertGreater(result['irq_tstates'],0)
            self.assertFalse(any(h.cpu.banks[5][:6912])); self.assertFalse(any(h.cpu.banks[7][:6912]))
        clock.drain()
        self.assertEqual(clock.ticks,len(ticks))
        self.assertEqual([r['fields'] for r in clock.publications],[1+6*i for i in range(count)])
        self.assertFalse(any(r['late_fields'] for r in clock.publications))
        self.assertEqual(word(h.cpu,h.audio['audio_ticks_played']),len(ticks))
        # IRQ register-write counts can move publication a few hundred T within
        # the field. The display bank is switched in the same field every time.
        deltas = [b['tstates']-a['tstates'] for a,b in zip(clock.publications,clock.publications[1:])]
        self.assertTrue(all(abs(t-6*FIELD)<2000 for t in deltas))


if __name__ == '__main__': unittest.main()
