"""Host-format, partitioning and bootstrap regressions; no external tools needed."""
import hashlib
import math
import struct
import unittest

import numpy as np

from build_fap3_trd import Builder, volume_id
from build_long_video_trd import AyFrame
from encode_fap3 import encode
from fap3_disk_z80 import build_bootstrap
from profile_fap3 import summarize_fuse


class GenericConverterTests(unittest.TestCase):
    def test_single_black_frame_empty_huffman_contexts(self):
        state = np.zeros((1, 3840), dtype=np.uint8)
        state[:, 3072:] = 1
        raw, report = encode(state, [AyFrame((1, 1, 1), (0, 0, 0))]*6)
        self.assertEqual(raw[:4], b'FAP3')
        self.assertTrue(report['exact_compact_frames'])
        self.assertEqual(report['ay_ticks'], 6)

    def test_high_entropy_and_abrupt_scene_changes_roundtrip(self):
        rng = np.random.default_rng(92)
        states = np.zeros((5, 3840), dtype=np.uint8)
        states[:, 384:2688] = rng.integers(0, 256, (5, 2304), dtype=np.uint8)
        states[:, 3072:] = 1
        states[:, 3168:3744] = rng.integers(0, 128, (5, 576), dtype=np.uint8)
        states[2] = states[1]
        frames = [AyFrame((100+i, 200+i, 300+i), (i % 16, 8, 9), i % 32) for i in range(30)]
        _, report = encode(states, frames)
        self.assertTrue(report['exact_compact_frames'] and report['exact_ay_records'])
        self.assertLess(report['max_payload_bytes'], 4704)

    def test_nonblack_reserved_band_rejected(self):
        state = np.ones((1, 3840), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, 'black'):
            encode(state, [AyFrame((1, 1, 1), (0, 0, 0))]*6)

    def test_bootstrap_all_preload_bank_counts(self):
        sections = [dict(bank=6, sector=21, buffer=0x4000, address=0xc000, sectors=1)]*6
        for sectors in (1, 64, 65, 128, 129, 192, 193, 256):
            code, labels = build_bootstrap(sections, 40, sectors)
            self.assertEqual(len(code), 1024)
            self.assertGreaterEqual(labels['overlay_copy'], 0x6100)
            self.assertLessEqual(labels['end'], 0x6400)
            if 'overlay_jump' in labels:
                at = labels['overlay_jump']-0x6000
                self.assertEqual(code[at], 0xc3)
                self.assertEqual(int.from_bytes(code[at+1:at+3], 'little'), labels['overlay_copy'])
                from test_fap3_disk import DiskCPU, install
                cpu = DiskCPU(b'', b'')
                install(cpu, 0x6000, code)
                cpu.pc = labels['overlay_jump']
                before = cpu.tstates
                cpu.step()
                self.assertEqual(cpu.pc, labels['overlay_copy'])
                self.assertEqual(cpu.tstates-before, 10)

    def test_full_ring_bootstrap_is_byte_identical_to_00313d3(self):
        sections = [dict(bank=6, sector=21, buffer=0x4000, address=0xc000, sectors=1)]*6
        for interleaved, expected in (
                (False, 'ef3e3fca2e167196c74bf93c1065eb38d326dea0f168f2ce7c0a3fd531b8a6a7'),
                (True, 'ea96fd8fe2960517b660a08d554e9aa631a721249a002e6e3c54e27d41dbc020')):
            code, _ = build_bootstrap(sections, 40, 256, interleaved=interleaved)
            self.assertEqual(hashlib.sha256(code).hexdigest(), expected)

    def test_legacy_and_long_series_fingerprints(self):
        old = hashlib.sha256(b'raw'+struct.pack('<HH', 1000, 2000)).digest()[:6]
        self.assertEqual(volume_id(b'raw', [1000, 2000], 2), b'FAP3ZXV1'+old+b'\2\0')
        long_id = volume_id(b'raw', [60000, 70000], 2)
        self.assertEqual(len(long_id), 16)
        self.assertNotEqual(long_id, volume_id(b'raw', [60000, 70001], 2))

    def test_partition_real_capacity_and_counter_limit(self):
        class Fixture:
            raw = bytes(1900000)
            states = range(1900)
            offsets = list(range(0, 1900001, 1000))
            compress = staticmethod(lambda data: data)
            def volume(self, start, end, part):
                # Deliberately costlier startup than the initial estimate.
                used = 180+math.ceil((end-start)*1000/256)
                return None, dict(frames=end-start, free_sectors=2544-used,
                                  video_sectors=used-180)
        fixture = Fixture()
        ends = Builder.automatic_ends(fixture, max_frames=800)
        self.assertGreater(len(ends), 1)
        self.assertEqual(ends[-1], 1900)
        start = 0
        for end in ends:
            self.assertLessEqual(end-start, 800)
            self.assertGreaterEqual(fixture.volume(start, end, 1)[1]['free_sectors'], 16)
            start = end
        for invalid in (0, 10923):
            with self.assertRaises(ValueError): Builder.automatic_ends(fixture, invalid)

    def test_partial_or_unrecovered_timing_cannot_pass(self):
        report = dict(complete=True, publications=[dict(tstate=0, late_fields=0),
            dict(tstate=7*70908, late_fields=1)], actual_phase_tstates=[0, 70908],
            ay_record_field_gaps=0, ay_record_field_duplicates=0, audio_underruns=0,
            late_runs=[dict(start=1, end=1, recovered_at=None)], reads=[], seek_calls=[])
        result = summarize_fuse(report)
        self.assertEqual(result['missed_nominal_frame_indices'], [1])
        self.assertFalse(result['nominal_deadlines_met'] or result['fallback_one_field_met'])
        report.update(complete=False, publications=[], actual_phase_tstates=[], late_runs=[])
        result = summarize_fuse(report)
        self.assertFalse(result['nominal_deadlines_met'] or result['fallback_one_field_met'])

    def test_record_underrun_keeps_record_cursor_and_chip_state(self):
        from test_pipelined_frame import fixture
        from pipelined_frame_harness import Clock
        from benchmark_context_huffman import word
        h, _, ticks = fixture(2)
        clock = Clock(h, ticks, record_underruns=True)
        h.cpu.write8(h.audio['audio_enabled'], 1)
        before = bytes(h.cpu.ay)
        clock.run_irq()
        self.assertEqual(clock.ticks, 0)
        self.assertEqual(bytes(h.cpu.ay), before)
        self.assertEqual(word(h.cpu, h.audio['audio_underruns']), 1)
        self.assertEqual(len(clock.underruns), 1)


if __name__ == '__main__':
    unittest.main()
