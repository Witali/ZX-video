"""Noise packing, actual Z80 AY register writes, and synthesis selection."""
import unittest
import struct

import numpy as np

import ay_fidelity as ay
import ay_noise
import blocked_stream
import build_fast_sparse_trd as codec
import build_long_video_trd as video
import packed_stream
from retune_ay_build import replace_ay_states
import test_blocked_stream as block_tests
from test_memory_clock import fixture
from test_packet_lookahead import run
from compare_ay_fidelity import match_onsets, onsets


class AyNoiseTests(unittest.TestCase):
    def test_retune_versions_checksum_and_original_pixels(self):
        state=bytes(i%256 for i in range(3840))
        tone=video.AyFrame((300,400,500),(10,12,14))
        noise=video.AyFrame(tone.periods,tone.volumes,17)
        original=video.serialize_video([video.make_packet(state,None,tone.serialize())],25/3,25/3)
        tuned=replace_ay_states(original,[noise])
        self.assertEqual(tuned[4],5)
        self.assertEqual(tuned[24:32],b'ZXVAY05 ')
        self.assertEqual(tuned[264:273],noise.serialize())
        self.assertEqual(tuned[273:],original[273:])
        self.assertEqual(struct.unpack_from('<H',tuned,262)[0],(sum(state)+sum(noise.serialize()))&65535)
        self.assertEqual(replace_ay_states(tuned,[tone]),original)
        direct=video.serialize_video([video.make_packet(state,None,noise.serialize())],25/3,25/3)
        self.assertEqual(direct,tuned)

    def test_noise_apply_survives_irq_at_every_instruction_boundary(self):
        frame=video.AyFrame((0xABC,0xFED,0x123),(3,14,15),31)
        reference,labels=fixture(interleaved=True,ay_noise=True)
        for i,b in enumerate(frame.serialize()):reference.write8(labels['ay_state']+i,b)
        before=reference.steps
        run(reference,labels,'ay_apply')
        steps=reference.steps-before
        for boundary in range(steps):
            cpu,labels=fixture(interleaved=True,ay_noise=True)
            for i,b in enumerate(frame.serialize()):cpu.write8(labels['ay_state']+i,b)
            cpu.pc=labels['ay_apply'];cpu.push(0x5F00)
            for _ in range(boundary):cpu.step()
            return_pc=cpu.pc;cpu.push(return_pc);cpu.pc=0xBDBD
            while cpu.pc!=return_pc:cpu.step()
            while cpu.pc!=0x5F00:cpu.step()
            self.assertEqual(cpu.ay,reference.ay)
            self.assertEqual(cpu.sp,0xBFF0)

    def test_v10_stream_plays_tone_noise_transitions_and_v9_is_rejected(self):
        states=[bytes(3840)]*4
        audio=[video.AyFrame((300,400,500),(10,12,14),n).serialize() for n in (0,1,31,0)]
        _,packets=codec.make_volume_packets(states,audio,0,2530,packed=True)
        frames=[packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks=[blocked_stream.Block(f,f,1,True,0) for f in frames]
        helper=block_tests.BlockedStreamTests()
        helper.run_player(states,blocks,ay_states=audio,interleaved=True,ay_noise=True)
        with self.assertRaisesRegex(AssertionError,'entered fatal'):
            helper.run_player(states,blocks,ay_states=audio,interleaved=True,ay_noise=True,stream_version=9)
        with self.assertRaisesRegex(AssertionError,'entered fatal'):
            helper.run_player(states,blocks,ay_states=audio,interleaved=True,stream_version=10)

    def test_all_periods_round_trip_and_z80_registers_and_cycles(self):
        cpu,labels=fixture(interleaved=True,ay_noise=True)
        # Follow noise by tone-only: R6 and the mixer must both reset.
        for noise in (*range(1,32),0):
            frame=video.AyFrame((0xABC,0xFED,0x123),(3,14,15),noise)
            data=frame.serialize()
            self.assertEqual(len(data),9)
            self.assertEqual(video.AyFrame.deserialize(data),frame)
            for i,b in enumerate(data):cpu.write8(labels['ay_state']+i,b)
            cycles=run(cpu,labels,'ay_apply')
            self.assertEqual(cycles,ay_noise.APPLY_TSTATES['extended_noise' if noise else 'extended_tones'])
            self.assertEqual(list(cpu.ay[:11]),[0xBC,0xA,0xED,0xF,0x23,1,noise,frame.mixer,3,14,15])

    def test_legacy_player_cycles_unchanged(self):
        cpu,labels=fixture()
        self.assertEqual(run(cpu,labels,'ay_apply'),ay_noise.APPLY_TSTATES['legacy'])

    def test_noise_detection_rejects_tone_and_silence(self):
        rate=22050;t=np.arange(rate*3)/rate
        signals=(np.zeros(len(t)),.1*np.sin(2*np.pi*440*t),
                 np.random.default_rng(31).normal(0,.1,len(t)))
        for i,signal in enumerate(signals):
            magnitude,rms=ay.spectra(signal,rate,25/3,25)
            period,volume,_=ay.arrange_noise(magnitude,rms,np.ones(25),np.zeros((25,3),dtype=int))
            if i<2:self.assertFalse(np.any(period))
            else:
                self.assertTrue(np.all(period[2:-2]>0))
                self.assertTrue(np.all(volume[2:-2,1]>0))
                self.assertFalse(np.any(volume[:,[0,2]]))

    def test_noise_does_not_replace_stronger_harmony(self):
        rng=np.random.default_rng(19)
        magnitude,rms=ay.spectra(rng.normal(0,.1,22050*3),22050,25/3,25)
        volumes=np.full((25,3),15)
        period,result,_=ay.arrange_noise(magnitude,rms,np.ones(25),volumes)
        self.assertFalse(np.any(period))
        np.testing.assert_array_equal(result,volumes)

    def test_noise_continuity_and_unused_tone_pitch(self):
        frame=video.AyFrame((100,200,300),(0,12,0),31)
        different=video.AyFrame((100,3900,300),(0,12,0),31)
        signal=ay.render([frame]*2,25/3)
        np.testing.assert_allclose(signal,ay.render([frame],25/6),atol=1e-12)
        np.testing.assert_array_equal(signal,ay.render([different]*2,25/3))
        self.assertGreater(np.std(signal),.02)
        self.assertEqual(len(ay.noise_sequence()),131071)

    def test_rhythm_matching_penalizes_missing_and_extra_events(self):
        match=match_onsets([2,8,15],[3,7,20])
        self.assertEqual(match['matched'],2)
        self.assertAlmostEqual(match['f1'],2/3)
        self.assertEqual(onsets(np.zeros((20,81))),[])
        self.assertEqual(match_onsets([],[])['f1'],0)


if __name__=='__main__':unittest.main()
