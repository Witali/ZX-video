"""Verify the saved SD2 search with feedback initialization in the silent tail.

Reuse the completed host encoding; never silently resume an old producer
identity after source changes. This is a new independently verified disk.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from build_ima3_direct import build_verified
from probe_reconstruction_error import wav8
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args()
    source=wav8(a.run/'pilot/source-preview.wav')
    packed=gzip.decompress((a.run/'encode/soundtrack.ima.gz').read_bytes())
    meta=json.loads((a.run/'candidate/player.json').read_bytes())
    assert hashlib.sha256(packed).hexdigest()==meta['packed_sha256']
    spec=dict(meta['model'],reset_feedback_in_guard=True)
    report=build_verified(source,packed,a.output,a.fuse,a.ffmpeg,spec)
    save(a.output/'repair-input.json',dict(
        input_pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
        input_ima_sha256=hashlib.sha256(packed).hexdigest(),model=spec,
        note='New full verification, reusing existing encoded data; no repeated search')))
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
