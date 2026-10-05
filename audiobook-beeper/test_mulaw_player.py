"""Format, native execution, RAM boundaries and public CLI regression checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

import numpy as np
import convert_audio
import convert_mulaw_audio
from mulaw_player import CAPACITY, layout, build_disk
from verify_mulaw import native_check


class MuLawPlayer(unittest.TestCase):
    def test_every_code_in_native_z80(self):
        payload=bytes(range(256))*32
        with tempfile.TemporaryDirectory() as tmp:
            disk,meta=build_disk(payload,Path(tmp)/'assembly')
            result=native_check(disk,meta,payload)
        self.assertTrue(result['every_decoded_level_and_error_exact'])
        self.assertEqual(result['bits_verified'],8192*16+1)

    def test_full_ram_boundaries(self):
        sections=layout(bytes(CAPACITY))
        ranges={}
        for s in sections:
            a=s['address']-0xc000;b=a+s['bytes']
            for old_a,old_b in ranges.get(s['bank'],[]):
                self.assertTrue(b<=old_a or a>=old_b)
            ranges.setdefault(s['bank'],[]).append((a,b))
        self.assertEqual(CAPACITY+2048+1024+6912,131072)
        self.assertEqual(ranges[2],[(2048,16384)])
        self.assertEqual(ranges[5],[(0,7168),(8192,16384)])
        self.assertEqual(ranges[7],[(6912,16384)])
        for bad in (b'',b'\xff',bytes(CAPACITY+256)):
            with self.assertRaises(ValueError):layout(bad)

    def test_prepared_pcm16_retains_low_bits(self):
        pcm=np.resize(np.array([-13,-1,0,1,13],dtype='<i2'),8192);pcm[-128:]=0
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.wav'
            with wave.open(str(path),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.tobytes())
            result,meta=convert_mulaw_audio.prepare(path,'unused',prepared=True)
            np.testing.assert_array_equal(result,pcm)
            self.assertEqual(meta['fixed_gain'],1)
            with self.assertRaises(ValueError):convert_mulaw_audio.prepare(path,'unused',1.,True)

    def test_public_aliases_and_ima_default(self):
        for codec in ('mulaw','ulaw'):
            with patch('convert_mulaw_audio.main',return_value='mu-law') as fn:
                self.assertEqual(convert_audio.main(['--codec',codec,'source.wav','--output','example']), 'mu-law')
                self.assertEqual(fn.call_args.args[0],['source.wav','--output','example'])
        with patch('convert_ima3_audio.main',return_value='ima3'):
            self.assertEqual(convert_audio.main(['source.wav','--output','example']),'ima3')


if __name__=='__main__':unittest.main()
