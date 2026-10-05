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
        # Codec-only diagnostics retain their historical shared-clock basis.
        # Selection must also penalize timing error against the fixed source.
        period=CPU/8000;count=int(np.ceil(times[-1]/period))
        edges=np.r_[np.arange(count)*period,times[-1]]
        values=np.pad((pcm.astype(float)+32768)/65536,(0,max(0,count-len(pcm))),constant_values=.5)[:count]
        fixed=filter_signal(values,edges,ffmpeg,768000)
        cut=slice(4410,-4410)
        rows.append(dict(cycle=cycle+1,total_snr_db=ratio(ref[cut],actual[cut]-ref[cut]),
                         fixed_clock_snr_db=ratio(fixed[cut],actual[cut]-fixed[cut]),
                         codec_snr_db=ratio(ref[cut],decoded[cut]-ref[cut]),
                         modulator_snr_db=ratio(decoded[cut],actual[cut]-decoded[cut])))
        if cycle==0:
            write_wav(out/'reference-preview.wav',ref*.5)
            write_wav(out/'fixed-reference-preview.wav',fixed*.5)
            write_wav(out/'output-preview.wav',actual*.5)
    return dict(cycles=rows,integration_rate_hz=768000,filter=STABLE_FILTER,
                minimum_total_snr_db=min(r['total_snr_db'] for r in rows),
                minimum_fixed_clock_snr_db=min(r['fixed_clock_snr_db'] for r in rows),
                scope='Full real OUT timeline. Selection uses fixed_clock_snr_db against the fixed 8-kHz source. Historical total/codec/modulator diagnostics use observed sample boundaries. No gain/delay fitting; speed checked separately.',
                listening_gain=.5,physical_hardware_measured=False)


def qualify(out,payload,pcm,fuse,ffmpeg):
    """Execute a complete candidate; all PC estimates remain provisional."""
    out.mkdir(parents=True,exist_ok=True)
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.astype('<i2').tobytes())
    (out/'soundtrack.mulaw').write_bytes(payload)
    disk,meta=build_disk(payload,out/'assembly')
    save(out/'player.json',meta);(out/'audiobook-preview.trd').write_bytes(disk)
    print('Verifying mu-law candidate: '+str(out),flush=True)
    native=native_check(disk,meta,payload);save(out/'native.json',native)
    actual=fuse_check(fuse,out,meta,payload);save(out/'fuse.json',actual)
    quality=measure(out,meta,payload,pcm,ffmpeg);save(out/'quality.json',quality)
    return dict(complete=True,quality=quality,native=native,fuse=actual,
                trd_sha256=hashlib.sha256(disk).hexdigest())


def optimize(control,out,pcm,fuse,ffmpeg):
    from mulaw_waveform_encoder import encode as search, saved_timeline, timed_pcm, close_guard
    from g711_codec import decode_table
    timeline=saved_timeline(control);timeline-=timeline[0]
    candidates=[dict(directory=str(control),quality=json.loads((control/'quality.json').read_bytes()))]
    target=timed_pcm(pcm,timeline);target[-128:]=0
    compensated=np.frombuffer(encode(np.rint(target).astype('<i2'),'mulaw',ffmpeg),'u1').copy()
    levels=decode_table('mulaw').astype(np.int64)+32768
    close_guard(compensated,(32768+8*int(levels[compensated].sum()))&65535,levels)
    folder=out/'timing-control'
    result=qualify(folder,compensated.tobytes(),pcm,fuse,ffmpeg)
    candidates.append(dict(directory=str(folder),**result));save(out/'candidates.json',candidates)
    for width,horizon,weight in ((8,16,.1),(32,32,.3)):
        folder=out/f'waveform-{width}';folder.mkdir(parents=True,exist_ok=True)
        statistics={}
        payload=search(pcm,timeline,width=width,horizon=horizon,commit=8,regularization=weight,statistics=statistics)
        statistics.update(source_sha256=hashlib.sha256(pcm.astype('<i2').tobytes()).hexdigest(),
            clock_sha256=hashlib.sha256((control/'output-times.u32.gz').read_bytes()).hexdigest(),
            packed_sha256=hashlib.sha256(payload).hexdigest(),
            producer_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
                ('mulaw_waveform_encoder.py','ima_waveform_encoder.py','waveform_kernel.py','g711_codec.py')})
        save(folder/'search.json',statistics)
        result=qualify(folder,payload,pcm,fuse,ffmpeg)
        assert json.loads((folder/'player.json').read_bytes())['binary_sha256']==json.loads((control/'player.json').read_bytes())['binary_sha256']
        candidates.append(dict(directory=str(folder),**result))
        save(out/'candidates.json',candidates)
    return max(candidates,key=lambda row:row['quality']['minimum_fixed_clock_snr_db']),candidates


def convert(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    pcm,preparation=prepare(args.input,args.ffmpeg,args.duration,args.prepared_pcm)
    save(out/'preparation.json',preparation)
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.astype('<i2').tobytes())
    verify_tables(args.ffmpeg)
    payload=encode(pcm,'mulaw',args.ffmpeg)
    assert len(payload)==len(pcm)
    control=out/'control';initial=qualify(control,payload,pcm,args.fuse,args.ffmpeg)
    best=dict(directory=str(control),**initial);candidates=[best]
    if getattr(args,'quality','best')=='best' and np.any(pcm):
        best,candidates=optimize(control,out,pcm,args.fuse,args.ffmpeg)
    selected=Path(best['directory'])
    for path in selected.iterdir():
        if path.is_file():shutil.copy2(path,out/path.name)
    shutil.copytree(selected/'assembly',out/'assembly')
    native=json.loads((out/'native.json').read_bytes());actual=json.loads((out/'fuse.json').read_bytes())
    quality=best['quality'];disk=(out/'audiobook-preview.trd').read_bytes()
    recording=None
    if not args.no_recording:
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                        '--output',str(out/'recording')],check=True)
        recording=json.loads((out/'recording/report.json').read_bytes())
        assert recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    sources=['convert_mulaw_audio.py','mulaw_player.py','mulaw-player.asm','verify_mulaw.py','g711_codec.py',
             'record_pcm.py','build_pdm.py','assess_snr.py','verify_pdm.py','feedback_player.py','ima_player.py',
             'pcm_player.py','pdm_player.py','mulaw_waveform_encoder.py','ima_waveform_encoder.py','waveform_kernel.py']
    snapshots=out/'sources';snapshots.mkdir(exist_ok=True)
    for name in sources:shutil.copy2(HERE/name,snapshots/name)
    report=dict(complete=True,codec='G.711 mu-law',disks=1,repeat=True,
        prepared_seconds=len(pcm)/8000,retained_input_seconds=preparation['retained_input_samples']/8000,
        native=native,fuse=actual,quality=quality,recording=recording,
        selected=selected.name,candidates=candidates,quality_profile=getattr(args,'quality','best'),
        target_30_db_passed=quality['minimum_fixed_clock_snr_db']>=30,
        limitations=['First-order real-time control, not the PC-only second-order 128-kHz model',
                     'One resident prefix, looping; mu-law sequential volumes are not implemented',
                     'No physical Spectrum or sound-card-loopback test'],
        trd_sha256=hashlib.sha256(disk).hexdigest())
    save(out/'report.json',report)
    print(json.dumps(dict(complete=True,disk=str(out/'audiobook-preview.trd'),
        snr_db=quality['minimum_fixed_clock_snr_db'],speed_error_percent=actual['speed_error_percent'])),flush=True)
    return report


def main(argv=None, *, parents=()):
    p=argparse.ArgumentParser(description=__doc__,parents=list(parents),allow_abbrev=False)
    p.add_argument('input',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));p.add_argument('--fuse',required=True,type=Path)
    p.add_argument('--duration',type=float,help='initial seconds, bounded by resident capacity')
    p.add_argument('--quality',choices=('best','balanced'),default='best',
                   help='best: waveform-aware PC search with verified fallback; balanced: ordinary G.711 encoder')
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
