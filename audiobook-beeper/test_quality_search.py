"""Quality-selection contracts and shared alphabet dispatch."""
import json
import gzip
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from convert_audio import main
from quality_search import host_search, ranked_hosts, search_plan
import numpy as np


class QualitySearch(unittest.TestCase):
    def test_default_quality_and_failure_gate_match_both_codecs(self):
        args = ['source.wav', '--output', 'unused', '--ffmpeg', 'ffmpeg', '--fuse', 'fuse']
        for codec, function in (('ima3', 'convert_ima3_audio.convert'), ('ima4', 'convert_audio.convert')):
            with patch(function, return_value={'quality_gate_passed': False}) as convert:
                with self.assertRaises(SystemExit) as status:
                    main(args+['--codec', codec, '--target-snr', '25'])
                self.assertEqual(status.exception.code, 2)
                options = convert.call_args.args[0]
                self.assertEqual((options.quality, options.target_snr, options.attempts), ('best', 25, 3))
                if codec=='ima4':self.assertTrue(options.refine_clock)

    def test_balanced_profile_remains_explicit_and_bounded(self):
        old = ((256, .03, 128), (512, .03, 128), (1024, .03, 256))
        self.assertEqual(search_plan('ima3', 'balanced'), old)
        for codec in ('ima3', 'ima4'):
            for count in (1, 2, 3):
                self.assertEqual(len(search_plan(codec, 'best', count)), count)
        with self.assertRaises(ValueError):search_plan('ima3', 'best', 0)

    def test_waveform_command_selects_real_alphabet_and_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out/'report.json').write_text(json.dumps({'host_fixed_clock_snr_db': 21.}))
            for codec in ('ima3', 'ima4'):
                with patch('quality_search.subprocess.run') as run:
                    host_search(Path('pilot'), out, 512, .03, 128, 'ffmpeg', codec)
                    command = run.call_args.args[0]
                    self.assertEqual('--ima3' in command, codec == 'ima3')
                    self.assertEqual(command[command.index('--commit-size')+1], '64')
                    self.assertTrue(run.call_args.kwargs['check'])

    def test_shortlist_uses_host_scores_without_marking_a_release(self):
        hosts = [dict(directory='first', host_fixed_clock_snr_db=19.),
                 dict(directory='second', host_fixed_clock_snr_db=23.),
                 dict(directory='third', host_fixed_clock_snr_db=22.)]
        selected = ranked_hosts(hosts)
        self.assertEqual([c['directory'] for c in selected], ['second', 'third'])
        self.assertTrue(all('quality_gate_passed' not in c for c in selected))
        self.assertEqual(len(hosts), 3)

    def test_best_continues_after_target_and_selects_measured_quality(self):
        # The pilot already passes 20 dB. Host ranking prefers encode-1,
        # but real execution prefers encode-2; selection must follow that.
        from convert_ima3_audio import convert
        from convert_audio import pcm_wav
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = np.full(8192, 128, dtype='u1'); source[:8000] = 129
            pcm_wav(root/'source.wav', source)
            (root/'fuse').write_bytes(b'fixture'); (root/'ffmpeg').write_bytes(b'fixture')
            args = SimpleNamespace(output=root/'out', input=root/'source.wav',
                ffmpeg=str(root/'ffmpeg'), fuse=root/'fuse', quality='best', attempts=3,
                duration=None, target_snr=20., no_recording=True, disk_mode='preview',
                prepared_pcm=True, reuse_pilot=None, resume=False)

            def build(source, packed, path, *unused):
                path.mkdir(parents=True)
                (path/'assembly').mkdir()
                score = 21. if path.name=='pilot' else 23. if path.name.endswith('3') else 20.5 if path.name.endswith('1') else 22.
                report = dict(complete=True, quality=dict(minimum_snr_db=score, speed_within_two_percent=True))
                for name, data in (('report.json', report), ('player.json', {'model': {}}),
                                   ('phase-probe.json', {'first_output_absolute_tstates':[3546900]})):
                    (path/name).write_text(json.dumps(data))
                (path/'audiobook-preview.trd').write_bytes(path.name.encode())
                (path/'clock-aware-output-preview.wav').write_bytes(b'fixture')
                return report

            def host(pilot, path, *unused):
                path.mkdir()
                (path/'soundtrack.ima.gz').write_bytes(gzip.compress(bytes(4096)))
                report = {'host_fixed_clock_snr_db':24. if path.name.endswith('1') else 22. if path.name.endswith('3') else 23.}
                (path/'report.json').write_text(json.dumps(report))
                return report

            with patch('convert_ima3_audio.build_verified', side_effect=build) as build_call, \
                 patch('convert_ima3_audio.host_search', side_effect=host) as host_call, \
                 patch('convert_ima3_audio.encode', return_value=bytes(4096)):
                report = convert(args)
                self.assertEqual(host_call.call_count, 3)
                self.assertEqual(build_call.call_count, 4)
                self.assertEqual(report['selected']['directory'], 'disk-encode-3')
                self.assertEqual(report['selected']['minimum_snr_db'], 23.)
                self.assertTrue(report['quality_gate_passed'])


if __name__ == '__main__':
    unittest.main()
