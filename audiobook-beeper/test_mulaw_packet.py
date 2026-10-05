"""Packet arithmetic, native instructions, compact RAM and public routing."""
import tempfile
import unittest
import gzip
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import convert_mulaw_audio
from mulaw_packet import MODEL, HOLDS, layout, build_disk, reference, intervals
from mulaw_packet_encoder import encode
from verify_mulaw_packet import rational_check, native_check


class MuLawPackets(unittest.TestCase):
    def test_all_transitions_against_exact_fractions(self):
        self.assertEqual(rational_check(MODEL)['exact_fraction_transitions'],8192)

    def test_all_codes_and_idle_block_boundary_in_native_z80(self):
        payload=bytes(range(256))*32
        for pairs,pad in ((0,0),(255,0),(256,35)):
            with self.subTest(pairs=pairs), tempfile.TemporaryDirectory() as tmp:
                disk,meta=build_disk(payload,Path(tmp),idle_pairs=pairs,idle_pad=pad)
                proof=native_check(disk,meta,payload)
                self.assertTrue(proof['memory_guards_passed'])
                self.assertEqual(proof['packet_feedback_checks'],len(payload)*2+1)
                self.assertEqual(proof['bits_verified'],(len(payload)*16+pairs*2)*2+1)
                self.assertEqual(len(intervals(meta)),meta['outputs_per_cycle'])

    def test_ram_and_repeat_contract(self):
        words,nxt,states,first,second,pointers,reserve,ids,rows,reset,regions=layout()
        self.assertLessEqual(len(states),16)
        self.assertTrue(all((p&63)==0 for p in first.values()))
        self.assertEqual(int(nxt[255,reset]),16)
        capacity=sum(size for _,_,size in regions)
        self.assertEqual(capacity,97024)
        self.assertEqual(capacity+reserve+6912+14592,131072)
        for bank,address,size in regions:
            self.assertEqual(address+size,65536)
            if bank==2:self.assertGreaterEqual(address-0x4000,pointers+512)
            if bank==7:self.assertGreaterEqual(address,0xdb00)
            if bank==5:self.assertGreaterEqual(address-0x8000,max(rows)+64)
        payload=bytes(range(256))*32
        bits,_=reference(payload,idle_pairs=256)
        count=len(payload)*16+512
        np.testing.assert_array_equal(bits[:count],bits[count:count*2])

    def test_waveform_backends_preserve_guard(self):
        pcm=np.zeros(256,dtype='<i2')
        pcm[:128]=np.rint(12000*np.sin(np.arange(128)*.071)).astype('<i2')
        times=np.r_[0,np.cumsum(np.tile(HOLDS,len(pcm)))]
        meta={'model':MODEL}
        a=encode(pcm,meta,times,width=4,horizon=8,commit=4,backend='numpy')
        b=encode(pcm,meta,times,width=4,horizon=8,commit=4,backend='native')
        self.assertEqual(a,b)
        self.assertEqual(a[-128:],bytes([255])*128)
        self.assertEqual(len(a),len(pcm))

    def test_public_rate_selection_preserves_64khz_control(self):
        for option,callee in (([], 'convert_mulaw_packet.convert'),
                              (['--pdm-rate','64000'],'convert_mulaw_audio.convert')):
            with tempfile.TemporaryDirectory() as tmp, patch(callee,return_value='selected') as fn:
                self.assertEqual(convert_mulaw_audio.main([
                    'input.wav','--output',str(Path(tmp)/'out'),
                    '--fuse','fuse.exe','--ffmpeg','ffmpeg.exe',*option]),'selected')
                self.assertEqual(fn.call_count,1)

    def test_silent_reference_has_no_infinite_snr_claim(self):
        from convert_mulaw_packet import score
        count=8192;pcm=np.zeros(count,dtype='<i2')
        times=np.r_[0,np.cumsum(np.tile(HOLDS,count*2))].astype('<u4')
        meta=dict(model=MODEL,loop_idle_pairs=0,outputs_per_cycle=count*16)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'output-times.u32.gz').write_bytes(gzip.compress(times.tobytes()))
            with patch('convert_mulaw_packet.filter_signal',return_value=np.zeros(44100)), \
                 patch('convert_mulaw_packet.write_wav'):
                result=score(out,meta,bytes([255])*count,pcm,'unused')
            self.assertIsNone(result['minimum_snr_db'])
            json.dumps(result,allow_nan=False)


if __name__=='__main__':unittest.main()
