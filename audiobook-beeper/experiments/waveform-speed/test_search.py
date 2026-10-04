"""Exact accelerated-search regressions against the archived pre-change code."""
import gzip
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import numpy as np
import ima_waveform_encoder as current
import waveform_kernel
from probe_reconstruction_error import wav8

HERE=Path(__file__).resolve().parent


def baseline():
    module=types.ModuleType('waveform_speed_baseline')
    source=gzip.decompress((HERE/'baseline.py.gz').read_bytes())
    exec(compile(source,'archived-waveform-encoder.py','exec'),module.__dict__)
    return module


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel=waveform_kernel.workspace(1024,16,'native')
        cls.old=baseline()
        cls.meta,_,_,cls.nxt,_,cls.desired,cls.features,cls.ids=current.prepare(HERE/'pilot')
        cls.prior=wav8(HERE/'pilot/compensated-pcm.wav')

    def test_unique_selection_ties_and_collisions(self):
        rng=np.random.default_rng(917)
        for count in (1,7,129,8192):
            candidates=rng.permutation(count).astype(np.int64)
            for width in (1,7,64,1024):
                kernel=waveform_kernel.workspace(width,max(16,(count+width-1)//width),'native')
                for kind in ('equal','tied','close','random'):
                    keys=rng.integers(0,max(1,count//3),count,dtype=np.int64)
                    score=(np.zeros(count) if kind=='equal' else
                           rng.integers(0,10,count).astype(float) if kind=='tied' else
                           1+rng.random(count)*1e-14 if kind=='close' else rng.random(count))
                    order=np.lexsort((candidates,score[candidates],keys))
                    ordered=candidates[order]
                    ordered=ordered[np.r_[True,keys[order][1:]!=keys[order][:-1]]]
                    expected=ordered[np.lexsort((ordered,score[ordered]))[:width]]
                    with self.subTest(count=count,width=width,kind=kind):
                        np.testing.assert_array_equal(kernel.select(candidates,score,keys),expected)
                        np.testing.assert_array_equal(current._best_unique(candidates,score,keys,width),expected)

    def test_error_terms_preserve_float64_operations(self):
        rng=np.random.default_rng(41)
        for parents in (1,7,128):
            for branches in (8,16):
                kernel=waveform_kernel.workspace(parents,branches,'native')
                base=rng.normal(size=(parents,16));response=rng.normal(size=(256,16))
                words=rng.integers(0,256,parents*branches,dtype=np.int64)
                desired=rng.normal(size=16);weights=rng.random(16)
                parent=np.repeat(np.arange(parents),branches)
                error=base[parent]+response[words]-desired
                expected=error*error*weights
                actual=kernel.errors(base,response,words,desired,weights)
                np.testing.assert_array_equal(actual.view(np.uint64),expected.view(np.uint64))

    def test_complete_paths_overlap_history_and_alphabets(self):
        cases=[(192,32,64,32,0,np.arange(0,16,2), (4,123)),
               (194,17,128,64,0,None,None),
               (128,1,64,64,0,np.arange(0,16,2),None),
               (128,23,128,16,8,np.arange(0,16,2), (4,123)),
               (192,32,64,32,0,np.arange(14,-1,-2), (4,123))]
        for n,width,horizon,commit,history,codes,bounds in cases:
            source=np.r_[self.prior[:n],np.full(128,128,dtype='u1')]
            args=(source,self.desired[:n],self.features,self.ids[:n],self.nxt)
            options=dict(width=width,block_size=horizon,commit_size=commit,history_bins=history,
                         allowed_codes=codes,level_bounds=bounds,regularization=.03)
            expected=self.old.encode_waveform(*args,**options)
            for backend in ('numpy','native'):
                with self.subTest(n=n,width=width,commit=commit,history=history,backend=backend):
                    self.assertEqual(current.encode_waveform(*args,**options,backend=backend),expected)

    def test_unavailable_compiler_falls_back_without_a_download(self):
        with patch.object(waveform_kernel,'_attempted',True),patch.object(waveform_kernel,'_library',None):
            self.assertIsNone(waveform_kernel.workspace(32,8,'auto'))
            with self.assertRaises(RuntimeError):waveform_kernel.workspace(32,8,'native')

    def test_invalid_backend_and_width(self):
        with self.assertRaises(ValueError):waveform_kernel.workspace(32,8,'unknown')
        with self.assertRaises(ValueError):
            current.encode_waveform(np.zeros(128,dtype='u1'),None,[],[],self.nxt,width=0)


if __name__=='__main__':unittest.main(verbosity=2)
