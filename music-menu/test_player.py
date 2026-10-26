"""Music import identity, real instruction replay and menu regression checks."""
import json
import tempfile
import unittest
from pathlib import Path

from arrangement import notes_for_pattern, timeline
from build import HERE, ROOT, build, control_frames, sha
from verify import native_check, unpack


class MusicMenuTests(unittest.TestCase):
    def test_import_preserves_original_four_role_arrangements(self):
        reference = json.loads((HERE/'reports/import-reference.json').read_text())
        for song in ('lumiere', 'alicia'):
            source = (HERE/'scores'/f'{song}.json').read_bytes()
            result = timeline(json.loads(source))
            canonical = json.dumps(result, separators=(',', ':')).encode()
            self.assertEqual(sha(source), reference[song]['score_sha256'])
            self.assertEqual(sha(canonical), reference[song]['timeline_sha256'])

    def test_complete_cpu_playback_and_controls(self):
        (ROOT/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='zx-music-', dir=ROOT/'build') as temp:
            disk, meta = build(temp)
            report = native_check(Path(temp), meta)
            self.assertEqual(len(disk), 655360)
            self.assertEqual(len(report['variants']), 4)
            self.assertTrue(all(v['complete'] and v['ay_and_dds_exact'] for v in report['variants']))
            self.assertEqual(report['irq_handler_tstates'], 46)

    def test_alignment_eof_and_mode_validation(self):
        score = json.loads((HERE/'scores/alicia.json').read_text())
        for mode in ('hybrid', 'ay'):
            data, meta = control_frames(score, mode)
            self.assertEqual(len(unpack(data)), meta['ticks'])
            self.assertEqual(len(data) % 16, 0)
            self.assertLessEqual(meta['max_note_boundary_error_seconds'], .01)
            with self.assertRaises(ValueError):
                unpack(data[:-1])
            with self.assertRaises(ValueError):
                unpack(bytes(16)+data)
        with self.assertRaises(ValueError):
            control_frames(score, 'invalid')

    def test_reject_malformed_bars_and_ties(self):
        score = dict(patterns=dict(A=['C4:3']), beats_per_bar=4, chord_pairs=[['Bm','Em']])
        with self.assertRaises(ValueError):
            notes_for_pattern(score, 'A')
        score['patterns']['A'] = ['C4:4~']
        with self.assertRaises(ValueError):
            notes_for_pattern(score, 'A')


if __name__ == '__main__':
    unittest.main()
