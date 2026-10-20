"""Exact online selector parity against the frozen C and Python total order."""
import ctypes
import hashlib
from pathlib import Path
import subprocess
import unittest

import numpy as np

import waveform_kernel


def library():
    root=Path(__file__).resolve().parent
    source=waveform_kernel.SOURCE+'\n#define NWF_SELECT_TEST 1\n'+(root/'native_waveform_encoder.c').read_text(encoding='utf-8')
    command=waveform_kernel._command()
    identity=hashlib.sha256((source+repr(command)).encode()).hexdigest()[:24]
    folder=root/'.native-cache'/('select-parity-'+identity);folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'kernel.dll'
    if not binary.exists():
        (folder/'kernel.c').write_text(source,encoding='utf-8',newline='\n')
        result=subprocess.run(command,cwd=folder,capture_output=True,creationflags=0x08000000)
        (folder/'build.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    loaded=ctypes.CDLL(str(binary))
    integers=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
    floats=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
    for name in ('waveform_select','native_waveform_select_probe'):
        function=getattr(loaded,name)
        function.argtypes=[integers,integers,floats,ctypes.c_size_t,ctypes.c_size_t,
                           integers,integers,ctypes.c_size_t,integers]
        function.restype=ctypes.c_size_t
    return loaded


class ExactOnlineSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.functions=library()

    def check(self,candidates,keys,score,width):
        candidates=np.ascontiguousarray(candidates,dtype=np.int64)
        keys=np.ascontiguousarray(keys,dtype=np.int64)
        score=np.ascontiguousarray(score,dtype=np.float64)
        capacity=1 << max(1,(2*max(1,len(keys))-1).bit_length())
        expected={}
        for candidate,key in zip(candidates,keys):
            rank=(score[candidate],int(candidate))
            if key not in expected or rank<expected[key]:expected[key]=rank
        wanted=[candidate for _,candidate in sorted(expected.values())[:width]]
        for name in ('waveform_select','native_waveform_select_probe'):
            table=np.full(capacity,-91,dtype=np.int64)
            values=np.full(capacity,-92,dtype=np.int64)
            output=np.full(width,-93,dtype=np.int64)
            used=getattr(self.functions,name)(candidates,keys,score,len(keys),width,table,values,capacity,output)
            self.assertEqual(output[:used].tolist(),wanted,name)
            self.assertTrue(np.all(output[used:]==-93),name)

    def test_random_duplicates_and_ties(self):
        rng=np.random.default_rng(20102026)
        for width in (1,2,16,32,64,65,128):
            for case in range(200):
                count=int(rng.integers(1,1025));size=count+37
                candidates=rng.choice(size,count,replace=False)
                keys=rng.integers(0,max(1,count//2),count,dtype=np.int64)
                score=rng.integers(-16,17,size).astype('f8')
                if case%2:score+=rng.random(size)*.125
                self.check(candidates,keys,score,width)

    def test_evicted_key_reappears_and_duplicate_improves(self):
        for width in (1,2,32,64):
            size=width*12;candidates=np.arange(size,dtype=np.int64)
            keys=np.arange(size,dtype=np.int64)%(width*2)
            for values in (np.arange(size,dtype='f8'),-np.arange(size,dtype='f8'),
                           np.tile(np.array([7.,1.,4.,0.,8.,-1.]),size//6+1)[:size]):
                self.check(candidates,keys,values,width)

    def test_zero_extremes_and_candidate_id_ties(self):
        values=np.array([0.,-0.,np.finfo('f8').tiny,-np.finfo('f8').tiny,
                         np.finfo('f8').max,-np.finfo('f8').max]*30)
        candidates=np.arange(len(values),dtype=np.int64)[::-1].copy()
        self.check(candidates,np.arange(len(values))%23,values,32)
        self.check(candidates,np.arange(len(values))%97,np.zeros(len(values)),64)

    def test_large_beam_uses_unchanged_fallback(self):
        rng=np.random.default_rng(8448)
        size=8192;candidates=rng.permutation(size)
        self.check(candidates,rng.integers(0,5000,size),rng.normal(size=size),4096)

    def test_empty_candidates(self):
        self.check(np.array([],dtype=np.int64),np.array([],dtype=np.int64),np.array([],dtype='f8'),32)


if __name__=='__main__':unittest.main()
