"""Exact eviction/reuse and malformed control records for the mutable row cache."""
import struct
import unittest

import numpy as np

import dynamic_row_dictionary as dynamic
from test_generic_cell_codebook import frame


def fixture():
    rng=np.random.default_rng(4216)
    result=[]
    for index in range(12):
        words=(np.arange(160,dtype=np.uint16)+index*47)%625
        result.append(frame(rng.choice(words,2304),71 if index%3 else 7))
    return np.stack(result)


class DynamicRowsTests(unittest.TestCase):
    def test_eviction_reuse_preserves_both_physical_screens(self):
        frames=fixture()
        result=dynamic.encode(frames,0,len(frames))
        self.assertGreater(result['unique_literal_rows'],256)
        self.assertGreater(result['row_updates'],0)
        checked=dynamic.decode_check(result['raw'],frames,0,len(frames),result['rows'])
        self.assertEqual(checked['row_updates'],result['row_updates'])
        self.assertTrue(checked['both_screens_exact'])
        self.assertEqual(result['rows']['ram_bytes'],512)

    def test_independent_volume_uses_real_two_screen_history(self):
        frames=fixture()
        result=dynamic.encode(frames,3,11)
        checked=dynamic.decode_check(result['raw'],frames,3,11,result['rows'])
        self.assertEqual(checked['frames'],8)

    def test_still_image_and_all_five_levels(self):
        frames=np.stack([frame([0,156,312,468,624],71)]*3)
        result=dynamic.encode(frames,0,3)
        checked=dynamic.decode_check(result['raw'],frames,0,3,result['rows'])
        self.assertEqual(result['row_updates'],0)
        self.assertEqual(result['details'][2]['changed_cells'],0)
        self.assertTrue(checked['both_screens_exact'])

    def test_bad_replacement_count_is_rejected(self):
        frames=np.stack([frame([0])])
        result=dynamic.encode(frames,0,1)
        for count in (0,257,32767):
            raw=result['raw'][:2056]+struct.pack('<H',0x8000|count)+result['raw'][2056:]
            with self.assertRaisesRegex(ValueError,'update count'):
                dynamic.decode_check(raw,frames,0,1,result['rows'])


if __name__=='__main__':unittest.main()
