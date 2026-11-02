"""AY delta-stream, complete foreground execution and live menu regressions."""
import json
import tempfile
import unittest
from pathlib import Path

from arrangement import notes_for_pattern, timeline
from build import HERE, ROOT, REGISTER_ORDER, MUTE_WRITES, CONTROL_HZ, REPEAT_GAP_FIELDS, build, control_frames, pack_frames, sha, triangle_period, soft_edges
from verify import unpack
from verify_demo import native
from music_codec import compress, decompress


class MusicMenuTests(unittest.TestCase):
    def test_original_arrangements_unchanged(self):
        reference = json.loads((HERE/'reports/import-reference.json').read_text())
        for song in ('lumiere','alicia'):
            source = (HERE/'scores'/f'{song}.json').read_bytes()
            canonical = json.dumps(timeline(json.loads(source)),separators=(',',':')).encode()
            self.assertEqual(sha(source),reference[song]['score_sha256'])
            self.assertEqual(sha(canonical),reference[song]['timeline_sha256'])

    def test_complete_player_ui_and_cached_switching(self):
        (ROOT/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='ay-menu-',dir=ROOT/'build') as temp:
            meta = build(temp)
            report = native(Path(temp))
            self.assertEqual((Path(temp)/meta['disk_name']).stat().st_size,655360)
            self.assertLess(meta['cache_bytes'],5*16384)
            self.assertTrue(report['complete_playlist'] and report['no_beeper_audio'])
            self.assertEqual(len(set(p['name'] for p in report['pictures_completed'])),18)
            self.assertTrue(report['controls']['manual_song_switch'])
            self.assertTrue(report['controls']['held_space_swallowed'])
            self.assertLess(max(map(int,report['irq_body_tstates'])),meta['frame_tstates'])

    def test_lossless_grammar_and_soft_edges_preserve_complete_parts(self):
        streams=[]
        for name in ('lumiere','alicia'):
            data,_=control_frames(json.loads((HERE/'scores'/f'{name}.json').read_text()))
            faded,report=soft_edges(data)
            a,b=unpack(data),unpack(faded)
            self.assertEqual(len(a),len(b))
            for before,after in zip(a,b):
                self.assertEqual(before[:8]+before[11:],after[:8]+after[11:])
                for reg in (8,9,10):
                    self.assertEqual(bool(before[reg]),bool(after[reg]))
                    if before[reg]&16:
                        self.assertEqual(before[reg],after[reg])
            streams.append(faded)
        packed,dictionary,depth=compress(streams)
        self.assertLessEqual(depth,12)
        self.assertLess(sum(map(len,packed))+len(dictionary),sum(map(len,streams)))
        self.assertEqual([decompress(p,dictionary) for p in packed],streams)

    def test_delta_roundtrip_preserves_envelope_restart_events(self):
        start = bytearray(14)
        start[7] = 0x38
        start[10] = 16
        start[11] = 32
        start[13] = 14
        hold = start.copy()
        hold[13] = 255
        frames = [bytes(start)]+[bytes(hold)]*600+[bytes(start)]+[bytes(hold)]*9
        data,records,writes = pack_frames(frames)
        self.assertEqual(unpack(data),frames)
        self.assertLess(len(data),60)
        self.assertGreater(records,3)
        with self.assertRaises(ValueError):
            unpack(data[:-1])
        with self.assertRaises(ValueError):
            unpack(data+b'\0')
        with self.assertRaises(ValueError):
            unpack(b'\x01\x00\xC0\0')

    def test_actual_song_tuning_and_timing_bounds(self):
        for name in ('lumiere','alicia'):
            score = json.loads((HERE/'scores'/f'{name}.json').read_text())
            data,meta = control_frames(score)
            frames = unpack(data)
            self.assertEqual(len(frames),meta['ticks'])
            self.assertLessEqual(meta['max_note_boundary_error_seconds'],.01)
            self.assertLessEqual(meta['max_triangle_pitch_error_cents'],18)
            self.assertGreater(meta['triangle_fields'],0)
            self.assertLess(meta['envelope_restarts'],meta['triangle_fields']//5)
            self.assertTrue(all(sum(bool(row[i]&16) for i in (8,9,10))<=1 for row in frames))
            classic,classic_meta = control_frames(score,triangle=False)
            self.assertEqual(classic_meta['triangle_fields'],0)
            self.assertTrue(all(row[10]<16 for row in unpack(classic)))
        self.assertLess(abs(triangle_period(35)[1]),4)
        self.assertGreater(abs(triangle_period(42)[1]),18)

    def test_click_repair_preserves_source_grid_and_removes_zero_periods(self):
        old = json.loads((HERE/'reports/ay-only/build.json').read_text())
        for name in ('lumiere','alicia'):
            score = json.loads((HERE/'scores'/f'{name}.json').read_text())
            baseline,before = control_frames(score,click_safe=False)
            fixed,after = control_frames(score,articulation=False,percussion=False)
            self.assertEqual(before['frames_sha256'],next(s for s in old['songs'] if s['song']==name)['frames_sha256'])
            self.assertEqual(before['ticks'],after['ticks'])
            self.assertLess(after['envelope_restarts'],before['envelope_restarts']//2)
            self.assertLessEqual(after['max_release_extension_seconds'],.065)
            rows = unpack(fixed)
            self.assertTrue(all(row[11]+256*row[12]>0 and row[6]==31 for row in rows))
            self.assertGreater(after['phase_preserved_bass_note_changes'],0)

    def test_repeated_lead_notes_have_real_silent_fields(self):
        for name in ('lumiere','alicia'):
            score = json.loads((HERE/'scores'/f'{name}.json').read_text())
            data,meta = control_frames(score)
            rows = unpack(data)
            count = 0
            notes = timeline(score)[0][0]
            for before,after in zip(notes,notes[1:]):
                onset = round(after[0]*CONTROL_HZ)
                end = round((before[0]+before[1])*CONTROL_HZ)
                if before[2]!=after[2] or not 0<=onset-end<REPEAT_GAP_FIELDS:
                    continue
                self.assertTrue(all(row[8]==0 for row in rows[onset-REPEAT_GAP_FIELDS:onset]))
                self.assertGreater(rows[onset][8],0)
                self.assertEqual(rows[onset-REPEAT_GAP_FIELDS-1][:2],rows[onset][:2])
                count += 1
            self.assertEqual(count,len(meta['repeated_note_articulation']))
            self.assertGreater(count,0)

    def test_repeat_attack_release_and_ties(self):
        score = dict(tempo_bpm=120,beats_per_bar=4,playlist=['A'],
                     patterns=dict(A=['C4:1 C4:1 R:2']),chord_pairs=[['Bm','Bm']])
        data,meta = control_frames(score,percussion=False)
        rows = unpack(data)
        onset = round(.5*CONTROL_HZ)
        attack = [row[8] for row in rows[onset:onset+5]]
        self.assertEqual(attack,sorted(attack))
        self.assertLess(attack[0],attack[-1])
        tail = [row[8] for row in rows[onset-6:onset]]
        self.assertEqual(tail,sorted(tail,reverse=True))
        self.assertEqual(tail[-2:],[0,0])
        score['patterns']['A'] = ['C4:4~','C4:4']
        tied,tied_meta = control_frames(score,percussion=False)
        middle = round(2*CONTROL_HZ)
        self.assertEqual(len(timeline(score)[0][0]),1)
        self.assertFalse(tied_meta['repeated_note_articulation'])
        self.assertTrue(all(row[8]>0 for row in unpack(tied)[middle-2:middle+2]))

    def test_noise_uses_only_silent_piano_slots_and_preserves_bass_envelope(self):
        for name in ('lumiere','alicia'):
            score = json.loads((HERE/'scores'/f'{name}.json').read_text())
            plain,plain_meta = control_frames(score,percussion=False)
            noisy,meta = control_frames(score)
            without,with_noise = unpack(plain),unpack(noisy)
            self.assertEqual(len(without),len(with_noise))
            count = 0
            for a,b in zip(without,with_noise):
                self.assertGreater(b[11]+256*b[12],0)
                self.assertTrue(all(b[r]<16 for r in (8,9)))
                self.assertEqual(b[7]&(8|32),8|32)
                if b[7]&16:
                    self.assertEqual(a,b)
                else:
                    self.assertEqual(a[9],0)
                    self.assertEqual(b[7]&2,2)
                    self.assertIn(b[6],(4,12))
                    self.assertIn(b[9],(5,7))
                    self.assertTrue(all(a[r]==b[r] for r in range(14) if r not in (6,7,9)))
                    count += 1
            self.assertEqual(count,meta['noise_fields'])
            self.assertGreater(count,0)
            self.assertEqual(meta['envelope_restarts'],plain_meta['envelope_restarts'])

    def test_generators_are_programmed_before_channel_enable(self):
        for volume in (8,9,10):
            self.assertGreater(REGISTER_ORDER.index(volume),REGISTER_ORDER.index(13))
        self.assertEqual([r for r,v in MUTE_WRITES[:3]],[8,9,10])
        self.assertTrue(all(v==0 for r,v in MUTE_WRITES if r in (8,9,10)))
        self.assertLess([r for r,v in MUTE_WRITES].index(13),[r for r,v in MUTE_WRITES].index(11))

    def test_reject_invalid_bars_and_ties(self):
        score = dict(patterns=dict(A=['C4:3']),beats_per_bar=4,chord_pairs=[['Bm','Em']])
        with self.assertRaises(ValueError):
            notes_for_pattern(score,'A')
        score['patterns']['A'] = ['C4:4~']
        with self.assertRaises(ValueError):
            notes_for_pattern(score,'A')


if __name__=='__main__':
    unittest.main()
