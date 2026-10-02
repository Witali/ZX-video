"""Prepare PCM8, encode IMA4, assemble a separate ASM player and package TRD."""
from __future__ import annotations
import argparse,gzip,hashlib,json,subprocess,wave
from pathlib import Path
import numpy as np
from ima_codec import encode,decode,verification_wav
from ima_player import layout,build_disk,CPU_CLOCK
from build_pdm import pcm8k,write_wav,reconstruct,RATE
from verify_ima import verify,reference
from verify_pdm import save

HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()


def ffmpeg_check(packed,pcm,indices,ffmpeg,out):
    """Decode every compressed nibble using FFmpeg's independent IMA-WAV path."""
    checks=[];previous=state=0
    for i,start in enumerate(range(0,len(packed),32764)):
        part=packed[start:start+32764];wav=verification_wav(part,previous,state)
        result=subprocess.run([ffmpeg,'-v','error','-nostdin','-i','-','-f','s16le','-acodec','pcm_s16le','-'],
                              input=wav,capture_output=True,check=True)
        actual=np.frombuffer(result.stdout,'<i2')
        expected=pcm[2*start:2*(start+len(part))]
        if len(actual)!=len(expected)+1 or actual[0]!=previous or not np.array_equal(actual[1:],expected):
            raise AssertionError(f'FFmpeg IMA mismatch at block {i}')
        checks.append(dict(packed_offset=start,bytes=len(part),decoded_samples=len(expected),exact=True))
        previous=int(expected[-1]);state=int(indices[2*(start+len(part))-1])
    version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    return dict(complete=True,tool=version,blocks=checks,decoded_samples=len(pcm),every_sample_exact=True)


def render(out,packed,meta,ffmpeg):
    pcm,indices,levels,bits,n=reference(packed,meta)
    times=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:n+1]
    # Same measured time base and three-slot output delay for the comparison.
    ideal=np.r_[np.zeros(3),levels[:n-3]/256]
    signals={'beeper':reconstruct(bits[:n],times),'decoded-held':reconstruct(ideal,times)}
    filtered={}
    for name,signal in signals.items():
        raw=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
             '-af','highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2','-ar','44100','-f','f32le','-'],
             input=signal.astype('<f4').tobytes(),capture_output=True,check=True).stdout
        filtered[name]=np.frombuffer(raw,'<f4').astype(float)
    gain=min(1.,.9/max(float(np.max(abs(x))) for x in filtered.values()))
    for name,signal in filtered.items():write_wav(out/f'{name}-preview.wav',signal*gain)
    a=filtered['decoded-held'][4410:-4410];b=filtered['beeper'][4410:-4410]
    return dict(scope='actual Fuse FE holds; same 70 Hz HP / two 4.5 kHz 2-pole LPs; no speaker model',
        common_gain=gain,pdm_snr_db=float(10*np.log10(np.mean(a*a)/np.mean((a-b)**2))),
        pdm_correlation=float(np.corrcoef(a,b)[0,1]),excluded_edge_seconds=.1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--fuse',type=Path,required=True);p.add_argument('--start',type=float,default=60)
    p.add_argument('--speech-gain',type=float,default=4,help='pre-ADPCM gain with 0.85 lookahead peak limit; 1 keeps old level')
    p.add_argument('--resume',action='store_true',help='reuse prepared stream; verify again unless proof and sources match')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=json.loads((HERE/'source-format.json').read_bytes());path=Path(source['source'])
    sections,_=layout();count=2*sum(s['bytes'] for s in sections);duration=count/8000
    if not args.resume:
        if any(out.iterdir()):p.error('output must be empty, or --resume')
        if sha(path.read_bytes())!=source['source_sha256']:raise ValueError('source changed')
        context=min(1.,args.start)
        raw=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-ss',str(args.start-context),'-i',str(path),
            '-t',str(context+duration+1),'-map','0:a:0','-ac','1','-af',
            'highpass=f=70,lowpass=f=3800:p=2,lowpass=f=3800:p=2','-ar',str(RATE),'-f','f32le','-'],
            capture_output=True,check=True).stdout
        original=np.frombuffer(raw,'<f4').astype(float)[round(context*RATE):round((context+duration)*RATE)]
        if len(original)!=round(duration*RATE):raise ValueError('source excerpt incomplete')
        gain=.65/max(float(np.max(abs(original))),1e-12);original*=gain
        t=np.arange(len(original))/RATE;original*=np.maximum(0,np.minimum(1,np.minimum(t/.020,(duration-t)/.020)))
        before_rms=float(np.sqrt(np.mean(original**2)))
        conditioning=f'volume={args.speech_gain},alimiter=limit=0.85:attack=5:release=100:level=0:latency=1'
        limited=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
            '-af',conditioning,'-f','f32le','-'],input=original.astype('<f4').tobytes(),capture_output=True,check=True).stdout
        original=np.frombuffer(limited,'<f4').astype(float)
        if len(original)!=round(duration*RATE):raise AssertionError('limiter changed sample count')
        _,source_pcm=pcm8k(original,args.ffmpeg,out/'pcm8k-preview.wav')
        source_pcm['pdm_input']='high byte of live IMA PCM16 predictor; six PDM slots/sample plus bank-tail holds'
        with wave.open(str(out/'pcm8k-preview.wav'),'rb') as wav:raw_pcm=wav.readframes(wav.getnframes())
        if len(raw_pcm)!=count:raise AssertionError('PCM sample count')
        print(f'Encoding {count} PCM8 samples into {count//2} IMA bytes',flush=True)
        packed=encode(raw_pcm);pcm,indices=decode(packed)
        independent=ffmpeg_check(packed,pcm,indices,args.ffmpeg,out)
        write_wav(out/'decoded-preview.wav',pcm.astype(float)/32768,8000)
        disk,meta=build_disk(packed,assembly_dir=out/'assembly')
        (out/'audiobook-preview.trd').write_bytes(disk)
        (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));save(out/'player.json',meta)
        expected=(np.frombuffer(raw_pcm,'u1').astype(float)-128)*256
        error=pcm.astype(float)-expected
        prep=dict(source=source,source_start_seconds=args.start,source_duration_seconds=duration,source_pcm=source_pcm,
            source_gain=gain,edge_fade_seconds=.020,ffmpeg_decode=independent,
            level_conditioning=dict(filter=conditioning,before_rms=before_rms,after_rms=float(np.sqrt(np.mean(original**2))),
                                    purpose='raise quiet speech above first-order PDM noise; peak limiting changes dynamics'),
            compression_snr_db=float(10*np.log10(np.mean(expected**2)/np.mean(error**2))),
            compression_ratio_to_pcm8=2,compression_ratio_to_pcm16=4,
            input_pcm_bytes=count,compressed_bytes=len(packed))
        save(out/'preparation.json',prep)
    else:
        packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
        meta=json.loads((out/'player.json').read_bytes());prep=json.loads((out/'preparation.json').read_bytes())
        disk,rebuilt=build_disk(packed,assembly_dir=out/'assembly')
        if disk!=(out/'audiobook-preview.trd').read_bytes() or rebuilt!=meta:raise ValueError('resume binary/metadata changed')
    sources={name:sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) for name in
             ('ima-player.asm','ima_player.py','ima_codec.py','verify_ima.py','build_ima.py','test_ima.py')}
    proof=None
    if args.resume and (out/'verification.json').exists():
        old=json.loads((out/'verification.json').read_bytes())
        if old.get('sources_sha256_lf')==sources and old['fuse']['trd_sha256']==sha(disk):proof=old
    if proof is None:
        proof=verify(out,args.fuse);proof['sources_sha256_lf']=sources;save(out/'verification.json',proof)
    metrics=render(out,packed,meta,args.ffmpeg)
    # Retain exact binary inputs/output and assembler listing for separate builds.
    archive=out/'producer-source';archive.mkdir(exist_ok=True)
    for name in sources:(archive/(name+'.gz')).write_bytes(gzip.compress((HERE/name).read_bytes().replace(b'\r\n',b'\n'),mtime=0))
    report=dict(complete=True,preview_only=True,physical_hardware_tested=False,preparation=prep,player=meta,
        verification=proof,render=metrics,sources_sha256_lf=sources,
        artifacts={f.relative_to(out).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
                   for f in sorted(out.rglob('*')) if f.is_file() and f.name not in ('report.json','fuse-stderr.txt')})
    save(out/'report.json',report)
    print(json.dumps(dict(preparation=prep,render=metrics,actual_timing=proof['fuse'])),flush=True)


if __name__=='__main__':main()
