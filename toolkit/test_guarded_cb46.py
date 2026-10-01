"""Generic profile selection, CPU-budget fallback and fixed-memory planning."""
import unittest
from unittest.mock import patch

import numpy as np

import guarded_cb46 as guarded
from convert_cb41 import pack_blocks,plan_volumes,video_encoder
from dynamic_row_dictionary import decode_check
from lzsa2_oracle import encode
from test_generic_cell_codebook import frame


class LiteralCodec:
    def __init__(self):self.calls=0
    def encode_verified(self,raw,cached,cache):
        self.calls+=1
        return encode(raw,[])


class GuardedCB46Tests(unittest.TestCase):
    def fixture(self):
        frames=np.stack([frame([0],1)]*6)
        frames[2:4,3936]=2;frames[4:6,3936]=3
        base=guarded.representation(frames,2,6)
        codec=LiteralCodec()
        stream,blocks=pack_blocks(base['raw'],codec,None)
        return frames,base,codec,stream,blocks

    def test_all_representations_keep_defaults_and_dynamic_rows(self):
        self.assertEqual(video_encoder().__module__,'generic_cell_codebook')
        self.assertEqual(video_encoder(True).__module__,'dynamic_row_dictionary')
        self.assertEqual(video_encoder(True,True).__module__,'front_cell_reuse')
        frames=np.stack([frame(range(250),7),frame(range(250,500),71),frame(range(375,625),7)])
        for lo,hi in ((0,1),(0,3),(1,3)):
            result=video_encoder(guarded_cb46=True)(frames,lo,hi)
            self.assertEqual(result['raw'][:4],b'CB46')
            self.assertTrue(decode_check(result['raw'],frames,lo,hi,result['rows'])['both_screens_exact'])

    def test_real_decoder_saving_and_unchanged_fallback(self):
        frames,base,codec,stream,blocks=self.fixture()
        out=guarded.select(base['raw'],stream,blocks,base['rows'],frames,2,6,codec,None)
        self.assertTrue(out['report']['selected'])
        self.assertEqual(out['report']['removed_attribute_writes'],4)
        self.assertLess(out['report']['decoder_tstates_after'],out['report']['decoder_tstates_before'])
        self.assertEqual(out['report']['rgb_proof']['visible_pixel_changes'],0)
        # Running again with no redundant writes must keep the supplied stream.
        calls=codec.calls
        again=guarded.select(out['raw'],out['stream'],out['blocks'],base['rows'],out['states'],2,6,codec,None)
        self.assertFalse(again['report']['selected'])
        self.assertEqual(again['stream'],out['stream'])
        self.assertEqual(codec.calls,calls)

    def test_failed_cpu_budget_restores_original_packets(self):
        frames,base,codec,stream,blocks=self.fixture()
        def reject(payload,raw,bytes_limit,cpu_limit,*args,**kwargs):
            return payload,dict(tstates=cpu_limit+1),dict(budget_met=False)
        with patch('fit_lzsa2_cpu_budget.fit',side_effect=reject):
            out=guarded.select(base['raw'],stream,blocks,base['rows'],frames,2,6,codec,None)
        self.assertFalse(out['report']['selected'])
        self.assertEqual(out['raw'],base['raw']);self.assertEqual(out['stream'],stream)
        np.testing.assert_array_equal(out['states'],frames)
        self.assertEqual(len(out['report']['rounds']),2)

    def test_fixed_audio_capacity_drives_partition(self):
        frames=np.stack([frame([0])]*10)
        def sound(audio,lo,hi,labels,**kwargs):return bytes([hi-lo]),dict(resident_fits=True)
        def fixed(data,labels):return dict(resident_fits=data[0]<=3)
        with patch('convert_cb41.audio_size',side_effect=sound),patch.object(guarded,'audio_fits',side_effect=fixed), \
                patch('convert_cb41.pack_blocks',return_value=(bytes(10),[])):
            parts,_=plan_volumes(frames,[],{},None,None,10,dynamic_rows=True,audio_banks=2,guarded_cb46=True)
            self.assertEqual(sum(p['end']-p['start'] for p in parts),10)
            self.assertTrue(all(p['end']-p['start']<=3 for p in parts))
            with self.assertRaisesRegex(ValueError,'resident audio'):
                plan_volumes(frames,[],{},None,None,10,volume_cuts=[10],audio_banks=2,guarded_cb46=True)

    def test_sector_cache_tail_collision_rejected(self):
        for end,expected in ((0xb900,True),(0xb901,False)):
            fake=dict(payload_segments=[dict(bank=2,address=0xb800,bytes=end-0xb800)],
                payload_bytes=17000,fixed_bytes=3000,banks=[6],ayh1_sha256='fixture')
            with patch('fixed_resident_audio.build',return_value=fake):
                self.assertEqual(guarded.audio_fits(b'',{})['resident_fits'],expected)


if __name__=='__main__':unittest.main()
