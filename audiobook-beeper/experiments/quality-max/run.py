"""Bounded quality follow-up: preserve all qualified fallbacks and timings."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;MODULES=HERE.parents[1]
sys.path.insert(0,str(MODULES))
from verify_pdm import save
from convert_ima3_audio import stage
from build_ima3_direct import build_verified,write_candidate
from convert_mulaw_audio import measure,optimize
from mulaw_player import build_disk
from probe_reconstruction_error import wav8
spec=importlib.util.spec_from_file_location('overlap_study',HERE.parent/'ima4-overlap/run.py')
overlap=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlap)

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy_flat(source,dest):
    dest.mkdir(parents=True,exist_ok=True)
    for path in source.iterdir():
        if path.is_file():shutil.copy2(path,dest/path.name)
    shutil.copytree(source/'assembly',dest/'assembly',dirs_exist_ok=True)

def record(selected,out,fuse):
    subprocess.run([sys.executable,str(MODULES/'record_pcm.py'),str(selected),'--fuse',str(fuse),
                    '--output',str(out)],check=True)
    proof=read(out/'report.json')
    assert proof['recording_complete'] and proof['paging_latches_match'] and proof['secondary_paging_unchanged']
    assert proof['source_trd_sha256']==sha(selected/'audiobook-preview.trd')

def mulaw(out,fuse,ffmpeg):
    old=HERE.parent/'mulaw-trd/qualified';control=out/'control'
    # Reuse full historical execution only after exact current rebuild.
    payload=(old/'soundtrack.mulaw').read_bytes();disk,meta=build_disk(payload,out/'rebuild')
    assert disk==(old/'audiobook-preview.trd').read_bytes()
    assert read(old/'native.json')['complete'] and read(old/'fuse.json')['cycles_verified']==2
    assert read(old/'fuse.json')['fuse_sha256']==sha(fuse)
    copy_flat(old,control)
    with wave.open(str(old/'source-preview.wav'),'rb') as w:pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2').copy()
    save(control/'quality.json',measure(control,meta,payload,pcm,ffmpeg))
    save(out/'reuse.json',dict(exact_rebuilt_trd_sha256=sha(old/'audiobook-preview.trd'),
        reused_native=sha(old/'native.json'),reused_fuse=sha(old/'fuse.json'),reused_clock=sha(old/'output-times.u32.gz')))
    best,candidates=optimize(control,out,pcm,fuse,ffmpeg)
    selected=out/'selected';copy_flat(Path(best['directory']),selected)
    record(selected,out/'recording',fuse)
    save(out/'report.json',dict(complete=True,selected=best,candidates=candidates,
        trd_sha256=sha(selected/'audiobook-preview.trd'),ordinary_tstates=432,hot_path_delta=0))

def ima3(out,host,fuse,ffmpeg):
    old=HERE.parent/'ima-quality/paused/speech3-verified';saved=old/'disk-encode-2'
    # Authenticate finished files independently of the interrupted sibling.
    for name,digest in read(saved/'stage-complete.json').items():assert sha(saved/name)==digest,name
    meta=read(saved/'player.json');packed=gzip.decompress((saved/'soundtrack.ima.gz').read_bytes())
    source=wav8(saved/'source-preview.wav')
    disk,_=write_candidate(out/'rebuild',packed,source,pairs=meta['loop_idle_pairs'],
                           pad=meta['loop_idle_pad_tstates'],model=meta['model'])
    assert disk==(saved/'audiobook-preview.trd').read_bytes()
    save(out/'reuse.json',dict(exact_rebuilt_trd_sha256=sha(saved/'audiobook-preview.trd'),
        old_stage_sha256=sha(saved/'stage-complete.json'),old_clock_sha256=sha(saved/'output-times.u32.gz')))
    folders={'previous':HERE.parent/'ima-3bit-overlap/qualified','cached-best':saved}
    for name,encoded in [('cached-first',old/'encode-1'),('third',host)]:
        b=gzip.decompress((encoded/'soundtrack.ima.gz').read_bytes())
        assert hashlib.sha256(b).hexdigest()==read(encoded/'report.json')['packed_sha256']
        folder=out/name
        stage(folder,lambda p:build_verified(source,b,p,fuse,ffmpeg,meta['model']))
        folders[name]=folder
    finish_ima(out,folders,fuse,ffmpeg,427.375)

def ima4(out,host,fuse,ffmpeg):
    packed=gzip.decompress((host/'soundtrack.ima.gz').read_bytes())
    assert hashlib.sha256(packed).hexdigest()==read(host/'report.json')['packed_sha256']
    stage(out/'third',lambda p:overlap.qualify(p,packed,fuse,ffmpeg))
    finish_ima(out,{'previous':overlap.CLOCK,'third':out/'third'},fuse,ffmpeg,423)

def finish_ima(out,folders,fuse,ffmpeg,cost):
    scores={name:overlap.stable_score(folder,out/'stable'/name,ffmpeg) for name,folder in folders.items()}
    eligible=[name for name,folder in folders.items() if read(folder/'quality.json')['speed_within_two_percent']]
    winner=max(eligible,key=lambda name:scores[name]['minimum_snr_db'])
    copy_flat(folders[winner],out/'selected');record(out/'selected',out/'recording',fuse)
    save(out/'report.json',dict(complete=True,selected=winner,scores=scores,
        legacy_scores={name:read(folder/'quality.json')['minimum_snr_db'] for name,folder in folders.items()},
        trd_sha256=sha(out/'selected/audiobook-preview.trd'),ordinary_tstates=cost,hot_path_delta=0))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',choices=('mulaw','ima3','ima4'),required=True)
    p.add_argument('--host',type=Path);p.add_argument('--fuse',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    identity=dict(stage=a.stage,fuse_sha256=sha(a.fuse),ffmpeg_sha256=sha(Path(a.ffmpeg)),
        host_report=read(a.host/'report.json') if a.host else None,
        producers={p.name:sha(p) for p in MODULES.glob('*.py')},
        assembly={p.name:sha(p) for p in MODULES.glob('*player.asm')})
    marker=a.output/'identity.json'
    if marker.exists():assert read(marker)==identity,'changed experiment identity'
    else:save(marker,identity)
    if a.stage=='mulaw':mulaw(a.output,a.fuse,a.ffmpeg)
    elif a.stage=='ima3':ima3(a.output,a.host,a.fuse,a.ffmpeg)
    else:ima4(a.output,a.host,a.fuse,a.ffmpeg)
if __name__=='__main__':main()
