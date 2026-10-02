"""Simulate an unloaded series-R/shunt-C low-pass on an existing PCM16 WAV.

The circuit obeys tau*dy/dt + y = x, tau=RC. At 16x the WAV rate we solve
each interval exactly for a linearly interpolated input, then resample back.
This avoids the large near-Nyquist response error of a coarse one-pole
recursion directly at 44.1 kHz. No extra gain or forward/backward pass.
"""
import argparse,array,cmath,hashlib,json,math,subprocess,wave
from pathlib import Path


def inspect(path):
    with wave.open(str(path),'rb') as wav:
        if wav.getsampwidth()!=2:raise ValueError('expected PCM16 WAV')
        samples=array.array('h',wav.readframes(wav.getnframes()))
        return dict(sample_rate_hz=wav.getframerate(),channels=wav.getnchannels(),bits=16,
            frames=wav.getnframes(),duration_seconds=wav.getnframes()/wav.getframerate(),
            peak_abs_pcm=max(map(abs,samples)),full_scale_samples=sum(x in (-32768,32767) for x in samples),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--cutoff',type=float,default=20000)
    p.add_argument('--resistance',type=float,default=1000)
    args=p.parse_args();before=inspect(args.input);rate=before['sample_rate_hz']
    if not 0<args.cutoff<rate/2 or args.resistance<=0:p.error('invalid cutoff or resistance')
    work_rate=rate*16;tau=1/(2*math.pi*args.cutoff);q=1/(work_rate*tau)
    a=math.exp(-q);beta=-math.expm1(-q)/q;b0=1-beta;b1=beta-a
    # y[n]=a*y[n-1]+b1*x[n-1]+b0*x[n]; zero initial capacitor voltage.
    assert 0<a<1 and abs((b0+b1)/(1-a)-1)<1e-12
    z=cmath.exp(-2j*math.pi*args.cutoff/work_rate)
    response=(b0+b1*z)/(1-a*z);db=20*math.log10(abs(response))
    ideal_db=-10*math.log10(2)
    assert abs(db-ideal_db)<0.03
    filters=(f'aresample={work_rate}:resampler=soxr:precision=28,'
             f'biquad=b0={b0:.17g}:b1={b1:.17g}:b2=0:a0=1:a1={-a:.17g}:a2=0:precision=f64,'
             f'aresample={rate}:resampler=soxr:precision=28')
    command=[args.ffmpeg,'-v','error','-nostdin','-n','-i',str(args.input.resolve()),
             '-map','0:a:0','-af',filters,'-c:a','pcm_s16le',str(args.output.resolve())]
    subprocess.run(command,check=True);after=inspect(args.output)
    assert all(before[k]==after[k] for k in ('sample_rate_hz','channels','bits','frames'))
    assert after['full_scale_samples']==0
    report=dict(cutoff_hz=args.cutoff,resistance_ohms=args.resistance,capacitance_farads=tau/args.resistance,
        time_constant_seconds=tau,topology='ideal unloaded series R, shunt C; output across C',
        analog_transfer='H(f)=1/(1+j*2*pi*f*R*C)',analog_slope_db_per_octave=-6.020599913279624,
        internal_rate_hz=work_rate,interpolation='exact first-order-hold RC step; SOXR 28-bit up/down sampling',
        coefficients=dict(a=a,b0=b0,b1=b1),modeled_rc_at_cutoff_db=db,ideal_rc_at_cutoff_db=ideal_db,
        response_check_scope='RC stage alone; excludes antialias resamplers and final PCM16 quantization',
        extra_gain_or_normalization=False,input=before,output=after,command=command,
        verification='Stable pole, unity DC gain, cutoff error <0.03 dB; unchanged WAV format/frame count; no full-scale output',
        scope='Offline RC filtering of existing Fuse WAV; not a complete Spectrum speaker circuit model',
        producer_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest())
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(output=str(args.output),cutoff_hz=args.cutoff,tau_seconds=tau,
                         modeled_rc_at_cutoff_db=db,wav=after)))


if __name__=='__main__':main()
