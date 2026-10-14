"""Full-disk dictionary/worker bounds without relaxing the legacy budget."""
from pathlib import Path
import tempfile
import unittest

from build_stream_trd import build
from direct_player import layout
from general import models
from verify_stream_trd import cold_load


class WorkerBudget(unittest.TestCase):
    def test_maximum_one_disk_stays_inside_fixed_code_bank(self):
        root=Path(__file__).resolve().parents[3]/'.tmp';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='worker-budget-') as temporary:
            model=dict(models())['duration_zero_half_recent']
            packed=bytes(2392*256)
            disk,meta=build(packed,Path(temporary),bytes(6912),model)
            self.assertEqual(meta['memory']['worker_origin'],0xba00)
            self.assertLessEqual(meta['player_labels']['stream_worker_end'],0xbfff)
            self.assertEqual(len(disk),655360)
            self.assertEqual(meta['memory']['base_audio_bytes'],91392)
            m,loaded=cold_load(disk,meta,'pentagon1024')
            self.assertEqual(loaded['remaining_sectors'],0)
            self.assertFalse(m.locked)
            self.assertEqual(sum(s['bytes'] for s in loaded['loaded_sections']),len(packed))

    def test_legacy_layout_does_not_infer_a_larger_budget(self):
        model=dict(dict(models())['duration_zero_half_recent'],extended_ram=True)
        with self.assertRaises(AssertionError):layout(bytes(256),model)
        # The continuous builder alone explicitly grants the proved budget.
        data=layout(bytes(256),model,resident_limit=14848)
        self.assertEqual(len(data[2]),18)
        with self.assertRaises(ValueError):layout(bytes(256),resident_limit=14848)


if __name__=='__main__':unittest.main()
