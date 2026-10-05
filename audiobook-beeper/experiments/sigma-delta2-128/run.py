"""Bounded exact SD2 experiment: one full pilot, one waveform search, own clocks.

The previous encoder-quality checkpoint remains paused. This independent
experiment reuses its unchanged prepared speech and reference IMA only.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from build_ima3_direct import build_verified
from convert_ima3_audio import stage
from quality_search import host_search
from sigma_delta2 import model, tables, independent_tables
from ima3_direct_player import build_disk
from probe_reconstruction_error import wav8, filtered
from build_pdm import reconstruct
from assess_snr import ratio
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def controls(source,ffmpeg,out):
    """No-IMA ideal-clock controls isolate state precision from CPU timing."""
    # Match the whole saved PCM; each control intentionally uses its declared
    # headroom gain, not a gain fitted from output audio.
    rows=[];times=np.arange(len(source)*16+1)*3546900/128000
    for name,scale,gain in [('q32-half',32,(1,2)),('q64-three-eighths',64,(3,8)),('q64-quarter',64,(1,4))]:
        spec=model(scale,gain);words,nxt,proof=tables(spec);independent_tables(spec)
        state=16;packets=[]
        for value in source:
            v=int(value)//2;packets.append(words[v,state]);state=int(nxt[v,state])
        bits=np.unpackbits(np.asarray(packets,dtype='>u2').view('u1'))
        original=filtered(reconstruct(np.repeat(source/256,16),times)*spec['output_gain'],ffmpeg)
        output=filtered(reconstruct(bits,times),ffmpeg)
        snr=ratio(original[4410:-4410],output[4410:-4410]-original[4410:-4410])
        row=dict(name=name,model=spec,ideal_pcm_snr_db=snr,certificate=proof,
                 scope='Complete-source ideal 128-kHz control, no IMA, no Z80/ULA proof')
        rows.append(row);print(json.dumps(dict(control=name,snr=snr)),flush=True)
    save(out/'ideal-controls.json',rows)
    return max(rows,key=lambda r:r['ideal_pcm_snr_db'])['model']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--resume',action='store_true')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    baseline=HERE.parent/'ima-3bit-overlap/qualified'
    source=wav8(baseline/'source-preview.wav')
    packed=gzip.decompress((baseline/'soundtrack.ima.gz').read_bytes())
    identity=dict(source=sha(baseline/'source-preview.wav'),packed=hashlib.sha256(packed).hexdigest(),
                  fuse=sha(a.fuse),ffmpeg=sha(Path(a.ffmpeg)),
                  producers={p.name:sha(p) for p in MODULES.iterdir() if p.suffix in ('.py','.asm')})
    if (out/'identity.json').exists():
        if not a.resume or json.loads((out/'identity.json').read_bytes())!=identity:
            raise ValueError('resume identity changed')
    else:save(out/'identity.json',identity)
    if (out/'ideal-controls.json').exists():
        rows=json.loads((out/'ideal-controls.json').read_bytes())
        spec=max(rows,key=lambda r:r['ideal_pcm_snr_db'])['model']
    else:spec=controls(source,a.ffmpeg,out)
    save(out/'model.json',spec)
    save(out/'state-certificate.json',tables(spec)[2])
    pilot=out/'pilot'
    old=stage(pilot,lambda path:build_verified(source,packed,path,a.fuse,a.ffmpeg,spec))
    encoded=out/'encode'
    host=stage(encoded,lambda path:host_search(pilot,path,256,.003,128,a.ffmpeg,'ima3'))
    refined=gzip.decompress((encoded/'soundtrack.ima.gz').read_bytes())
    candidate=out/'candidate'
    new=stage(candidate,lambda path:build_verified(source,refined,path,a.fuse,a.ffmpeg,spec))
    valid=[(path,r) for path,r in ((pilot,old),(candidate,new)) if r['quality']['speed_within_two_percent']]
    if not valid:raise RuntimeError('128-kHz candidate failed the required +/-2% speed')
    selected,report=max(valid,key=lambda pair:pair[1]['quality']['minimum_snr_db'])
    capture=out/'sound-128'
    def record(path):
        subprocess.run([sys.executable,str(MODULES/'record_pcm.py'),str(selected),
                        '--output',str(path),'--fuse',str(a.fuse),'--machine','128'],check=True)
        r=json.loads((path/'report.json').read_bytes())
        assert r['recording_complete'] and r['paging_latches_match'] and r['secondary_paging_unchanged']
        return r
    recording=stage(capture,record)
    result=dict(complete=True,model=spec,selected=selected.name,quality=report['quality'],
                pilot_quality=old['quality'],candidate_quality=new['quality'],host=host,
                recording=recording,trd_sha256=sha(selected/'audiobook-preview.trd'),
                source_pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                ordinary_tstates=427.375,ordinary_tstate_delta=0,
                physical_hardware_tested=False,previous_quality_study_resumed=False)
    save(out/'report.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
