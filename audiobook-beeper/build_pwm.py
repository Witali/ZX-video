"""Build a standalone IMA-to-PWM TRD, verify it and render matched audio."""
import argparse,gzip,hashlib,json,subprocess,wave
from pathlib import Path

import numpy as np

from build_pdm import reconstruct,write_wav,RATE
from ima_player import build_disk,CPU_CLOCK
from verify_ima import reference as pdm_reference
from verify_pwm import reference,native_check,fuse_check
from verify_pdm import save

HERE=Path(__file__).resolve().parent
SOURCES=('ima-pwm-player.asm','ima_player.py','ima_codec.py','verify_pwm.py',
         'build_pwm.py','test_ima_pwm.py','pack_ima.py','record_pcm.py',
         'build_pdm.py','verify_pdm.py','verify_ima.py')


def sha(blob):return hashlib.sha256(blob).hexdigest()


def render(out,baseline,ffmpeg):
    packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    meta=json.loads((out/'player.json').read_bytes());pcm,_,holds=reference(packed,meta)
    times=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:len(holds)+1]
    bits=np.tile(np.array([1,0],dtype=np.uint8),len(holds)//2)
    pcm8=((pcm.astype(np.int32)+32768)>>8)/256
    signals={'pwm':reconstruct(bits,times),'reference':reconstruct(np.repeat(pcm8,4),times)}
    oldmeta=json.loads((baseline/'player.json').read_bytes())
    oldpacked=gzip.decompress((baseline/'soundtrack.ima.gz').read_bytes())
    if oldpacked!=packed:raise ValueError('comparison requires identical IMA bytes')
    _,_,_,oldbits,n=pdm_reference(oldpacked,oldmeta)
    oldtimes=np.frombuffer(gzip.decompress((baseline/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:n+1]
    signals['pdm']=reconstruct(oldbits[:n],oldtimes)
    filtered={}
    filt='highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2'
    for name,signal in signals.items():
        raw=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                            '-af',filt,'-ar','44100','-f','f32le','-'],
                           input=signal.astype('<f4').tobytes(),capture_output=True,check=True).stdout
        filtered[name]=np.frombuffer(raw,'<f4').astype(float)
    # PWM uses only64/226 of the full-scale AC span. Compensate this fixed
    # transfer slope for comparison, not by individually normalizing peaks.
    filtered['pwm']*=226/64
    common_gain=min(1.,.9/max(float(np.max(abs(s))) for s in filtered.values()))
    for name in ('pwm','pdm'):write_wav(out/f'{name}-bandlimited-preview.wav',filtered[name]*common_gain)
    a=filtered['reference'][4410:-4410];b=filtered['pwm'][4410:-4410]
    prior=json.loads((baseline/'report.json').read_bytes())['render']
    return dict(filter=filt,scope='Measured Fuse edge times, integrated port holds; identical IMA bytes; no speaker or RC model',
                same_filter=True,common_gain=common_gain,pwm_fixed_ac_gain=226/64,
                pwm_uncompensated_ac_gain_db=float(20*np.log10(64/226)),
                pwm_snr_db=float(10*np.log10(np.mean(a*a)/np.mean((a-b)**2))),
                pwm_correlation=float(np.corrcoef(a,b)[0,1]),pdm_saved_snr_db=prior['pdm_snr_db'],
                time_alignment='same sample boundaries; no fitted delay, equalization or pitch correction',
                excluded_edge_seconds=.1,pwm_duration_seconds=float(times[-1]/CPU_CLOCK),
                pdm_duration_seconds=float(oldtimes[-1]/CPU_CLOCK))


def finish(out,baseline,ffmpeg):
    metrics=render(out,baseline,ffmpeg)
    proof=json.loads((out/'verification.json').read_bytes())
    capture=out/'sound-128/fuse-preview.wav'
    delivery=None
    if capture.exists():
        with wave.open(str(capture),'rb') as wav:
            count=round(proof['fuse']['cycle_durations_seconds'][0]*wav.getframerate())
            params=wav.getparams();raw=wav.readframes(count)
        if (params.nchannels,params.sampwidth,params.framerate)!=(1,2,44100):raise ValueError('unexpected capture format')
        if len(raw)!=count*params.sampwidth*params.nchannels:raise ValueError('short recording')
        with wave.open(str(out/'result-preview.wav'),'wb') as wav:
            wav.setparams(params);wav.writeframes(raw)
        delivery=dict(scope='First-loop-length prefix of ready-aligned actual Fuse audio; no gain or filter',
                      frames=count,sample_rate=params.framerate,pcm_sha256=sha(raw),
                      peak_pcm16=int(np.max(abs(np.frombuffer(raw,'<i2').astype(np.int32)))),
                      full_scale_samples=int(np.count_nonzero(abs(np.frombuffer(raw,'<i2').astype(np.int32))>=32767)))
    archive=out/'producer-source';archive.mkdir(exist_ok=True)
    hashes={}
    for name in SOURCES:
        data=(HERE/name).read_bytes().replace(b'\r\n',b'\n');hashes[name]=sha(data)
        (archive/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    save(out/'report.json',dict(date='2026-10-02',complete=True,preview_only=True,verification=proof,
        player=json.loads((out/'player.json').read_bytes()),render=metrics,delivery=delivery,
        sources_sha256_lf=hashes,baseline=str(baseline),
        artifacts={p.relative_to(out).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
                   for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'report.json' and p.name!='fuse-stderr.txt'}))
    return metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--baseline',type=Path,default=HERE/'experiments/ima-uniform73')
    p.add_argument('--fuse',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--record',action='store_true',help='also record two loops at normal speed')
    args=p.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):p.error('output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    packed=gzip.decompress((args.baseline/'soundtrack.ima.gz').read_bytes())
    old=json.loads((args.baseline/'player.json').read_bytes())
    if sha(packed)!=old['packed_sha256']:raise ValueError('baseline stream changed')
    disk,meta=build_disk(packed,old['initial_predictor'],old['initial_index'],out/'assembly',pwm=True)
    (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));save(out/'player.json',meta)
    native=native_check(disk,meta,packed);print(json.dumps(native),flush=True)
    actual=fuse_check(args.fuse,out,meta,packed)
    save(out/'verification.json',dict(complete=True,native=native,fuse=actual))
    if args.record:
        import sys
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                        '--output',str(out/'sound-128'),'--machine','128'],check=True)
    print(json.dumps(finish(out,args.baseline,args.ffmpeg)),flush=True)


if __name__=='__main__':main()
