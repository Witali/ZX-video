"""Authenticate all saved evidence and rebuild the audition disk byte for byte.

--verify also repeats complete native/cold-Fuse two-loop checks. The archival
series proof separately covers independent cold boot, reload and END OF AUDIO.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[1]),str(HERE.parents[2]/'toolkit')]
from audit import read
from direct_player import build_disk
from convert_audio import validate
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',type=Path,default=HERE.parents[2],help='Main checkout containing local Git LFS objects')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--verify',action='store_true')
    p.add_argument('--ffmpeg')
    p.add_argument('--fuse',type=Path)
    a=p.parse_args()
    archive=HERE/'evidence'
    manifest=json.loads(read(archive/'manifest.json',a.repository))
    for name,record in manifest['files'].items():
        data=read(archive/name,a.repository)
        assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'],name
    source=archive/'quiet-fixed'
    old=json.loads(read(source/'player.json',a.repository))
    packed=gzip.decompress(read(source/'soundtrack.ima.gz',a.repository))
    a.output.mkdir(parents=True,exist_ok=False)
    disk,meta=build_disk(packed,a.output/'assembly',old['model'],old['hot_indices'],
        old['loop_idle_pairs'],old['loop_idle_pad_tstates'])
    expected=json.loads(read(archive/'report.json',a.repository))['audition_trd_sha256']
    assert hashlib.sha256(disk).hexdigest()==expected
    assert meta['binary_sha256']==old['binary_sha256']
    meta['compensated_reference_rate_hz']=8000
    (a.output/'audiobook-preview.trd').write_bytes(disk)
    save(a.output/'player.json',meta)
    for name in ('source-preview.wav','soundtrack.ima.gz'):
        (a.output/name).write_bytes(read(source/name,a.repository))
    if a.verify:
        assert a.ffmpeg and a.fuse,'Full verification requires FFmpeg and Fuse'
        result=validate(a.output,a.fuse,a.ffmpeg)
        assert result['speed_within_two_percent']
        assert not result['snr_at_least_20_db'],'This excerpt remains an explicit quality preview'
    print(json.dumps(dict(evidence_authenticated=True,rebuilt_byte_exact=True,
        native_and_cold_fuse_reverified=a.verify,trd_sha256=expected)))


if __name__=='__main__':main()
