"""Rebuild explicit series fixtures, then execute every resulting volume.

Set PYTHONPATH to audiobook-beeper and toolkit, as for the main converter.
The repeated recording and synthetic tail are regression fixtures, not a
claim to have converted a longer original recording.
"""
import argparse
import gzip
from pathlib import Path
import numpy as np
from ima3_series import build_volume,capacity_samples
from build_ima3_direct import build_verified
from probe_reconstruction_error import wav8
from verify_ima3_series import verify_series
from verify_pcm import save

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('case',choices=('reload','swap','capacity'))
p.add_argument('--output',type=Path,required=True)
p.add_argument('--fuse',type=Path,required=True)
p.add_argument('--ffmpeg',required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
base=Path(__file__).resolve().parent.parent/'ima-3bit-direct'
if a.case=='reload':
    groups=[[base,base]];identity=bytes(16)
elif a.case=='swap':
    short=base/'automatic-short-final'
    groups=[[short,short],[short]];identity=bytes(range(16))
else:
    n=capacity_samples();source=np.full(n,128,dtype='u1');original=wav8(base/'source-preview.wav')
    source[:len(original)]=original
    packed=gzip.decompress((base/'soundtrack.ima.gz').read_bytes())
    packed+=bytes(n//2-len(packed))
    build_verified(source,packed,out/'reference',a.fuse,a.ffmpeg)
    groups=[[out/'reference']];identity=bytes(range(32,48))
volumes=[]
for number,group in enumerate(groups,1):
    disk,meta=build_volume(group,out/f'volume-{number}',identity,number,len(groups))
    name=f'audio-{number:04d}.trd';(out/name).write_bytes(disk)
    volumes.append(dict(file=name,**meta))
save(out/'volumes.json',volumes)
verify_series(out,a.fuse,a.ffmpeg)
