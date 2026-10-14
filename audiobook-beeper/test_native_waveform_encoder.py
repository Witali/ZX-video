"""Whole-loop C parity against the untouched Python search and guard."""
import hashlib
import time
import unittest
import tempfile
from pathlib import Path

import numpy as np

from build_pdm import CPU_CLOCK
from direct_player import HOLDS
from ima_codec import decode, require_unclipped
from ima_waveform_encoder import WaveformModel, encode_waveform
from native_waveform_encoder import encode_waveform_native,write_workset,execute_workset
from probe_feedback_packets import integral_table


def fixture(values, boundary=False):
    source = np.r_[np.asarray(values,dtype=np.uint8),np.full(128,128,dtype=np.uint8)]
    holds = np.tile(HOLDS,(len(source),1)).astype(float)
    holds[:,7] += 26
    if boundary:
        holds[127,14] += 243
        holds[511,14] += 14
    holds *= CPU_CLOCK/3584000
    edges = np.r_[0,np.cumsum(holds.ravel())]
    count = len(source)-128
    unique, ids = np.unique(holds[:count],axis=0,return_inverse=True)
    model_holds = HOLDS.copy(); model_holds[7] += 26
    words,nxt,_ = integral_table(64,2,holds=model_holds,beta=.5,extent=.5,pcm_origin=0)
    signed = (((words.ravel()[:,None]>>np.arange(15,-1,-1))&1).astype(float)*2-1)
    analog = WaveformModel(); features=[]
    for row in unique:
        a,b,l,r = analog.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(CPU_CLOCK/8000)))
    queries = ((edges[:-1]+edges[1:])/2).reshape(-1,16)[:count]
    desired = analog.reference(source,np.rint(queries*80)/80)
    return source,desired,features,ids,nxt


class CompleteNativeWaveformTests(unittest.TestCase):
    def check_parity(self, values, boundary=False):
        args = fixture(values,boundary)
        py = encode_waveform(*args,width=32,block_size=128,commit_size=64,backend='native')
        statistics={}
        native = encode_waveform_native(*args,statistics=statistics)
        self.assertEqual(py,native)
        pcm,indices = decode(native)
        self.assertEqual((int(pcm[-1]),int(indices[-1])),(0,0))
        self.assertEqual(require_unclipped(native)['saturation_events'],0)
        self.assertEqual(statistics['backend'],'complete-c')
        self.assertGreater(statistics['search_iterations'],0)

    def test_silence_and_exact_zero_guard(self):
        self.check_parity(np.full(512,128,dtype=np.uint8))

    def test_quiet_tone_and_nonordinary_holds(self):
        self.check_parity(np.rint(128+4*np.sin(2*np.pi*997*np.arange(768)/8000)),True)

    def test_steps_preserve_prefix_and_guard(self):
        self.check_parity(np.where((np.arange(1024)//256)%2,220,36),True)

    def test_fixed_random_high_entropy_source(self):
        self.check_parity(np.random.default_rng(714).integers(16,240,512,dtype=np.uint8))

    def test_unsupported_options_fail_explicitly(self):
        args=fixture(np.full(128,128,dtype=np.uint8))
        for options in ({'history_bins':100},{'allowed_codes':np.arange(0,16,2)},
                        {'allowed_codes':np.arange(15,-1,-1)}, {'level_bounds':(0,63)},
                        {'allowed_codes':np.arange(16,dtype=float)},
                        {'width':16},{'block_size':32},{'commit_size':129},
                        {'regularization':float('nan')},{'backend':'numpy'}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                encode_waveform_native(*args,**options)

    def test_array_shapes_and_state_bounds_fail_before_native(self):
        args=list(fixture(np.full(128,128,dtype=np.uint8)))
        changed=args.copy(); changed[4]=args[4].copy(); changed[4][0,0]=32
        with self.assertRaises(ValueError):encode_waveform_native(*changed)
        changed=args.copy(); changed[3]=args[3].copy(); changed[3][0]=len(args[2])
        with self.assertRaises(ValueError):encode_waveform_native(*changed)
        changed=args.copy(); changed[0]=args[0].copy(); changed[0][-1]=127
        with self.assertRaises(ValueError):encode_waveform_native(*changed)
        changed=args.copy(); changed[1]=args[1][:-1]
        with self.assertRaises(ValueError):encode_waveform_native(*changed)

    def test_standalone_program_exact_bytes_and_bad_workset(self):
        args=fixture(np.rint(128+36*np.sin(2*np.pi*440*np.arange(256)/8000)))
        expected=encode_waveform(*args,width=32,block_size=128,commit_size=64,backend='native')
        scratch=Path(__file__).resolve().parent.parent/'.tmp/native-waveform-tests'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root=Path(temporary);workset=root/'input.bin';output=root/'звук.ima'
            write_workset(workset,*args);statistics={}
            actual=execute_workset(workset,output,statistics)
            self.assertEqual(actual,expected)
            self.assertFalse(statistics['child_python_runtime'])
            self.assertEqual(statistics['backend'],'standalone-c')
            workset.write_bytes(b'bad header')
            with self.assertRaises(RuntimeError):execute_workset(workset,output)


if __name__=='__main__':
    unittest.main()
