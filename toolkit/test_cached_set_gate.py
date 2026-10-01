"""Reject weakened publication gates before replacing root disk images."""
import gzip
import json
from pathlib import Path
import unittest

from finish_cached_cell_set import timing_gate


def measured():
    path=Path(__file__).with_name('side_only_seek_evidence')/'window-work-ZX-video-front_part07-timing.json.gz'
    return json.loads(gzip.decompress(path.read_bytes()))


def delayed():
    r=measured();p=r['publications'][100]
    p['field']+=1;p['late_fields']=1
    p['tstate']+=70908-r['actual_phase_tstates'][100]
    r['actual_phase_tstates'][100]=70908
    r.update(nominal_late_frames=1,max_late_fields=1,max_actual_deviation_tstates=70908,
        late_runs=[dict(start=100,end=100,recovered_at=101)])
    return r


class GateTests(unittest.TestCase):
    def test_nominal_and_explicit_fallback(self):
        self.assertTrue(timing_gate(measured())['nominal_deadlines_met'])
        with self.assertRaises(AssertionError):timing_gate(delayed())
        r=timing_gate(delayed(),True)
        self.assertFalse(r['nominal_deadlines_met']);self.assertTrue(r['strict_one_field_fallback_met'])

    def test_one_extra_tstate_cannot_hide_in_irq_tolerance(self):
        r=delayed();r['actual_phase_tstates'][100]+=1;r['publications'][100]['tstate']+=1
        # Even a stale zero aggregate count must not permit >20 ms.
        self.assertEqual(r['actual_out_over_one_field'],0)
        with self.assertRaises(AssertionError):timing_gate(r,True)

    def test_missing_audio_partial_run_and_unrecovered_frame(self):
        for key,value in [('complete',False),('ay_record_field_gaps',1),('audio_underruns',1),
                          ('ay_record_field_duplicates',1),('max_late_fields',2),('bad_actual_intervals',1)]:
            r=delayed();r[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):timing_gate(r,True)
        for recovered in (None,102):
            r=delayed();r['late_runs'][0]['recovered_at']=recovered
            with self.assertRaises(AssertionError):timing_gate(r,True)

    def test_field_counts_are_verified_as_well_as_actual_out(self):
        r=delayed();r['publications'][100]['field']+=1
        with self.assertRaises(AssertionError):timing_gate(r,True)


if __name__=='__main__':unittest.main()
