"""Dictionary/reference integration edge cases independent of movie content."""
import unittest
import numpy as np
import five_level_dither as five
import build_long_video_trd as video
from frame_output_pipeline import display_screen as legacy
from row_dictionary_video import encode_states,display_screen,reference_tables


def frame(words):
    words=np.resize(np.array(words,dtype=np.uint16),(96,32))
    levels=((words[...,None]//np.array([125,25,5,1]))%5).astype(np.uint8).reshape(96,128)
    levels[:12]=0;levels[84:]=0
    return five.pack_levels(levels)+bytes([71])*768


class DictionaryTests(unittest.TestCase):
    def test_all_five_shades_and_restored_legacy_globals(self):
        source=[frame([0,1,2,3,4,624,156]),frame([4,3,2,1,0])]
        old=(video.PLAYER_DITHER_TOP,video.PLAYER_DITHER_BOTTOM)
        states,book=encode_states(source)
        self.assertEqual(book['words'][0],0)
        for s,f in zip(states,source):
            self.assertEqual(display_screen(s.tobytes(),{'row_dictionary':book}),b''.join(five.expand(f)))
        self.assertEqual((video.PLAYER_DITHER_TOP,video.PLAYER_DITHER_BOTTOM),old)
        self.assertEqual(display_screen(bytes(3840),{}),legacy(bytes(3840),black_borders=True))

    def test_oversized_dictionary_and_corrupt_table_rejected(self):
        with self.assertRaises(ValueError): encode_states([frame(range(257))])
        _,book=encode_states([frame([0,624])]); book['sha256']='bad'
        with self.assertRaises(ValueError),reference_tables(book): pass


if __name__=='__main__': unittest.main()
