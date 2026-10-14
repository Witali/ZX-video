"""Complete integer trellis parity; reference ima_beam.py is unchanged."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from ima_beam import encode
from ima_codec import decode,require_unclipped
from native_ima_encoder import encode_pcm_native,execute_pcm_file


class NativePcmEncoderTests(unittest.TestCase):
    def parity(self,source,**options):
        expected=encode(source,**options);statistics={}
        actual=encode_pcm_native(source,statistics=statistics,**options)
        self.assertEqual(expected,actual)
        predictor=options.get('predictor',0);index=options.get('index',0)
        if len(source):
            pcm,indices=decode(actual,predictor,index)
            self.assertEqual((int(pcm[-1]),int(indices[-1])),
                             (statistics['final_predictor'],statistics['final_index']))
            guard=require_unclipped(actual,predictor,index)
            self.assertEqual(guard['raw_min'],statistics['raw_min'])
            self.assertEqual(guard['raw_max'],statistics['raw_max'])
        self.assertEqual(statistics['saturation_events'],0)
        self.assertFalse(statistics['blas_dependency'])

    def test_silence_tones_transients_and_random(self):
        n=512;t=np.arange(n)/8000
        for source in (np.full(n,128),np.rint(128+2*np.sin(2*np.pi*997*t)),
                       np.rint(128+96*np.sin(2*np.pi*3000*t)),
                       np.where((np.arange(n)//128)%2,220,36),
                       np.random.default_rng(715).integers(0,256,n)):
            with self.subTest(source=source[:8]):
                self.parity(np.r_[source,np.full(128,128)].astype(np.uint8))

    def test_extremes_and_partial_final_block_preserve_every_sample(self):
        self.parity(np.tile(np.array([0,255],dtype=np.uint8),97))
        self.parity(np.empty(0,dtype=np.uint8))

    def test_seeds_bounds_beams_and_block_lengths(self):
        source=np.random.default_rng(92).integers(0,256,194,dtype=np.uint8)
        for options in ({'predictor':1234,'index':35},
                        {'predictor':-321,'index':9,'predictor_bounds':(-20000,18000)},
                        {'width':1,'block_samples':2},
                        {'width':7,'block_samples':32},
                        {'width':32,'block_samples':128}):
            with self.subTest(options=options):self.parity(source,**options)

    def test_code_alphabets_and_exact_candidate_ties(self):
        source=np.r_[np.full(64,128),np.arange(64)+96].astype(np.uint8)
        for codes in (np.arange(0,16,2),np.arange(15,-1,-1),np.array([8,0]),np.array([0])):
            with self.subTest(codes=codes):self.parity(source,allowed_codes=codes)

    def test_invalid_input_and_no_unclipped_path(self):
        valid=np.full(128,128,dtype=np.uint8)
        for source in (valid[:-1],np.full((2,64),128,dtype=np.uint8),
                       valid.astype(float),np.array([-1,128]),np.array([128,256])):
            with self.subTest(source=np.shape(source)),self.assertRaises(ValueError):
                encode_pcm_native(source)
        for options in ({'width':0},{'block_samples':3},{'predictor':32768},
                        {'index':89},{'predictor_bounds':(-1,-2)},
                        {'allowed_codes':[0,0]},{'allowed_codes':[16]},
                        {'allowed_codes':[0.]},{'index':88,'predictor_bounds':(-1,1),'allowed_codes':[0]}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                encode_pcm_native(valid,**options)

    def test_standalone_unicode_paths_and_odd_source_rejection(self):
        source=np.rint(128+35*np.sin(2*np.pi*440*np.arange(512)/8000)).astype(np.uint8)
        expected=encode(source);scratch=Path(__file__).resolve().parent.parent/'.tmp/native-ima-tests'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root=Path(temporary);input_path=root/'источник.raw';output=root/'звук.ima'
            source.tofile(input_path);statistics={}
            self.assertEqual(execute_pcm_file(input_path,output,statistics),expected)
            self.assertFalse(statistics['child_python_runtime'])
            self.assertFalse(statistics['blas_dependency'])
            input_path.write_bytes(b'odd')
            with self.assertRaises(RuntimeError):execute_pcm_file(input_path,output)


if __name__=='__main__':unittest.main()
