"""Build, verify, record and measure the independently bootable packet TRD."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
from assess_snr import FILTER,ratio
from build_pdm import RATE,reconstruct,write_wav
from ima_codec import decode,verification_wav
from packet_player import HERE,prepare
from pdm_player import CPU_CLOCK
from verify_packet import reference,intervals,native_check,fuse_check
from verify_pcm import save


def render(out,ffmpeg,native=False,reference_fn=reference,intervals_fn=intervals,loop=0):
    meta=json.loads((out/'player.json').read_bytes())
    packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    pcm,indices,levels,bits=reference_fn(packed,cycles=loop+1);n=meta.get('outputs_per_cycle',len(pcm)*16)
    bits=bits[loop*n:(loop+1)*n]
    times=(np.r_[0,np.cumsum(intervals_fn(meta))] if native else
           np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[loop*n:(loop+1)*n+1])
    times=times-times[0]
    with wave.open(str(out/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    filtered={}
    from verify_direct import expand_samples
    for name,values in [('packet',bits[:n]),('decoded',expand_samples(meta,levels)/256),('source',expand_samples(meta,source)/256)]:
        signal=reconstruct(values,times)
        result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                               '-af',FILTER,'-ar','44100','-f','f32le','-'],input=signal.astype('<f4').tobytes(),
                              capture_output=True,check=True)
        filtered[name]=np.frombuffer(result.stdout,'<f4').astype(float)
    def snr(a,b):
        ref=filtered[b][4410:-4410];actual=filtered[a][4410:-4410]
        return ratio(ref,actual-ref)
    if not native and loop==0:
        for key in ('packet','source'):write_wav(out/(key+'-bandlimited-preview.wav'),filtered[key])
    return dict(scope='Native timing model, no ULA' if native else 'Integrated actual Fuse output timing; not a physical speaker measurement',
                total_snr_db=snr('packet','source'),modulator_snr_db=snr('packet','decoded'),codec_snr_db=snr('decoded','source'),
                duration_seconds=float(times[-1]/CPU_CLOCK),filter=FILTER,excluded_edge_seconds=.1,
                alignment='reference follows actual sample boundaries; no fitted delay/gain or pitch correction')


def finish(out,ffmpeg,reference_fn=reference,intervals_fn=intervals):
    native=json.loads((out/'native.json').read_bytes());fuse=json.loads((out/'fuse.json').read_bytes())
    assert native['complete'] and fuse['complete']
    packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes());pcm,indices=decode(packed)
    blocks=0
    for start in range(0,len(packed),30000):
        chunk=packed[start:start+30000];predictor=int(pcm[2*start-1]) if start else 0
        index=int(indices[2*start-1]) if start else 0
        run=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','wav','-i','-','-f','s16le','-acodec','pcm_s16le','-'],
                           input=verification_wav(chunk,predictor,index),capture_output=True,check=True)
        assert np.array_equal(np.frombuffer(run.stdout,'<i2'),np.r_[predictor,pcm[2*start:2*(start+len(chunk))]])
        blocks+=1
    recording=json.loads((out/'sound-128/report.json').read_bytes())
    assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    with wave.open(str(out/'sound-128/fuse-preview.wav'),'rb') as w:
        params=w.getparams();count=round(fuse['cycle_durations_seconds'][0]*params.framerate);raw=w.readframes(count)
    assert len(raw)==count*2
    with wave.open(str(out/'result-preview.wav'),'wb') as w:w.setparams(params);w.writeframes(raw)
    report=dict(date='2026-10-02',complete=True,preview_only=True,physical_hardware_tested=False,
                native=native,fuse=fuse,render=render(out,ffmpeg,False,reference_fn,intervals_fn),
                native_render=render(out,ffmpeg,True,reference_fn,intervals_fn),
                independent_ima=dict(decoder='FFmpeg IMA WAV',samples=len(pcm),blocks=blocks,every_sample_exact=True),
                delivery=dict(scope='Actual Fuse sound generator, first loop from ready; no added filter or gain',
                              wav_frames=count,sample_rate_hz=params.framerate,pcm_sha256=hashlib.sha256(raw).hexdigest()))
    archive=out/'producer-source';archive.mkdir(exist_ok=True);hashes={}
    for name in ('packet-player.asm','packet_player.py','verify_packet.py','build_packet.py','feedback_player.py',
                 'ima_beam.py','ima_codec.py','ima_player.py','pcm_player.py','pdm_player.py','record_pcm.py',
                 'build_pdm.py','assess_snr.py','probe_feedback_packets.py')+(
                 ('direct-player.asm','direct_player.py','verify_direct.py','build_direct.py','analyze_voice_jitter.py','precompensate_voice.py','probe_loop_phase.py') if reference_fn is not reference else ()):
        data=(HERE/name).read_bytes().replace(b'\r\n',b'\n');hashes[name]=hashlib.sha256(data).hexdigest()
        (archive/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    report['source_sha256_lf']=hashes
    save(out/'report.json',report);return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--finish-only',action='store_true');args=p.parse_args();out=args.output.resolve()
    if not args.finish_only:
        if out.exists() and any(out.iterdir()):p.error('output must be empty')
        prepare(out);meta=json.loads((out/'player.json').read_bytes())
        packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
        save(out/'native.json',native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed))
        save(out/'fuse.json',fuse_check(args.fuse,out,meta,packed))
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                        '--output',str(out/'sound-128'),'--machine','128'],check=True)
    report=finish(out,args.ffmpeg);print(json.dumps(report['render']),flush=True)


if __name__=='__main__':main()
