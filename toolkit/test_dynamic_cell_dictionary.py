"""Dynamic cell replacements preserve both histories and old CB42 bytes."""
import gzip
from pathlib import Path
import unittest

import numpy as np

import dynamic_row_dictionary as dynamic
from test_dynamic_row_dictionary import fixture
from test_generic_cell_codebook import frame


def scenes():
    rng=np.random.default_rng(256);frames=[]
    for scene in range(4):
        pool=rng.choice(np.arange(120,dtype=np.uint16)+scene*120,(80,4))
        cells=pool[np.arange(576)%80]
        words=cells.reshape(18,32,4).transpose(0,2,1).reshape(72,32)
        frames.extend([frame(words.ravel(),71 if scene%2 else 7)]*4)
    return np.stack(frames)


class DynamicCellTests(unittest.TestCase):
    def test_row_only_stream_remains_byte_identical(self):
        old=Path(__file__).with_name('dynamic_rows_evidence')/'fixture-work-ZX-video-dynamic_part01-codebook.raw.gz'
        frames=fixture();current=dynamic.representation(frames,0,len(frames))
        self.assertEqual(current['raw'],gzip.decompress(old.read_bytes()))

    def test_replacements_and_real_two_screen_histories(self):
        frames=scenes()
        for start in (0,3):
            result=dynamic.representation(frames,start,len(frames),cell_window=4)
            self.assertEqual(result['raw'][:4],b'CB43')
            self.assertGreater(result['cell_updates'],0)
            self.assertEqual(result['cell_updates'],result['dynamic_proof']['cell_updates'])
            self.assertTrue(result['dynamic_proof']['both_screens_exact'])

    def test_fixed_scene_needs_no_replacements(self):
        frames=np.stack([frame([0,156,312,468,624])]*8)
        result=dynamic.representation(frames,0,8,cell_window=2)
        self.assertEqual(result['cell_updates'],0)
        self.assertEqual(result['row_updates'],0)


if __name__=='__main__':unittest.main()
