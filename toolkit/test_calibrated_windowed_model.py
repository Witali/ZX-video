"""Check stage attribution, absolute deadlines and compatibility of controls."""
import unittest

from calibrated_windowed_model import CalibratedModel, frame_costs
from test_windowed_zx0_planner import fixture
from windowed_zx0_planner import Model, PERIOD


class CalibratedWindowTests(unittest.TestCase):
    def test_disabled_corrections_reproduce_original_scheduler(self):
        frames, blocks = fixture()
        names = ['min0']*len(blocks)
        old = Model(frames, blocks)
        new_frames = [dict(f, metadata_tstates=0, draw_entry_tstates=0, prepare_entry_tstates=0) for f in frames]
        new = CalibratedModel(new_frames, blocks)
        old.run(names)
        new.run(names)
        self.assertEqual(old.publications, new.publications)
        self.assertEqual(old.reserves, new.reserves)
        self.assertEqual((old.now, old.consumer, old.produced), (new.now, new.consumer, new.produced))

    def test_read_pays_metadata_before_returning_to_background(self):
        frames, blocks = fixture(12)
        costs = [dict(f, metadata_tstates=12345, draw_entry_tstates=0, prepare_entry_tstates=0) for f in frames]
        model = CalibratedModel(costs, blocks)
        model.phase, model.read_frame, model.read_after = 'read', 3, 'idle'
        model.run(['min0']*len(blocks), until_frame=2)
        self.assertEqual(model.now, frames[3]['copy_tstates']+12345)
        self.assertEqual(model.consumer, frames[3]['packet_end'])
        self.assertTrue(model.pending)

    def test_metadata_is_relocated_without_double_counting(self):
        reference = [dict(raw_position=0, packet_bytes=600, stages={
            'draw': dict(elapsed=110, disk_service=10),
            'metadata': dict(elapsed=25, disk_service=5),
            'prepare': dict(elapsed=80, disk_service=10)})]
        calibration = dict(copy=dict(tstates_per_byte=21, fixed_tstates=3000),
            draw_entry_tstates=5600, prepare_entry_tstates=3900)
        new = frame_costs(reference, calibration)[0]
        old = frame_costs(reference, calibration, move_metadata=False)[0]
        self.assertEqual((new['metadata_tstates'], new['prepare_tstates']), (20, 70))
        self.assertEqual(old['metadata_tstates']+old['prepare_tstates'], 90)
        self.assertEqual(new['copy_tstates'], 15600)
        self.assertEqual(new['draw_tstates'], 100)

    def test_cloned_window_keeps_work_and_recovers_absolute_origin(self):
        frames, blocks = fixture(16)
        costs = [dict(f, metadata_tstates=500, draw_entry_tstates=10, prepare_entry_tstates=10) for f in frames]
        costs[2]['draw_tstates'] = 2*PERIOD
        model = CalibratedModel(costs, blocks, disk_tstates_per_byte=0)
        names = ['min4']*len(blocks)
        model.run(names, until_frame=4)
        clone = model.clone()
        self.assertEqual((clone.now, clone.consumer, clone.produced), (model.now, model.consumer, model.produced))
        clone.run(names)
        self.assertGreater(clone.publications[2], 2*PERIOD)
        self.assertEqual(clone.publications[-1], 15*PERIOD)
        self.assertEqual(len(model.publications), 4)


if __name__ == '__main__':
    unittest.main()
