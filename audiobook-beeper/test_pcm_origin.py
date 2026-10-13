"""Independent table arithmetic, legacy compatibility and full RAM-layout bounds."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

from direct_player import HOLDS, MEASURED_MODEL, MAX_PACKED_BYTES, build_disk, layout
from probe_feedback_packets import integral_table, model_table
from verify_packet import rational_tables


class PcmOrigin(unittest.TestCase):
    def test_all_new_entries_match_independent_fraction_recurrence(self):
        words,nxt,_=model_table(MEASURED_MODEL)
        rational_tables(MEASURED_MODEL['holds'],(words,nxt),MEASURED_MODEL['beta'],
                        MEASURED_MODEL['extent'],pcm_origin=0)

    def test_legacy_tables_keep_their_explicit_midpoint_meaning(self):
        for holds,extent in ((HOLDS,1.),(MEASURED_MODEL['holds'],.5)):
            default=integral_table(64,2,holds=holds,extent=extent)
            explicit=integral_table(64,2,holds=holds,extent=extent,pcm_origin=.5)
            self.assertTrue(np.array_equal(default[0],explicit[0]))
            self.assertTrue(np.array_equal(default[1],explicit[1]))
            rational_tables(holds,default,.5,extent)
        old=dict(MEASURED_MODEL)
        old.pop('pcm_origin')
        self.assertEqual(min(layout(bytes(256),old)[3].values()),0x8400)

    def test_zero_origin_retains_old_decoder_addresses_and_full_capacity(self):
        old=dict(MEASURED_MODEL)
        old.pop('pcm_origin')
        legacy=layout(bytes(MAX_PACKED_BYTES),old)
        fixed=layout(bytes(MAX_PACKED_BYTES),MEASURED_MODEL)
        self.assertEqual(min(fixed[3].values()),0x8380)
        self.assertEqual((fixed[5],fixed[6],fixed[7]),(legacy[5],legacy[6],legacy[7]))
        self.assertEqual(sum(s['bytes'] for s in fixed[8]),MAX_PACKED_BYTES)
        self.assertEqual(len(fixed[2]),18)

    def test_maximum_filler_and_chain_loader_fit_reclaimed_padding(self):
        packed=bytes(MAX_PACKED_BYTES)
        storage=dict(lower=118,upper=146,audio=[178,242,306,370,434,498,535])
        chain=dict(controller_disk=257,controller_sectors=8,volume=1,next_slot=1)
        root=Path(__file__).resolve().parents[1]/'.tmp'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='pcm-origin-') as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(root.resolve()))
            _,meta=build_disk(packed,Path(temporary),MEASURED_MODEL,
                             idle_pairs=1530,idle_pad=260,chain=chain,storage=storage)
            self.assertLessEqual(meta['player_labels']['startup_end'],0x8380)
            self.assertEqual(meta['ordinary_tstates'],423)
            self.assertEqual(meta['memory']['adpcm_bytes'],93440)
            self.assertEqual(meta['memory']['total_ram_bytes'],131072)

    def test_invalid_grid_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            integral_table(64,2,pcm_origin=.25)


if __name__=='__main__':unittest.main()
