"""Release cadence rejects skipped fields, missing OUT events and jitter."""
import unittest

from inspect_frame_cadence import FIELD_TSTATES as FIELD, inspect, require_smooth


def fixture():
    stamps = [1000 + i * 6 * FIELD for i in range(4)]
    meta = dict(volumes=[dict(trd_name='test.trd', frames=4, frame_start=0)])
    trace = dict(frame_timestamps=stamps, frame_interval_tstates=[6 * FIELD] * 3,
        frame_prepared_timestamps=[n + 100 for n in stamps[:-1]],
        rom_call_entry_frames=[], rom_call_kinds=[], rom_call_tstates=[],
        clock_hz=3546900, screen_flip_timestamps=[n - 58 for n in stamps[1:]])
    return meta, [trace]


class FrameCadenceTests(unittest.TestCase):
    def test_six_fields(self):
        require_smooth(inspect(*fixture()))

    def test_actual_out_events_required(self):
        meta, traces = fixture(); del traces[0]['screen_flip_timestamps']
        with self.assertRaisesRegex(ValueError, 'timestamps'):
            require_smooth(inspect(meta, traces))

    def test_field_slip_and_subfield_jitter(self):
        for delay in (FIELD, 4000):
            meta, traces = fixture(); trace = traces[0]
            trace['screen_flip_timestamps'][1] += delay
            with self.assertRaises(ValueError):
                require_smooth(inspect(meta, traces))


if __name__ == '__main__':
    unittest.main()
