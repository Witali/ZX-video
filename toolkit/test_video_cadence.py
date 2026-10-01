"""Cadence boundaries, AY envelope identity and real timestamp gate tests."""
import unittest
from video_cadence import fields_for_fps, scaffold_audio
from build_long_video_trd import AyFrame
import ay_interrupt
from profile_fap3 import summarize_fuse, FIELD


class CadenceTests(unittest.TestCase):
    def test_supported_rates_and_no_fractional_fields(self):
        self.assertEqual(fields_for_fps('10'),5)
        self.assertEqual(fields_for_fps('25/3'),6)
        for value in ('9','12','0','-10'):
            with self.assertRaises(ValueError): fields_for_fps(value)

    def test_envelope_preserves_all_ay_changes_and_boundary_states(self):
        sound = [AyFrame((i+1,100+i,200-i),(i%16,0,7),i%32) for i in range(20)]
        expected = ay_interrupt.encode_ticks(sound)
        envelope = scaffold_audio(sound,5)
        ticks = ay_interrupt.encode_ticks(envelope)
        self.assertEqual([t for i,t in enumerate(ticks) if i%6 != 5],expected)
        self.assertEqual(ticks[5::6],[b'\0']*4)
        self.assertEqual(envelope[5::6],sound[4::5])
        old = sound[:18]
        self.assertIs(scaffold_audio(old,6),old)
        with self.assertRaises(ValueError): scaffold_audio(sound[:-1],5)

    def test_10fps_gate_rejects_six_field_intervals(self):
        def report(times, phases, late):
            return dict(complete=True,frame_fields=5,
                publications=[dict(tstate=t,late_fields=l) for t,l in zip(times,late)],
                actual_phase_tstates=phases,ay_record_field_gaps=0,ay_record_field_duplicates=0,
                audio_underruns=0,late_runs=[],reads=[])
        good = summarize_fuse(report([0,5*FIELD,10*FIELD],[0,0,0],[0,0,0]))
        bad = summarize_fuse(report([0,6*FIELD,12*FIELD],[0,FIELD,2*FIELD],[0,1,2]))
        self.assertTrue(good['nominal_deadlines_met'])
        self.assertFalse(bad['nominal_deadlines_met'])
        self.assertFalse(bad['fallback_one_field_met'])
        self.assertEqual(bad['missed_nominal_frame_indices'],[1,2])

    def test_three_volume_window_balance_keeps_rows_and_coverage(self):
        from balance_cb41_cadence import three_parts
        sets=[{0,i//16+1} for i in range(96)]
        costs=[1]*32+[6]*32+[1]*32
        parts,report=three_parts(sets,costs,64)
        self.assertEqual([i for lo,hi in parts for i in range(lo,hi)],list(range(96)))
        self.assertLessEqual(max(report['estimated_video_bytes']),128)
        self.assertEqual(sum(report['estimated_video_bytes']),sum(costs))
        self.assertEqual(report['whole_movie_candidates_compressed'],0)
        with self.assertRaises(ValueError):three_parts([set(range(257))]*48,[1]*48,64)


if __name__ == '__main__': unittest.main()
