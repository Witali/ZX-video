import unittest
from assess_frame_jitter import assess,FIELD


class FrameJitterTests(unittest.TestCase):
    def rows(self,fields):
        return [dict(fields=f,tstates=f*FIELD+100) for f in fields]

    def test_one_late_frame_recovers_original_deadline(self):
        r=assess(self.rows([1,7,14,19,25]))
        self.assertTrue(r['passes_field_budget'])
        self.assertEqual(r['interval_field_histogram'],{5:1,6:2,7:1})
        self.assertEqual(r['phase_above_20ms'],0)
        self.assertEqual(r['late_runs'],[dict(first_frame=2,frames=1,recovered_at_frame=3)])

    def test_two_delayed_frames_recover_without_changing_the_origin(self):
        r=assess(self.rows([1,8,14,19]))
        self.assertTrue(r['passes_field_budget'])
        self.assertEqual(r['late_runs'],[dict(first_frame=1,frames=2,recovered_at_frame=3)])
        self.assertFalse(r['unrecovered_at_recording_end'])
        self.assertTrue(assess(self.rows([1,8,14]))['unrecovered_at_recording_end'])

    def test_steady_seven_fields_accumulates_unacceptable_drift(self):
        r=assess(self.rows([1,8,15,22]))
        self.assertFalse(r['passes_field_budget'])
        self.assertEqual(r['intervals_outside_budget'],0)
        self.assertEqual(r['first_outside_field_budget'],2)

    def test_early_or_two_fields_late_are_rejected(self):
        for fields in ([1,6,13],[1,9,13]):
            self.assertFalse(assess(self.rows(fields))['passes_field_budget'])

    def test_field_counter_does_not_hide_intrafield_delay(self):
        rows=self.rows([1,8,13]); rows[1]['tstates']+=1000
        r=assess(rows)
        self.assertTrue(r['passes_field_budget'])
        self.assertEqual(r['phase_above_20ms'],1)
        self.assertFalse(r['irq_boundary_publication_verified'])


if __name__=='__main__': unittest.main()
