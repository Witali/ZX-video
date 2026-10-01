"""Explicit measured cuts must retain all source frames and enforce RAM limits."""
import unittest
from unittest.mock import patch

import numpy as np

from convert_cb41 import plan_volumes


class ExplicitCutsTests(unittest.TestCase):
    def setUp(self):
        self.frames = np.zeros((20,4608),dtype=np.uint8)
        self.frames[:,3840:] = 1

    def test_exact_coverage_and_audio_ranges_at_10_fps(self):
        with patch('convert_cb41.audio_size',return_value=(b'AYH1',dict(resident_fits=True))) as size:
            parts, report = plan_volumes(self.frames, [], {}, None, None, 4096, 5, volume_cuts=[7,20])
        self.assertEqual([(p['start'],p['end']) for p in parts],[(0,7),(7,20)])
        self.assertEqual(report['boundaries'],[0,7,20])
        self.assertFalse(report['final_disk_capacity_verified'])
        self.assertEqual([c.kwargs['frame_fields'] for c in size.call_args_list],[5,5])
        self.assertEqual([c.args[1:3] for c in size.call_args_list],[(0,7),(7,20)])

    def test_invalid_cuts_cannot_truncate_duplicate_or_reorder(self):
        for cuts in ([],[19],[21],[7,7,20],[10,5,20],[0,20],[-1,20]):
            with self.assertRaises(ValueError):
                plan_volumes(self.frames,[],{},None,None,4096,5,volume_cuts=cuts)
        with self.assertRaises(ValueError):
            plan_volumes(self.frames,[],{},None,None,10,5,volume_cuts=[20])
        with self.assertRaises(ValueError):
            plan_volumes(self.frames,[],{},None,None,4096,5,3,volume_cuts=[20])

    def test_audio_overflow_is_explicit_without_hidden_recuts(self):
        with patch('convert_cb41.audio_size',return_value=(b'',dict(resident_fits=False))):
            with self.assertRaisesRegex(ValueError,'audio bank'):
                plan_volumes(self.frames,[],{},None,None,4096,5,volume_cuts=[20])


if __name__ == '__main__': unittest.main()
