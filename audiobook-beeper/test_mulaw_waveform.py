"""Independent recurrence and deterministic search backend checks."""
import unittest
import numpy as np
from g711_codec import decode_table
from mulaw_waveform_encoder import encode, close_guard, pulse_tables
from verify_mulaw import reference

class WaveformMuLaw(unittest.TestCase):
    def test_backends_match_and_both_loops_close(self):
        pcm=np.zeros(384,dtype='<i2')
        pcm[:256]=np.rint(12000*np.sin(np.arange(256)*.071)).astype('<i2')
        # Vary holds to expose accidental uniform-clock assumptions.
        holds=np.resize(np.array([53,59,53,61,56,55,55,58]),len(pcm)*8)
        times=np.r_[0,np.cumsum(np.r_[holds,np.roll(holds,3)])]
        a=encode(pcm,times,width=4,horizon=12,commit=4,backend='numpy')
        b=encode(pcm,times,width=4,horizon=12,commit=4,backend='native')
        self.assertEqual(a,b)
        _,bits,errors=reference(a)
        np.testing.assert_array_equal(bits[:len(pcm)*8],bits[len(pcm)*8:len(pcm)*16])
        self.assertEqual(errors[len(pcm)*8-1],32768)
        self.assertEqual(len(a),len(pcm))

    def test_all_fast_transitions_against_cumulative_area(self):
        levels=decode_table('mulaw').astype(np.int64)+32768
        words,nxt=pulse_tables(levels)
        for q in range(0,65536,32):
            area=q+levels[:,None]*np.arange(9)
            expected=np.diff(area//65536,axis=1)@(1<<np.arange(8))
            np.testing.assert_array_equal(words[q>>5],expected)
            np.testing.assert_array_equal(nxt[q>>5],area[:,-1]&65535)

    def test_guard_covers_every_reachable_residue_with_small_levels(self):
        levels=decode_table('mulaw').astype(np.int64)+32768
        # One arbitrary seed represents the preceding audio. Check the
        # correction separately against the integer accumulator identity.
        for error in range(0,65536,32):
            data=np.full(128,255,dtype='u1')
            # close_guard also checks the complete-stream seed; construct
            # a prefix having this exact residue using all ordinary codes.
            prefix=[];remaining=((error-32768)//8+4096)%8192-4096
            lookup={int(v)-32768:i for i,v in enumerate(levels)}
            if remaining%8:
                value=132 if remaining>0 else -132;prefix.append(lookup[value]);remaining-=value
            while remaining:
                value=min(120,abs(remaining))*(1 if remaining>0 else -1)
                prefix.append(lookup[value]);remaining-=value
            data=np.r_[np.array(prefix,dtype='u1'),data]
            close_guard(data,error,levels)
            self.assertTrue(np.max(abs(levels[data[-64:]]-32768))<=132)
            self.assertEqual((32768+8*int(levels[data].sum()))%65536,32768)

if __name__=='__main__':unittest.main()
