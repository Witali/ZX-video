"""Neutral packet selection, table invariants and exact periodic state proof."""
import unittest
import numpy as np

from build_pdm import CPU_CLOCK
from ima_waveform_encoder import WaveformModel
from neutral_packet_model import (NEUTRAL_PACKET_WORD,NEUTRAL_PACKET_SUCCESSOR,
    ORDINARY_PENTAGON_HOLDS,PHYSICAL_CPU_HZ,on_time_tstates,
    validate_neutral_packet,apply_neutral_packet,select_neutral_packet)
from probe_feedback_packets import integral_table


def model():
    return dict(holds=list(ORDINARY_PENTAGON_HOLDS),beta=.5,extent=1.,pcm_origin=0,
                pcm_quantization_bias=512,neutral_packet_word=NEUTRAL_PACKET_WORD,
                neutral_packet_successor=NEUTRAL_PACKET_SUCCESSOR)


def table():
    words,nxt,_=integral_table(64,2,holds=ORDINARY_PENTAGON_HOLDS,beta=.5,extent=1.,pcm_origin=0)
    return words,nxt


class NeutralPacketTests(unittest.TestCase):
    def test_absent_option_is_identity_and_unchanged(self):
        words,nxt=table();before=words.copy();next_before=nxt.copy()
        for settings in (None,{},dict(holds=[1])):
            result,next_result=apply_neutral_packet(words,nxt,settings)
            self.assertIs(result,words);self.assertIs(next_result,nxt)
            self.assertIsNone(validate_neutral_packet(settings))
        np.testing.assert_array_equal(words,before);np.testing.assert_array_equal(nxt,next_before)

    def test_override_copies_only_bin32_and_stabilizes_every_state(self):
        words,nxt=table();before=words.copy();next_before=nxt.copy()
        words.flags.writeable=False;nxt.flags.writeable=False
        output,next_output=apply_neutral_packet(words,nxt,model())
        self.assertIsNot(output,words);self.assertIsNot(next_output,nxt)
        mask=np.arange(64)!=32
        np.testing.assert_array_equal(output[mask],words[mask])
        np.testing.assert_array_equal(next_output[mask],nxt[mask])
        self.assertTrue(np.all(output[32]==NEUTRAL_PACKET_WORD))
        self.assertTrue(np.all(next_output[32]==16))
        np.testing.assert_array_equal(words,before);np.testing.assert_array_equal(nxt,next_before)
        for state in range(32):
            self.assertEqual(int(next_output[32,state]),16)
            self.assertEqual(int(next_output[32,next_output[32,state]]),16)
            self.assertEqual(int(output[32,next_output[32,state]]),NEUTRAL_PACKET_WORD)

    def test_exhaustive_balanced_selection_and_complement_tie(self):
        report,arrays=select_neutral_packet()
        self.assertEqual(report['all_words_enumerated'],65536)
        self.assertEqual(report['balanced_candidates'],848)
        self.assertFalse(report['source_audio_opened'])
        self.assertEqual(report['selected_word'],0x56AD)
        self.assertEqual(on_time_tstates(0x56AD),225)
        self.assertFalse(arrays['allowed'][0]);self.assertFalse(arrays['allowed'][65535])
        self.assertTrue(np.all(np.isin(arrays['on_tstates'][arrays['allowed']],(224,225))))
        complement=65535-NEUTRAL_PACKET_WORD
        self.assertEqual(arrays['variance'][NEUTRAL_PACKET_WORD],arrays['variance'][complement])
        self.assertEqual(tuple(arrays['ranking'][:2]),(NEUTRAL_PACKET_WORD,complement))
        self.assertLess(report['solve_condition'],100)
        self.assertLess(report['solve_residual_max'],1e-14)
        self.assertLess(report['spectral_radius'],1)

    def test_independent_sequential_periodic_filter_state(self):
        report,arrays=select_neutral_packet()
        bits=np.array([1. if NEUTRAL_PACKET_WORD&(1<<shift) else -1. for shift in range(15,-1,-1)])
        steady=np.linalg.solve(np.eye(6)-arrays['a'],arrays['b']@bits)
        state=steady.copy();observed=[];analog=WaveformModel()
        holds=np.asarray(ORDINARY_PENTAGON_HOLDS)*CPU_CLOCK/PHYSICAL_CPU_HZ
        for hold,bit in zip(holds,bits):
            e,u=analog.transition(hold/2);observed.append(analog.c@(e@state+u*bit))
            e,u=analog.transition(hold);state=e@state+u*bit
        np.testing.assert_allclose(state,steady,atol=2e-13,rtol=0)
        observed=np.asarray(observed);weight=np.asarray(ORDINARY_PENTAGON_HOLDS)
        average=np.sum(weight*observed)/449
        variance=np.sum(weight*(observed-average)**2)/449
        self.assertAlmostEqual(variance,report['selected_estimated_variance'],places=16)

    def test_model_validation_rejects_partial_flags_dc_exploit_and_wrong_scope(self):
        good=model();self.assertEqual(validate_neutral_packet(good),(0x56AD,16))
        variants=({'neutral_packet_word':None},{'neutral_packet_word':True},
            {'neutral_packet_word':float(NEUTRAL_PACKET_WORD)},
            {'neutral_packet_word':np.int64(NEUTRAL_PACKET_WORD)},
            {'neutral_packet_word':-1},{'neutral_packet_word':65536},
            {'neutral_packet_word':0},{'neutral_packet_word':65535},
            {'neutral_packet_successor':15},{'neutral_packet_successor':16.},
            {'neutral_packet_successor':True},{'pcm_quantization_bias':0},
            {'pcm_quantization_bias':512.},{'pcm_bins':128},
            {'family':'sigma_delta2'},{'pcm_origin':.5},{'extent':.5},
            {'beta':.4},{'q_clip':(0,14)}, {'holds':[1]*16})
        for changes in variants:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                validate_neutral_packet(dict(good,**changes))
        for field in ('neutral_packet_word','neutral_packet_successor'):
            partial=good.copy();partial.pop(field)
            with self.assertRaises(ValueError):validate_neutral_packet(partial)

    def test_malformed_table_rejected_before_mutation(self):
        words,nxt=table()
        for first,second in ((words[:63],nxt),(words,nxt[:63]),(words.astype(float),nxt),
                             (np.full((64,32),65536),nxt),(words,np.full((64,32),32))):
            with self.assertRaises(ValueError):apply_neutral_packet(first,second,model())


if __name__=='__main__':unittest.main()
