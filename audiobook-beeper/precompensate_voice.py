"""Bounded offline timing compensation probe; original PCM stays the reference.

The pilot clock is data-dependent. A score on that old clock is only a host
estimate, never proof of a new disk's playback quality. Verify the newly encoded
disk independently and check both loop phases before accepting compensation.
"""
import argparse,gzip,hashlib,json,shutil,time,wave
from functools import partial
from pathlib import Path
import numpy as np
from direct_player import build_disk
from ima_beam import encode
from ima_codec import decode
from verify_direct import reference,intervals,sample_positions
from verify_packet import native_check,fuse_check
from verify_pcm import save
from analyze_voice_jitter import analyze


def compensate(source,times,radius=16,period=None):
    """Lanczos interpolation at actual hold centers, in original sample units."""
    n=len(source);period=times[-1]/n if period is None else period
    positions=(times[:-1]+times[1:])/(2*period)-.5
    centers=np.floor(positions).astype(np.int64)
    offsets=np.arange(-radius+1,radius+1)
    result=np.empty(n,dtype='u1')
    for start in range(0,n,8192):
        stop=min(n,start+8192)
        index=centers[start:stop,None]+offsets
        distance=positions[start:stop,None]-index
        weights=np.sinc(distance)*np.sinc(distance/radius)
        values=np.where((index>=0)&(index<n),source[np.clip(index,0,n-1)].astype(float)-128,0.)
        restored=(values*weights).sum(axis=1)/weights.sum(axis=1)
        result[start:stop]=np.clip(np.rint(restored+128),0,255).astype('u1')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--fuse',type=Path)
    a=p.parse_args();out=a.output.resolve();pilot=a.pilot.resolve()
    if out.exists() and any(out.iterdir()):p.error('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    meta=json.loads((pilot/'player.json').read_bytes())
    with wave.open(str(pilot/'source-preview.wav'),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,8000)
        source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    n=len(source)
    times=np.frombuffer(gzip.decompress((pilot/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[sample_positions(meta)]
    fixed_rate=8000 if meta.get('loop_idle_pairs',0) else None
    target=compensate(source,times,period=3546900/fixed_rate if fixed_rate else None)
    # The delivered source already has 128 silence samples. Keep its loop guard.
    assert np.all(source[-128:]==128)
    if not fixed_rate:target[-128:]=128
    with wave.open(str(out/'compensated-pcm.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(target.tobytes())
    started=time.monotonic();packed=encode(target)
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    disk,new_meta=build_disk(packed,out/'assembly',meta['model'],meta['hot_indices'],meta.get('loop_idle_pairs',0),meta.get('loop_idle_pad_tstates',0))
    if fixed_rate:new_meta['compensated_reference_rate_hz']=fixed_rate
    save(out/'player.json',new_meta);(out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    shutil.copy2(pilot/'source-preview.wav',out/'source-preview.wav')
    shutil.copy2(pilot/'output-times.u32.gz',out/'output-times.u32.gz')
    estimate=analyze(out,a.ffmpeg)
    (out/'voice-jitter.json').rename(out/'host-estimate.json')
    report=dict(scope=__doc__,pilot=str(pilot),original_source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                compensated_source_sha256=hashlib.sha256(target.tobytes()).hexdigest(),samples=n,
                interpolation='Lanczos radius 16 at actual hold centers',encoding_seconds=time.monotonic()-started,
                hot_indices_frozen_from_pilot=True,player_instruction_changes=False,native_tstate_delta=0,
                host_fixed_mean_clock_snr_db=estimate['fixed_mean_clock_total_snr_db'])
    save(out/'precompensation.json',report);print(json.dumps(report),flush=True)
    if a.fuse:
        ref=partial(reference,model=new_meta['model'],idle_pairs=new_meta.get('loop_idle_pairs',0))
        save(out/'native.json',native_check(disk,new_meta,packed,ref,intervals))
        save(out/'fuse.json',fuse_check(a.fuse,out,new_meta,packed,False,ref,intervals))
        actual=analyze(out,a.ffmpeg)
        second=analyze(out,a.ffmpeg,loop=1)
        report['actual_clock_snr_db']=[actual['fixed_mean_clock_total_snr_db'],second['fixed_mean_clock_total_snr_db']]
        report['both_loops_reach_20_db']=min(report['actual_clock_snr_db'])>=20
        save(out/'precompensation.json',report)
        print(json.dumps(dict(actual_clock_snr_db=report['actual_clock_snr_db'])),flush=True)


if __name__=='__main__':main()
