"""Boundary tests for disk planning; full emulator checks use verify_series."""
import unittest
import contextlib
import io
from unittest.mock import patch
from ima3_series import capacity_samples,plan_parts,plan_volumes,FIRST_PLAYER_SECTOR


class SeriesPlanning(unittest.TestCase):
    def test_public_converter_defaults_to_ima3_and_keeps_disk_modes(self):
        from convert_audio import main
        base=['input.wav','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse']
        for flags,expected in (([],'single'),(['--codec','ima3'],'single'),(['--disk-mode','all'],'all'),(['--disk-mode','preview'],'preview')):
            with patch('convert_ima3_audio.convert',return_value={'quality_gate_passed':True}) as convert,patch('convert_audio.convert') as legacy:
                with self.assertRaises(SystemExit) as result:main(base+flags+['--target-snr','25'])
                self.assertEqual(result.exception.code,0)
                self.assertEqual(convert.call_args.args[0].disk_mode,expected)
                self.assertEqual(convert.call_args.args[0].target_snr,25)
                legacy.assert_not_called()

    def test_public_converter_preserves_failed_quality_exit(self):
        from convert_audio import main
        with patch('convert_ima3_audio.convert',return_value={'quality_gate_passed':False}):
            with self.assertRaises(SystemExit) as result:
                main(['input.wav','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse'])
            self.assertEqual(result.exception.code,2)

    def test_legacy_converter_requires_explicit_codec(self):
        from convert_audio import main
        base=['input.wav','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse','--iterations','1']
        with patch('convert_audio.convert') as legacy,patch('convert_ima3_audio.convert') as accepted:
            main(base+['--codec','ima4'])
            self.assertEqual(legacy.call_args.args[0].iterations,1)
            self.assertEqual(legacy.call_args.args[0].codec,'ima4')
            accepted.assert_not_called()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:main(base)
        self.assertEqual(result.exception.code,2)

    def test_codec_abbreviation_cannot_misroute(self):
        from convert_audio import main
        with contextlib.redirect_stderr(io.StringIO()),patch('convert_audio.convert') as legacy,patch('convert_ima3_audio.convert') as accepted:
            with self.assertRaises(SystemExit) as result:
                main(['input.wav','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse','--cod','ima4'])
            self.assertEqual(result.exception.code,2)
            legacy.assert_not_called()
            accepted.assert_not_called()

    def test_cli_defaults_to_one_disk(self):
        from convert_ima3_audio import main
        base=['converter','input.wav','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse']
        for flags,expected in (([],'single'),(['--disk-mode','all'],'all'),(['--disk-mode','preview'],'preview')):
            with patch('sys.argv',base+flags),patch('convert_ima3_audio.convert',return_value={'quality_gate_passed':True}) as convert:
                with self.assertRaises(SystemExit) as result:main()
                self.assertEqual(result.exception.code,0)
                self.assertEqual(convert.call_args.args[0].disk_mode,expected)

    def test_source_is_covered_once(self):
        maximum=capacity_samples()
        self.assertEqual(maximum,251888)
        for samples in (1,8064,maximum-129,maximum-128,maximum-127,20*maximum+1):
            parts=plan_parts(samples)
            self.assertEqual(parts[0]['start'],0)
            self.assertEqual(parts[-1]['stop'],samples)
            self.assertEqual(sum(p['stop']-p['start'] for p in parts),samples)
            self.assertEqual([p['stop'] for p in parts[:-1]],[p['start'] for p in parts[1:]])
            for p in parts:
                self.assertLessEqual(p['samples'],maximum)
                self.assertGreaterEqual(p['samples']-(p['stop']-p['start']),128)
                self.assertEqual(p['samples']%8,0)

    def test_all_and_single_disk_boundary(self):
        parts=plan_parts(20*(capacity_samples()-128)+1)
        volumes=plan_volumes(parts)
        self.assertEqual([i for v in volumes for i in v],list(range(len(parts))))
        self.assertEqual(plan_volumes(parts,single=True),volumes[:1])
        self.assertEqual(len(volumes[0]),5)
        for v in volumes:
            self.assertLessEqual(FIRST_PLAYER_SECTOR+sum(parts[i]['sectors'] for i in v),2560)
        for v in volumes[:-1]:
            self.assertGreater(FIRST_PLAYER_SECTOR+sum(parts[i]['sectors'] for i in v)+parts[v[-1]+1]['sectors'],2560)

    def test_exact_sector_fit(self):
        parts=[dict(sectors=2560-FIRST_PLAYER_SECTOR),dict(sectors=1)]
        self.assertEqual(plan_volumes(parts),[[0],[1]])
        self.assertEqual(plan_volumes(parts,single=True),[[0]])

    def test_short_tail_and_rejections(self):
        parts=plan_parts(capacity_samples()-127)
        self.assertEqual(parts[-1]['stop']-parts[-1]['start'],1)
        self.assertEqual(parts[-1]['samples'],8192)
        for count in (0,-1):
            with self.assertRaises(ValueError):plan_parts(count)
        for maximum in (8,8193,capacity_samples()+8):
            with self.assertRaises(ValueError):plan_parts(1,part_samples=maximum)


if __name__=='__main__':unittest.main()
