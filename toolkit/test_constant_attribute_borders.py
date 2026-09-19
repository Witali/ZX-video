import unittest

from bulk_frame_stream import pack
from test_frame_stream_z80 import source,ring
from frame_stream_harness import Harness
from frame_output_pipeline import frames,INITIALIZER
from cell_screen_z80 import expected_tstates
from build_long_video_trd import expand_compact_screen
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


class ConstantAttributeBorderTests(unittest.TestCase):
    def test_irq_at_every_attribute_copy_instruction(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        calls = FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,constant=True)
        self.assertGreater(calls,1200)

    def test_actual_initialization_and_both_screen_banks(self):
        states,cells,fap1,ticks = source(4,constant_attribute_borders=True)
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,packets = frames(cells)
        r = Reader(raw); read_header(r,magic=b'FAP3')
        for compressed in (False,True):
            old = Harness(ring(raw,509,compressed),tables,mapping,len(states),bulk=True,
                stored_guards=False,zero_copy=True,skip_noop_runs=True,ring_start=0xffff)
            new = Harness(ring(raw,509,compressed),tables,mapping,len(states),bulk=True,
                stored_guards=False,zero_copy=True,skip_noop_runs=True,ring_start=0xffff,
                constant_attribute_borders=True)
            self.assertLessEqual(INITIALIZER+len(new.frame.init_code),0x7b70)
            self.assertEqual(new.frame.init_result['total_tstates']-old.frame.init_result['total_tstates'],32284)
            self.assertEqual(new.frame.init_result['total_tstates'],430251)
            self.assertEqual(len(new.frame.draw_code),len(old.frame.draw_code))
            for bank in (5,7):
                self.assertEqual(bytes(new.cpu.banks[bank][:6912]),bytes(6144)+b'\1'*768)
            for h in (old,new): h.consume_header(raw[:r.pos])
            for i,state in enumerate(states):
                before,after = old.prepare(),new.prepare()
                self.assertEqual(after['tstates']-before['tstates'],-3240)
                self.assertEqual(after['stages']['output']-before['stages']['output'],-3240)
                mask = packets[i][1]
                self.assertEqual(after['stages']['output'],expected_tstates(mask,
                    fast_mask_dispatch=True,constant_attribute_borders=True))
                for h in (old,new): h.publish(); h.drain_six(ticks[i*6:i*6+6])
                target = 7 if i%2 == 0 else 5
                new.expected_screens[target] = b''.join(expand_compact_screen(state.tobytes()))
                for bank in (5,7):
                    self.assertEqual(bytes(new.cpu.banks[bank][:6912]),new.expected_screens[bank])
                self.assertEqual(bytes(new.cpu.banks[target][:6912]),bytes(old.cpu.banks[target][:6912]))
                self.assertEqual(new.cpu.banks[5][0x2400:0x3300],old.cpu.banks[5][0x2400:0x3300])
                self.assertEqual(new.cpu.ay,old.cpu.ay)


if __name__ == '__main__': unittest.main()
