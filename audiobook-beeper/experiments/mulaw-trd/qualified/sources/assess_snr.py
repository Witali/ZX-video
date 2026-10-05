"""Bounded host analysis of beeper SNR; never builds or modifies a player.

Compare the measured PDM schedule with ideal schedules on the same complete
speech excerpt. Distinguish modulation error from total error relative to
the prepared PCM8 input. Ideal rows are neither Z80 timing proofs nor physical
hardware predictions. The spectral band is an ideal measurement selection,
not a claim that the Spectrum speaker implements a brick-wall filter.
"""
import argparse,gzip,hashlib,json,subprocess,wave
from pathlib import Path
import numpy as np
from build_pdm import reconstruct,RATE
from ima_player import CPU_CLOCK
from ima_codec import decode
from verify_ima import reference
from verify_pdm import save

HERE=Path(__file__).resolve().parent
FILTER='highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2'


def sha(data):return hashlib.sha256(data).hexdigest()


def first_order(levels):
    phase=128+np.cumsum(levels,dtype=np.int64)
    return np.diff(np.r_[0,phase//256]).astype(np.uint8)


def feedback(levels,beta,gain):
    target=.5+gain*(levels.astype(float)/256-.5)
    result=np.empty(len(target),dtype=np.uint8);previous=older=peak=0.
    for i,x in enumerate(target):
        u=x+(1+beta)*previous-beta*older
        bit=int(u>=.5)
        older,previous=previous,u-bit
        result[i]=bit;peak=max(peak,abs(previous))
    if not np.isfinite(peak) or peak>8:raise ValueError(f'unbounded feedback candidate: {peak}')
    return result,dict(beta=beta,input_gain=gain,peak_error_state=peak,
                       z80_ported=False,rc_model=False)


def ratio(signal,error):
    noise=float(np.mean(error*error))
    return float(10*np.log10(np.mean(signal*signal)/noise)) if noise else None


def welch_power(signal,fs):
    n=65536;window=.5-.5*np.cos(2*np.pi*np.arange(n)/n)
    blocks=np.lib.stride_tricks.sliding_window_view(signal,n)[::n//2]
    power=np.zeros(n//2+1)
    for start in range(0,len(blocks),16):
        spectrum=np.fft.rfft(blocks[start:start+16]*window,axis=1)
        power+=np.sum(abs(spectrum)**2,axis=0)
    # Common Welch scaling cancels in each signal/error ratio.
    return np.fft.rfftfreq(n,1/fs),power/len(blocks)


def band_ratio(signal,error,fs,high):
    f,s=welch_power(signal,fs)
    _,e=welch_power(error,fs)
    band=(f>=70)&(f<=high)
    noise=float(e[band].sum())
    return float(10*np.log10(s[band].sum()/noise)) if noise else None


def measure(bits,decoded,source,times,ffmpeg,gain=1):
    # Every row has the same three-slot latency as the ordinary PDM player.
    emitted=np.r_[np.zeros(3,dtype=np.uint8),bits[:-3]]
    def delayed(values):return np.r_[np.zeros(3),.5+gain*(values[:-3]/256-.5)]
    output=reconstruct(emitted,times)
    target=reconstruct(delayed(decoded),times)
    original=reconstruct(delayed(source),times)
    raw={};filtered={}
    for name,sig in (('output',output),('decoded',target),('source',original)):
        raw[name]=sig[round(.1*RATE):-round(.1*RATE)]
        result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                               '-af',FILTER,'-ar','44100','-f','f32le','-'],
                              input=sig.astype('<f4').tobytes(),capture_output=True,check=True)
        filtered[name]=np.frombuffer(result.stdout,'<f4').astype(float)[4410:-4410]
    def metrics(x,spectral=False):
        a,b,c=x['output'],x['decoded'],x['source']
        fn=(lambda s,e:band_ratio(s,e,RATE,3800)) if spectral else ratio
        return dict(modulator_snr_db=fn(b,a-b),total_snr_db=fn(c,a-c),codec_snr_db=fn(c,b-c))
    return dict(common_listening_filter=metrics(filtered),band_70_3800_hz=metrics(raw,True),
                band_70_3000_hz_modulator_snr_db=band_ratio(raw['decoded'],raw['output']-raw['decoded'],RATE,3000))


def check_numerics(source,ffmpeg):
    """Check integration-rate sensitivity on the highest-quality candidate."""
    levels=np.repeat(source[:40000],16)
    bits,_=feedback(levels,1,.5)
    emitted=np.r_[np.zeros(3,dtype=np.uint8),bits[:-3]]
    target=np.r_[np.zeros(3),.5+.5*(levels[:-3]/256-.5)]
    times=np.arange(len(levels)+1)*CPU_CLOCK/128000
    rows=[]
    for rate in (192000,768000):
        signals=[]
        for values in (emitted,target):
            x=reconstruct(values,times,rate)
            result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(rate),
                                   '-ac','1','-i','-','-af',FILTER,'-ar','44100','-f','f32le','-'],
                                  input=x.astype('<f4').tobytes(),capture_output=True,check=True)
            signals.append(np.frombuffer(result.stdout,'<f4').astype(float)[4410:-4410])
        output,reference=signals
        rows.append(dict(integration_rate_hz=rate,snr_db=ratio(reference,output-reference)))
    delta=abs(rows[0]['snr_db']-rows[1]['snr_db'])
    assert delta<.1,rows
    return dict(scope='Numerical convergence only: first five seconds, PCM8, half-gain second-order 128 kHz, common listening filter',
                results=rows,absolute_delta_db=delta,baseline_matches_saved_full_fuse_render_to_db=1e-9)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    base=HERE/'experiments/ima-uniform73';old=HERE/'ima-preview'
    meta=json.loads((base/'player.json').read_bytes());saved=json.loads((base/'report.json').read_bytes())
    packed=gzip.decompress((base/'soundtrack.ima.gz').read_bytes())
    assert sha(packed)==meta['packed_sha256']
    prep=json.loads((old/'preparation.json').read_bytes())
    with wave.open(str(old/'pcm8k-preview.wav'),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,1,8000)
        source=np.frombuffer(wav.readframes(wav.getnframes()),'u1').copy()
    assert sha(source.tobytes())==prep['source_pcm']['data_sha256']
    pcm,_=decode(packed,meta['initial_predictor'],meta['initial_index'])
    decoded=((pcm.astype(np.int32)+32768)>>8).astype(np.uint8)
    assert len(decoded)==len(source)
    pcmref=(source.astype(float)-128)*256
    codec_raw=ratio(pcmref,pcm.astype(float)-pcmref)
    assert abs(codec_raw-prep['compression_snr_db'])<1e-10
    _,_,levels,expected,n=reference(packed,meta)
    levels=levels[:n];weights=np.full(len(source),6,dtype=np.int32);offset=0
    for s in meta['sections']:
        for end in range(offset+256,offset+s['bytes'],256):weights[2*end-2]=7
        offset+=s['bytes'];weights[2*offset-2]=11
    source_levels=np.repeat(source,weights)
    bits=first_order(levels)
    assert np.array_equal(np.r_[np.zeros(3,dtype=np.uint8),bits[:-3]],expected[:n])
    times=np.frombuffer(gzip.decompress((base/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:n+1]
    assert sha((base/'output-times.u32.gz').read_bytes())==saved['artifacts']['output-times.u32.gz']['sha256']
    rows=[]
    def add(name,bits,d,s,t,kind,gain=1,**extra):
        row=dict(name=name,status=kind,pdm_rate_hz=len(bits)*CPU_CLOCK/t[-1],**extra,
                 metrics=measure(bits,d,s,t,args.ffmpeg,gain))
        rows.append(row)
        print(json.dumps(row),flush=True)
    add('current_actual',bits,levels,source_levels,times,'saved full Fuse timing')
    assert abs(rows[-1]['metrics']['common_listening_filter']['modulator_snr_db']-saved['render']['pdm_snr_db'])<1e-9
    add('same_bits_uniform_timing',bits,levels,source_levels,np.linspace(0,times[-1],n+1),
        'host model; same bits, per-sample weights and total duration, ideal uniform output')
    for rate in (48000,64000,72000,96000,128000):
        repeat=rate//8000;d=np.repeat(decoded,repeat);s=np.repeat(source,repeat)
        ts=np.arange(len(d)+1,dtype=float)*CPU_CLOCK/rate
        add(f'first_order_{rate}',first_order(d),d,s,ts,'ideal timing model; not a player',slots_per_sample=repeat)
        if rate==64000:
            b,state=feedback(d,.5,1)
            add('damped_feedback_64000',b,d,s,ts,'host-only algorithm, unknown complete Z80 cost',generator=state)
        if rate in (64000,128000):
            b,state=feedback(d,1,.5)
            add(f'second_order_half_gain_{rate}',b,d,s,ts,'host-only second-order model, half amplitude; not ported',gain=.5,generator=state)
        if rate==128000:
            b,state=feedback(s,1,.5)
            add('pcm8_without_ima_second_order_128000',b,s,s,ts,
                'host-only changed format, short or streamed precomputed output; no verified playback kernel',gain=.5,generator=state)
    rms=float(np.std((source.astype(float)-128)/128))
    save(out/'numerical-check.json',check_numerics(source,args.ffmpeg))
    report=dict(date='2026-10-02',scope='Analysis only; no new player, disk or physical hardware test',
        reference='Prepared, conditioned PCM8 before IMA; not a clean studio reference or original noisy tape',
        source_samples=len(source),source_duration_seconds=len(source)/8000,source_rms=rms,
        input_pcm_sha256=sha(source.tobytes()),packed_sha256=sha(packed),
        cpu_clock_hz=CPU_CLOCK,codec_raw_pcm16_snr_db=codec_raw,
        ideal_pcm8_full_scale_sine_snr_db=6.020599913*8+1.760912591,
        ideal_pcm8_speech_snr_estimate_db=20*np.log10(rms/(1/128/np.sqrt(12))),
        filter=FILTER,band_measurement='Welch/Hann 65536 at 192000 Hz, 50% overlap; integrate 70..3800 Hz; no physical brick-wall filter implied',
        edges_excluded_seconds=.1,rows=rows,
        limitations=['SNR means signal-to-reconstruction-error including distortion, not isolated random noise.',
                     'Same filter is applied to output and each reference; no fitted phase/gain correction.',
                     'Each reference follows its row sample schedule, excluding tempo and sample-clock error against a fixed 8000-Hz clock.',
                     'Pulse areas are integrated at 192000 Hz before filtering; these are numerical reconstructions, not analog measurements.',
                     'Codec-only row is the perfect-decoded-waveform reference, not a universal bound for every codec or modulator.',
                     'First-order closed-form white-error scaling does not predict idle tones or correlated error exactly.',
                     'Higher-order feedback and rates are host models; no stable finite-word Z80 implementation is claimed.',
                     'The existing packed-bit player and IMA kernels do not establish 96/128-kHz feasibility.',
                     'Actual analog speaker/amplifier noise and distortion were not measured.'],
        references=['https://www.analog.com/media/en/training-seminars/tutorials/MT-001.pdf',
                    'https://www.analog.com/media/en/training-seminars/tutorials/MT-022.pdf',
                    'https://www.zilog.com/docs/z80/um0080.pdf'],
        producer_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    save(out/'report.json',report)
    (out/'assess_snr.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes().replace(b'\r\n',b'\n'),mtime=0))
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
