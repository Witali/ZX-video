"""Bounded audio prefix -> G.711 mu-law -> independently bootable looping TRD."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import numpy as np
from assess_snr import FILTER, ratio
from build_pdm import reconstruct, write_wav
from g711_codec import encode, decode, verify_tables
from mulaw_player import CAPACITY, CPU, build_disk
from verify_mulaw import native_check, fuse_check, reference
from verify_pdm import save

HERE=Path(__file__).resolve().parent
STABLE_FILTER=','.join(part+':precision=f64' for part in FILTER.split(','))


def prepare(path, ffmpeg, duration=None, prepared=False):
    limit=CAPACITY-128
    if duration is not None:
        if not math.isfinite(duration) or duration<=0: raise ValueError('duration must be finite and positive')
        limit=min(limit,max(1,int(duration*8000)))
    if prepared:
        with wave.open(str(path),'rb') as w:
            if w.getnchannels()!=1 or w.getframerate()!=8000 or w.getsampwidth() not in (1,2):
                raise ValueError('prepared input must be mono PCM8 or PCM16 at 8000 Hz')
            width=w.getsampwidth(); raw=w.readframes(w.getnframes())
        pcm=np.frombuffer(raw,'<i2').copy() if width==2 else (np.frombuffer(raw,'u1').astype(np.int16)-128)*256
        if duration is not None or len(pcm)<8192 or len(pcm)>CAPACITY or len(pcm)%256 or np.any(pcm[-128:]):
            raise ValueError('prepared input needs 8192..capacity sector-aligned samples and 128 silent final samples; no --duration')
        info=dict(prepared_input=True,retained_input_samples=len(pcm)-128,fixed_gain=1.,edge_fade_samples=0,truncated=False)
    else:
        run=subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(path),'-map','0:a:0',
            '-t',str((limit+1)/8000),'-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,check=True)
        samples=np.frombuffer(run.stdout,'<f4').astype(float)
        if not len(samples) or not np.all(np.isfinite(samples)): raise ValueError('no finite decodable audio')
        truncated=len(samples)>limit; samples=samples[:limit]
        peak=float(np.max(abs(samples)));gain=(109/128)/peak if peak else 1.
        samples*=gain;fade=min(80,len(samples)//2)
        if fade:
            samples[:fade]*=np.linspace(0,1,fade);samples[-fade:]*=np.linspace(1,0,fade)
        length=max(8192,(len(samples)+128+255)//256*256)
        pcm=np.zeros(length,dtype='<i2');pcm[:len(samples)]=np.rint(samples*32768).astype('<i2')
        info=dict(prepared_input=False,retained_input_samples=len(samples),fixed_gain=gain,
                  original_peak=peak,edge_fade_samples=fade,truncated=truncated,
                  truncation_reason=('duration or resident RAM bound' if truncated else None))
    info.update(input=str(path.resolve()),prepared_samples=len(pcm),maximum_samples=CAPACITY,
                sample_rate_hz=8000,channels=1,reference_pcm_bits=16,stored_bits_per_sample=8,
                silence_guard_samples=128,source_sha256=hashlib.sha256(pcm.astype('<i2').tobytes()).hexdigest())
    return pcm,info


def filter_signal(values, times, ffmpeg, rate):
    signal=reconstruct(values,times,rate)
    run=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f64le','-ar',str(rate),'-ac','1','-i','-',
        '-af',STABLE_FILTER,'-ar','44100','-f','f64le','-'],input=signal.astype('<f8').tobytes(),capture_output=True,check=True)
    return np.frombuffer(run.stdout,'<f8')


def measure(out, meta, payload, pcm, ffmpeg):
    timeline=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    _,bits,_=reference(payload);n=len(payload)*8;rows=[]
    for cycle in range(2):
        times=timeline[cycle*n:(cycle+1)*n+1].copy();times-=times[0]
        ref=filter_signal((pcm.astype(float)+32768)/65536,times[::8],ffmpeg,768000)
        decoded=filter_signal((decode(payload,'mulaw').astype(float)+32768)/65536,times[::8],ffmpeg,768000)
        actual=filter_signal(bits[cycle*n:(cycle+1)*n],times,ffmpeg,768000)
        cut=slice(4410,-4410)
        rows.append(dict(cycle=cycle+1,total_snr_db=ratio(ref[cut],actual[cut]-ref[cut]),
                         codec_snr_db=ratio(ref[cut],decoded[cut]-ref[cut]),
                         modulator_snr_db=ratio(decoded[cut],actual[cut]-decoded[cut])))
        if cycle==0:
            write_wav(out/'reference-preview.wav',ref*.5)
            write_wav(out/'output-preview.wav',actual*.5)
    return dict(cycles=rows,integration_rate_hz=768000,filter=STABLE_FILTER,
                minimum_total_snr_db=min(r['total_snr_db'] for r in rows),
                scope='Full real OUT timeline; reference uses the same sample boundaries. Includes codec and modulation distortion; no gain/delay fitting. Speed is checked separately.',
                listening_gain=.5,physical_hardware_measured=False)


def convert(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    pcm,preparation=prepare(args.input,args.ffmpeg,args.duration,args.prepared_pcm)
    save(out/'preparation.json',preparation)
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.astype('<i2').tobytes())
    verify_tables(args.ffmpeg)
    payload=encode(pcm,'mulaw',args.ffmpeg)
    assert len(payload)==len(pcm)
    (out/'soundtrack.mulaw').write_bytes(payload)
    disk,meta=build_disk(payload,out/'assembly')
    save(out/'player.json',meta);(out/'audiobook-preview.trd').write_bytes(disk)
    print('Built mu-law TRD; verifying every decoded level and PDM output',flush=True)
    native=native_check(disk,meta,payload);save(out/'native.json',native)
    print('Native Z80 passed; checking two complete cold-Fuse loops',flush=True)
    actual=fuse_check(args.fuse,out,meta,payload);save(out/'fuse.json',actual)
    quality=measure(out,meta,payload,pcm,args.ffmpeg);save(out/'quality.json',quality)
    recording=None
    if not args.no_recording:
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                        '--output',str(out/'recording')],check=True)
        recording=json.loads((out/'recording/report.json').read_bytes())
        assert recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    sources=['convert_mulaw_audio.py','mulaw_player.py','mulaw-player.asm','verify_mulaw.py','g711_codec.py',
             'record_pcm.py','build_pdm.py','assess_snr.py','verify_pdm.py','feedback_player.py','ima_player.py',
             'pcm_player.py','pdm_player.py']
    snapshots=out/'sources';snapshots.mkdir(exist_ok=True)
    for name in sources:shutil.copy2(HERE/name,snapshots/name)
    report=dict(complete=True,codec='G.711 mu-law',disks=1,repeat=True,
        prepared_seconds=len(pcm)/8000,retained_input_seconds=preparation['retained_input_samples']/8000,
        native=native,fuse=actual,quality=quality,recording=recording,
        target_30_db_passed=quality['minimum_total_snr_db']>=30,
        limitations=['First-order real-time control, not the PC-only second-order 128-kHz model',
                     'One resident prefix, looping; mu-law sequential volumes are not implemented',
                     'No physical Spectrum or sound-card-loopback test'],
        trd_sha256=hashlib.sha256(disk).hexdigest())
    save(out/'report.json',report)
    print(json.dumps(dict(complete=True,disk=str(out/'audiobook-preview.trd'),
        snr_db=quality['minimum_total_snr_db'],speed_error_percent=actual['speed_error_percent'])),flush=True)
    return report


def main(argv=None, *, parents=()):
    p=argparse.ArgumentParser(description=__doc__,parents=list(parents),allow_abbrev=False)
    p.add_argument('input',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));p.add_argument('--fuse',required=True,type=Path)
    p.add_argument('--duration',type=float,help='initial seconds, bounded by resident capacity')
    p.add_argument('--prepared-pcm',action='store_true',help='retain exact aligned PCM8/PCM16 mono 8-kHz reference with final silent guard')
    p.add_argument('--no-recording',action='store_true',help='omit sound-generator capture; all native/cold-Fuse checks still run')
    args=p.parse_args(argv)
    if not args.ffmpeg:p.error('FFmpeg not found; supply --ffmpeg')
    if args.output.exists() and any(args.output.iterdir()):p.error('output must be empty')
    try:return convert(args)
    except Exception as error:
        if args.output.exists():save(args.output/'failure.json',dict(complete=False,error=str(error),type=type(error).__name__))
        raise


if __name__=='__main__':main()
