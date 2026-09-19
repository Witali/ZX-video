import unittest

from bulk_frame_stream import pack
from test_frame_stream_z80 import source,ring
from frame_stream_harness import Harness
from frame_output_pipeline import frames
from cell_screen_z80 import expected_tstates
from build_long_video_trd import expand_compact_screen
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


class BlackBorderTests(unittest.TestCase):
    def test_keep_active_pixels_and_clear_borders_on_both_screens(self):
        states,cells,fap1,ticks = source(4,constant_attribute_borders=True)
        self.assertTrue(any(states[:,256:384].ravel()))
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,packets = frames(cells)
        r = Reader(raw); read_header(r,magic=b'FAP3')
        old = Harness(ring(raw,509,True),tables,mapping,len(states),bulk=True,stored_guards=False,
            zero_copy=True,skip_noop_runs=True,constant_attribute_borders=True)
        new = Harness(ring(raw,509,True),tables,mapping,len(states),bulk=True,stored_guards=False,
            zero_copy=True,skip_noop_runs=True,constant_attribute_borders=True,skip_black_borders=True)
        self.assertEqual(old.frame.init_result,new.frame.init_result)
        self.assertEqual(len(old.frame.draw_code),len(new.frame.draw_code))
        for h in (old,new): h.consume_header(raw[:r.pos])
        for i,state in enumerate(states):
            before,after = old.prepare(),new.prepare()
            mask = packets[i][1]
            delta = (expected_tstates(mask,fast_mask_dispatch=True,skip_black_borders=True)
                -expected_tstates(mask,fast_mask_dispatch=True))
            self.assertEqual(after['tstates']-before['tstates'],delta)
            self.assertEqual(after['stages']['output']-before['stages']['output'],delta)
            for h in (old,new): h.publish(); h.drain_six(ticks[i*6:i*6+6])
            wanted = bytearray(b''.join(expand_compact_screen(state.tobytes())))
            # Independent native-screen row addressing; leave every active
            # byte and all attributes exactly as the original renderer.
            for y in (*range(24),*range(168,192)):
                address = ((y&192)<<5)|((y&7)<<8)|((y&56)<<2)
                wanted[address:address+32] = bytes(32)
            new.expected_screens[7 if i%2 == 0 else 5] = bytes(wanted)
            for bank in (5,7):
                self.assertEqual(bytes(new.cpu.banks[bank][:6912]),new.expected_screens[bank])
            self.assertEqual(new.cpu.banks[5][0x2400:0x3300],old.cpu.banks[5][0x2400:0x3300])
            self.assertEqual(new.cpu.ay,old.cpu.ay)

    def test_requires_initialized_attributes(self):
        import cell_screen_z80
        with self.assertRaises(ValueError): cell_screen_z80.build(skip_black_borders=True)
        with self.assertRaises(ValueError): cell_screen_z80.build(fast_mask_dispatch=True,skip_black_borders=True)


if __name__ == '__main__': unittest.main()
