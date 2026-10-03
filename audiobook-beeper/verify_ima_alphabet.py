"""Check optional IMA3 search without changing ordinary four-bit results."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from ima_beam import encode, code_alphabet
from ima_codec import decode, require_unclipped
from ima_waveform_encoder import encode_waveform, prepare
from probe_dense_codecs import encode3
from build_ima3_disk import compress
from verify_pcm import save


def historical(module, revision):
    data = subprocess.run(['git', 'show', f'{revision}:audiobook-beeper/{module}.py'],
                          capture_output=True, check=True).stdout
    namespace = {'__name__':'baseline_verification', '__file__':module+'.py'}
    exec(compile(data, module+'.py', 'exec'), namespace)
    return namespace


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline-ref', default='7de87fd')
    args = p.parse_args()
    _, _, _, nxt, source, desired, features, ids = prepare(args.pilot)
    previous = historical('ima_beam', args.baseline_ref)['encode']
    signals = [source[:4096], np.tile(np.arange(256, dtype='u1'), 4), np.full(128,128,dtype='u1')]
    hashes = []
    for x in signals:
        a, b = previous(x), encode(x)
        assert a == b
        hashes.append(hashlib.sha256(a).hexdigest())
    codes = np.arange(0,16,2)
    x = np.r_[source[:4096], np.full(128,128,dtype='u1')]
    packed = encode(x, allowed_codes=codes)
    other, expected = encode3(x, (-1,-1,2,6))
    assert packed == (other[::2]*2 | other[1::2]*32).astype('u1').tobytes()
    restored, indices = decode(packed)
    assert np.array_equal(restored, expected)
    assert (restored[-1], indices[-1]) == (0,0)
    assert len(compress(packed))*8 == len(x)*3
    seeds = [(32767,88),(-32768,88),(1234,37),(-3456,46),(1,0),(-1,0),(0,0)]
    for predictor, index in seeds:
        tail = encode(np.full(128,128,dtype='u1'), predictor=predictor,index=index,allowed_codes=codes)
        pcm, idx = decode(tail,predictor,index)
        require_unclipped(tail,predictor,index)
        assert (pcm[-1],idx[-1])==(0,0)
        assert not np.any(np.frombuffer(tail,'u1')&0x11)
    length = 512
    x = np.r_[source[:length],np.full(128,128,dtype='u1')]
    old = historical('ima_waveform_encoder', args.baseline_ref)['encode_waveform']
    baseline = old(x,desired[:length],features,ids[:length],nxt,width=16)
    actual = encode_waveform(x,desired[:length],features,ids[:length],nxt,width=16)
    assert actual == baseline
    subset = encode_waveform(x,desired[:length],features,ids[:length],nxt,width=16,allowed_codes=codes)
    assert not np.any(np.frombuffer(subset,'u1')&0x11)
    rejected = []
    for alphabet in ([],[-1,0],[16],[0,0],[0.,2.],[[0,2]]):
        try:
            code_alphabet(alphabet)
        except ValueError:
            rejected.append(alphabet)
        else:
            raise AssertionError(alphabet)
    report = dict(complete=True, baseline_ref=args.baseline_ref,
                  ordinary_pcm_search_byte_identical=True, ordinary_pcm_fixture_lengths=list(map(len,signals)),
                  ordinary_pcm_fixture_sha256=hashes, ordinary_waveform_search_byte_identical=True,
                  waveform_fixture_samples=len(x), restricted_matches_existing_encode3=True,
                  restricted_fixture_samples=len(restored), nonzero_guard_seeds_verified=seeds,
                  guard_exact_zero_and_subset=True, invalid_alphabets_rejected=rejected)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    save(args.output,report)
    print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
