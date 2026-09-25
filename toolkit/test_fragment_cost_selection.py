import unittest
from bulk_frame_stream import pack
from probe_fragment_cost_selection import Selector
from reencode_bounded_fragments import encode,validate
from test_frame_stream_z80 import source


class FragmentSelectionTests(unittest.TestCase):
    def test_selector_preserves_all_pixels_and_ay(self):
        states,_,fap1,_=source(4)
        raw,_=pack(fap1,stored_guards=False)
        original_ay=validate(raw,states)
        control,_=encode(raw,states)
        self.assertEqual(validate(control,states),original_ay)
        unchanged,_=encode(raw,states,fragment_selector=lambda *args:False)
        self.assertEqual(unchanged,control)
        selector=Selector(1,3,128,400)
        changed,detail=encode(raw,states,fragment_selector=selector)
        self.assertGreater(len(selector.rows),0)
        self.assertTrue(all(1<=r['frame']<3 for r in selector.rows))
        self.assertEqual(validate(changed,states),original_ay)
        self.assertEqual(sum(r['selected_fragments'] for r in detail['packets']),len(selector.rows))


if __name__=='__main__':unittest.main()
