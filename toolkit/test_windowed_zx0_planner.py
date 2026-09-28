"""Check bounded lookahead, carried capacity and absolute schedule recovery."""
import unittest

from windowed_zx0_planner import FIELD, PERIOD, Model, select


def fixture(count=64):
    frames = [dict(packet_end=(i+1)*512, draw_tstates=50000,
        prepare_tstates=100000, copy_tstates=9000) for i in range(count)]
    blocks = []
    for at in range(0, count*512, 2048):
        size = min(2048, count*512-at); calls = (size+255)//256
        variants = {}
        for name, packed, ticks in (('min0', 300, 90000), ('min4', 600, 5000)):
            variants[name] = dict(bytes=packed, executed=True, all_offsets_fit=True,
                decoder_tstates=ticks*calls, slice_tstates=[ticks]*calls)
        blocks.append(dict(decoded_bytes=size, variants=variants))
    return frames, blocks


class WindowedPlannerTests(unittest.TestCase):
    def test_capacity_horizon_and_full_coverage(self):
        frames, blocks = fixture()
        capacity = len(blocks)*300+900
        result = select(frames, blocks, capacity, window_frames=8)
        self.assertLessEqual(result['stream_bytes'], capacity)
        self.assertEqual(result['names'][:3], ['min0']*3)
        self.assertEqual(len(result['estimated_publications']), len(frames))
        self.assertLessEqual(result['maximum_evaluated_horizon_frames'], 8)
        self.assertTrue(all(d['end_frame_exclusive']-d['first_frame'] <= 8 for d in result['decisions']))
        self.assertTrue(all(d['remaining_bytes'] >= 0 for d in result['decisions']))
        self.assertEqual([d['block'] for d in result['decisions']], list(range(3, len(blocks))))
        self.assertEqual(result['alternative_trds_built'], 0)
        self.assertEqual(result['alternative_fuse_runs'], 0)
        self.assertFalse(result['actual_publication_verified'])

    def test_window_clones_keep_partial_input_and_do_not_refill(self):
        frames, blocks = fixture(); names = ['min0']*len(blocks)
        model = Model(frames, blocks)
        index = model.run(names, stop_new=True)
        self.assertEqual(index, 3)
        model.accept(index, names[index]); model.produce(names, stop_new=False)
        clone = model.clone()
        self.assertEqual((clone.now, clone.consumer, clone.produced, clone.step_index),
                         (model.now, model.consumer, model.produced, model.step_index))
        clone.run(names, until_frame=clone.frame+8)
        self.assertGreater(clone.now, model.now)
        self.assertLess(len(model.publications), len(clone.publications))

    def test_late_frame_recovers_original_deadlines(self):
        frames, blocks = fixture(12)
        frames[2]['draw_tstates'] = 2*PERIOD
        model = Model(frames, blocks, disk_tstates_per_byte=0)
        model.run(['min4']*len(blocks))
        self.assertGreater(model.publications[2], 2*PERIOD)
        self.assertEqual(model.publications[-1], (len(frames)-1)*PERIOD)
        self.assertTrue(all(t % FIELD == 0 for t in model.publications))

    def test_single_frame_and_impossible_budget(self):
        frames, blocks = fixture(1)
        result = select(frames, blocks, 300, window_frames=2)
        self.assertEqual(result['estimated_publications'], [0])
        self.assertEqual(result['decisions'], [])
        with self.assertRaisesRegex(ValueError, 'no choices fit'):
            select(*fixture(), 1)


if __name__ == '__main__': unittest.main()
