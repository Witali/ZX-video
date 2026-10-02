"""Rebuild unchanged IMA audio with uniform 73-T ordinary PDM slots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from build_ima import render
from ima_player import build_disk
from verify_ima import verify,intervals
from verify_pdm import save

HERE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=HERE/'ima-preview')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fuse',type=Path,required=True)
    parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):parser.error('output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    baseline=json.loads((args.input/'report.json').read_bytes())
    for name in ('player.json','soundtrack.ima.gz','output-times.u32.gz'):
        if sha((args.input/name).read_bytes())!=baseline['artifacts'][name]['sha256']:
            raise ValueError(f'baseline changed: {name}')
    oldmeta=json.loads((args.input/'player.json').read_bytes())
    packed=gzip.decompress((args.input/'soundtrack.ima.gz').read_bytes())
    disk,meta=build_disk(packed,oldmeta['initial_predictor'],oldmeta['initial_index'],
                         out/'assembly',uniform=True)
    (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    save(out/'player.json',meta)
    proof=verify(out,args.fuse)
    audio=render(out,packed,meta,args.ffmpeg)
    oldtimes=np.frombuffer(gzip.decompress((args.input/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    newtimes=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    ordinary=np.tile(np.array(intervals(meta))==73,2)
    timing={}
    for name,ts in (('before',oldtimes),('after',newtimes)):
        holds=np.diff(ts)
        timing[name]=dict(mean_hold_tstates=float(np.mean(holds)),std_hold_tstates=float(np.std(holds)),
                          ordinary_std_tstates=float(np.std(holds[ordinary])),
                          minimum_hold_tstates=int(np.min(holds)),maximum_hold_tstates=int(np.max(holds)))
    sources=('ima-uniform-player.asm','ima-player.asm','ima_player.py','ima_codec.py',
             'verify_ima.py','build_uniform_ima.py','test_ima_uniform.py','pack_ima.py')
    archive=out/'producer-source';archive.mkdir()
    hashes={}
    for name in sources:
        source=(HERE/name).read_bytes().replace(b'\r\n',b'\n');hashes[name]=sha(source)
        (archive/(name+'.gz')).write_bytes(gzip.compress(source,mtime=0))
    report=dict(date='2026-10-02',complete=True,preview_only=True,baseline_trd_sha256=baseline['verification']['fuse']['trd_sha256'],
                player=meta,verification=proof,render=audio,timing_comparison=timing,
                baseline_render=baseline['render'],same_packed_audio=True,same_pdm_bits_and_slot_counts=True,
                sources_sha256_lf=hashes,artifacts={f.relative_to(out).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
                for f in out.rglob('*') if f.is_file() and f.name not in ('report.json','fuse-stderr.txt')})
    save(out/'report.json',report)
    print(json.dumps(dict(render=audio,baseline_render=baseline['render'],timing=timing)),flush=True)


if __name__=='__main__':main()
