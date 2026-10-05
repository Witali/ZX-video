"""A failed optional phase candidate must not discard verified IMA4 audio."""
from contextlib import ExitStack
import gzip,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import convert_audio as c


class PhaseFallback(unittest.TestCase):
    def exercise(self, failure):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=np.full(8192,128,dtype='u1');source[:8064]=129
            c.pcm_wav(root/'source.wav',source)
            args=SimpleNamespace(input=root/'source.wav',output=root/'out',duration=None,
                prepared_pcm=True,iterations=0,quality='best',attempts=3,
                fuse=root/'fuse',ffmpeg='ffmpeg',refine_clock=False,no_recording=True,target_snr=20.)

            def calibrate(folder,packed,reference,*unused):
                folder.mkdir(parents=True);(folder/'assembly').mkdir()
                meta={'hot_indices':[0]}
                (folder/'player.json').write_text(json.dumps(meta))
                (folder/'soundtrack.ima.gz').write_bytes(gzip.compress(packed))
                (folder/'output-times.u32.gz').write_bytes(gzip.compress(np.arange(8192,dtype='<u4').tobytes()))
                for name in ('audiobook-preview.trd','source-preview.wav','native.json','fuse.json','quality.json',
                             'voice-jitter.json','loop-2-voice-jitter.json','clock-aware-output-preview.wav','uniform-clock-source-preview.wav'):
                    (folder/name).write_bytes(b'test fixture')
                return folder,meta

            def validate(folder,*unused):
                if folder.name=='disk-encode-1':raise failure
                score={'pilot':21.,'disk-encode-2':23.,'disk-encode-3':22.}[folder.name]
                return dict(minimum_snr_db=score,speed_within_two_percent=True)

            def host(clock,folder,width,weight,horizon,*unused):
                folder.mkdir();(folder/'soundtrack.ima.gz').write_bytes(gzip.compress(bytes([1])*4096))
                return dict(host_fixed_clock_snr_db=30-int(folder.name[-1]),
                            beam_width=width,control_regularization=weight,block_size=horizon)

            with ExitStack() as patches:
                for name,value in [('snapshot_sources',lambda path:{}),('encode',lambda pcm:bytes(4096)),
                                   ('calibrate',calibrate),('validate',validate),('host_search',host),
                                   ('sample_positions',lambda meta:np.arange(8192)),
                                   ('compensate',lambda pcm,*a,**kw:pcm),('independent_ima_check',lambda *a:dict(complete=True))]:
                    patches.enter_context(patch.object(c,name,value))
                report=c.convert(args)
            self.assertEqual(report['selected_variant']['directory'],'disk-encode-2')
            self.assertEqual(len(report['variants']),3)
            self.assertEqual(len(report['rejected_variants']),1)
            self.assertFalse(report['rejected_variants'][0]['qualified'])
            self.assertTrue(report['quality_gate_passed'])
            self.assertEqual((args.output/'audiobook-preview.trd').read_bytes(),b'test fixture')

    def test_phase_failure_keeps_baseline_and_evaluates_later_candidates(self):
        self.exercise(c.PhaseCalibrationError('complete cold trace failed repeat-phase check: [626, 218]'))

    def test_corrupt_bits_are_fatal_not_a_quality_rejection(self):
        with self.assertRaisesRegex(AssertionError,'wrong PDM bit'):
            self.exercise(AssertionError('wrong PDM bit'))

    def test_unrelated_runtime_failure_is_fatal(self):
        with self.assertRaisesRegex(RuntimeError,'unexpected tool failure'):
            self.exercise(RuntimeError('unexpected tool failure'))


if __name__=='__main__':unittest.main()
