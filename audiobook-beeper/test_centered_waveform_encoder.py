"""Opt-in midpoint lookup: exhaustive bounds and independent search parity."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from build_pdm import CPU_CLOCK
from direct_player import HOLDS
from ima_codec import decode,require_unclipped
from ima_waveform_encoder import WaveformModel,encode_waveform
from centered_waveform_reference import encode_waveform_reference
from native_waveform_encoder import (encode_waveform_native,quantize_pcm_levels,
                                     write_workset,execute_workset)
from probe_feedback_packets import integral_table


def fixture(values,boundary=False,pcm_origin=.5):
    source=np.r_[np.asarray(values,dtype=np.uint8),np.full(128,128,dtype=np.uint8)]
    holds=np.tile(HOLDS,(len(source),1)).astype(float);holds[:,7]+=26
    if boundary:holds[127,14]+=243;holds[511,14]+=14
    holds*=CPU_CLOCK/3584000;edges=np.r_[0,np.cumsum(holds.ravel())]
    count=len(source)-128;unique,ids=np.unique(holds[:count],axis=0,return_inverse=True)
    weighted=HOLDS.copy();weighted[7]+=26
    words,nxt,_=integral_table(64,2,holds=weighted,beta=.5,extent=1.,pcm_origin=pcm_origin)
    signed=(((words.ravel()[:,None]>>np.arange(15,-1,-1))&1).astype(float)*2-1)
    analog=WaveformModel();features=[]
    for row in unique:
        a,b,l,r=analog.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(CPU_CLOCK/8000)))
    queries=((edges[:-1]+edges[1:])/2).reshape(-1,16)[:count]
    desired=analog.reference(source,np.rint(queries*80)/80)
    return source,desired,features,ids,nxt


class CenteredWaveformTests(unittest.TestCase):
    def test_every_signed_pcm16_value_and_ixh_equivalence(self):
        values=np.arange(-32768,32768,dtype=np.int64)
        legacy=quantize_pcm_levels(values)
        self.assertTrue(np.array_equal(legacy,(values+32768)//1024))
        centered=quantize_pcm_levels(values,512)
        arithmetic=np.minimum(63,(values+32768+512)//1024)
        hardware=np.minimum(63,(((values+32768)>>8)+2)//4)
        self.assertTrue(np.array_equal(centered,arithmetic))
        self.assertTrue(np.array_equal(centered,hardware))
        self.assertEqual((int(centered[32767]),int(centered[32768])),(32,32))
        self.assertEqual((int(centered[0]),int(centered[-1])),(0,63))
        self.assertEqual(set(map(int,centered)),set(range(64)))

    def test_small_signal_tone_transient_and_random_parity(self):
        t=np.arange(768)/8000
        for values in (np.full(768,128),np.rint(128+2*np.sin(2*np.pi*997*t)),
                       np.where((np.arange(768)//256)%2,220,36),
                       np.random.default_rng(716).integers(0,256,768,dtype=np.uint8)):
            args=fixture(values,True)
            expected=encode_waveform_reference(*args,width=32,block_size=128,commit_size=64,
                                               backend='numpy',pcm_quantization_bias=512)
            statistics={};actual=encode_waveform_native(*args,pcm_quantization_bias=512,statistics=statistics)
            self.assertEqual(actual,expected)
            pcm,indices=decode(actual)
            self.assertEqual((int(pcm[-1]),int(indices[-1])),(0,0))
            self.assertEqual(require_unclipped(actual)['saturation_events'],0)
            self.assertEqual(statistics['pcm_quantization_bias'],512)

    def test_zero_bias_delegates_and_default_bytes_remain_original(self):
        args=fixture(np.rint(128+26*np.sin(2*np.pi*440*np.arange(256)/8000)))
        expected=encode_waveform(*args,width=32,block_size=128,commit_size=64,backend='native')
        statistics={};self.assertEqual(encode_waveform_native(*args,statistics=statistics),expected)
        self.assertEqual(encode_waveform_native(*args,pcm_quantization_bias=0),expected)
        self.assertNotIn('pcm_quantization_bias',statistics)
        with patch('centered_waveform_reference._original_encode',return_value=b'delegated') as original:
            self.assertEqual(encode_waveform_reference(*args,pcm_quantization_bias=0),b'delegated')
            original.assert_called_once()

    def test_actual_zero_origin_control_matches_independent_reference(self):
        values=np.rint(128+2*np.sin(2*np.pi*997*np.arange(768)/8000))
        args=fixture(values,True,pcm_origin=0)
        expected=encode_waveform_reference(*args,width=32,block_size=128,commit_size=64,
                                           backend='numpy',pcm_quantization_bias=512)
        actual=encode_waveform_native(*args,pcm_quantization_bias=512)
        self.assertEqual(actual,expected)
        pcm,indices=decode(actual)
        self.assertEqual((int(pcm[-1]),int(indices[-1])),(0,0))
        self.assertEqual(require_unclipped(actual)['saturation_events'],0)

    def test_workset_versions_standalone_unicode_and_invalid_bias(self):
        args=fixture(np.rint(128+35*np.sin(2*np.pi*3000*np.arange(256)/8000)))
        scratch=Path(__file__).resolve().parent.parent/'.tmp/centered-waveform-tests'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root=Path(temporary);v1=root/'floor.nwf';zero=root/'zero.nwf';v2=root/'центр.nwf';output=root/'звук.ima'
            write_workset(v1,*args);write_workset(zero,*args,pcm_quantization_bias=0)
            self.assertEqual(v1.read_bytes(),zero.read_bytes())
            write_workset(v2,*args,pcm_quantization_bias=512)
            one=v1.read_bytes();two=v2.read_bytes()
            self.assertEqual(one[:8],b'NWFB001\0');self.assertEqual(two[:8],b'NWFB002\0')
            self.assertEqual(two[8:56],one[8:56]);self.assertEqual(struct.unpack('<q',two[56:64])[0],512)
            self.assertEqual(two[64:],one[56:])
            stats={};self.assertEqual(execute_workset(v2,output,stats),encode_waveform_native(*args,pcm_quantization_bias=512))
            self.assertEqual(stats['pcm_quantization_bias'],512)
            stats={};self.assertEqual(execute_workset(v1,output,stats),encode_waveform_native(*args))
            self.assertNotIn('pcm_quantization_bias',stats)
            corrupted=bytearray(two);corrupted[56:64]=struct.pack('<q',256);v2.write_bytes(corrupted)
            with self.assertRaises(RuntimeError):execute_workset(v2,output)
            v2.write_bytes(two[:60])
            with self.assertRaises(RuntimeError):execute_workset(v2,output)

    def test_strict_bias_and_predictor_validation(self):
        args=fixture(np.full(128,128,dtype=np.uint8))
        for bias in (-512,1,256,1024,0.,512.,True,np.int64(512)):
            with self.subTest(bias=bias):
                with self.assertRaises(ValueError):encode_waveform_native(*args,pcm_quantization_bias=bias)
                with self.assertRaises(ValueError):encode_waveform_reference(*args,pcm_quantization_bias=bias)
                with self.assertRaises(ValueError):quantize_pcm_levels(np.array([0]),bias)
        for values in (np.array([-32769]),np.array([32768]),np.array([0.])):
            with self.assertRaises(ValueError):quantize_pcm_levels(values,512)


if __name__=='__main__':unittest.main()
