"""Build one resident speech PDM preview against its measured Spectrum schedule."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np
from pdm_player import build_disk, CPU_CLOCK, BIT_TSTATES
from verify_pdm import save, verify

HERE=Path(__file__).resolve().parent
RATE=192000


def sha(blob): return hashlib.sha256(blob).hexdigest()


def sigma_delta(samples,intervals,seed=1977):
    """Second-order error feedback, in area units for nonuniform PDM slots.

    e[n] = w[n]*(x[n]-y[n]) + 2*e[n-1] - e[n-2]. The quantizer picks
    y in {-1,+1}. Fixed tiny TPDF dither prevents a coherent silence tone.
    """
    if len(samples)!=len(intervals) or not np.isfinite(samples).all() or np.any(intervals<=0):
        raise ValueError('invalid PDM input')
    rng=np.random.default_rng(seed)
    dither=(rng.random(len(samples))-rng.random(len(samples)))*.002
    weights=np.asarray(intervals,dtype=float)/BIT_TSTATES
    bits=np.empty(len(samples),dtype=np.uint8)
    previous=older=peak=0.
    for i,(x,w) in enumerate(zip(samples+dither,weights)):
        value=x+(2*previous-older)/w
        bit=value>=0; quantized=1. if bit else -1.
        error=w*(value-quantized)
        older,previous=previous,error; peak=max(peak,abs(error)); bits[i]=bit
        if not np.isfinite(error) or abs(error)>8: raise ValueError('PDM modulator overload')
    return bits,dict(order=2,dither='TPDF, peak +/-0.002',seed=seed,
        peak_error_area=peak,input_peak=float(np.max(abs(samples))),ones_density=float(bits.mean()))


def reconstruct(bits,times,rate=RATE):
    """Integrate actual piecewise-constant port levels into uniform PCM bins."""
    times=np.asarray(times,dtype=float)
    levels=bits.astype(float)*2-1
    area=np.r_[0,np.cumsum(levels*np.diff(times))]
    count=int(np.floor(times[-1]*rate/CPU_CLOCK))
    edges=np.arange(count+1,dtype=float)*CPU_CLOCK/rate
    indices=np.minimum(np.searchsorted(times,edges,side='right')-1,len(bits)-1)
    integral=area[indices]+levels[indices]*(edges-times[indices])
    return np.diff(integral)/(CPU_CLOCK/rate)


def write_wav(path,samples,rate=44100):
    data=np.rint(np.clip(samples,-1,1)*32767).astype('<i2')
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(data.tobytes())


def pcm8k(signal,ffmpeg,path):
    """Round-trip through an actual unsigned 8-bit, 8000 Hz mono WAV.

    Resampling applies antialiasing before quantization and band-limited
    interpolation afterwards. PDM receives only this decoded 8-bit signal.
    """
    down=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1',
        '-i','-','-ar','8000','-f','f32le','-'],input=signal.astype('<f4').tobytes(),
        capture_output=True,check=True).stdout
    samples=np.frombuffer(down,'<f4')
    data=np.clip(np.rint(samples.astype(float)*128+128),0,255).astype(np.uint8).tobytes()
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1); out.setsampwidth(1); out.setframerate(8000); out.writeframes(data)
    with wave.open(str(path),'rb') as saved:
        if (saved.getnchannels(),saved.getsampwidth(),saved.getframerate())!=(1,1,8000):
            raise AssertionError('PCM format mismatch')
        if saved.readframes(saved.getnframes())!=data: raise AssertionError('PCM bytes changed')
    up=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','u8','-ar','8000','-ac','1',
        '-i','-','-ar',str(RATE),'-f','f32le','-'],input=data,capture_output=True,check=True).stdout
    restored=np.frombuffer(up,'<f4').astype(float)
    # A fractional final 8-kHz sample is zero-padded/truncated at the faded edge.
    if abs(len(restored)-len(signal))>RATE//8000:
        raise AssertionError('PCM resampling length mismatch')
    restored=np.pad(restored,(0,max(0,len(signal)-len(restored))))[:len(signal)]
    return restored,dict(sample_rate_hz=8000,bits_per_sample=8,channels=1,codec='PCM unsigned 8-bit',
        samples=len(data),duration_seconds=len(data)/8000,quantization='round to nearest, (u8-128)/128',
        data_sha256=sha(data),file=path.name,antialiasing='FFmpeg sample-rate converter',
        pdm_input='band-limited reconstruction of these exact 8-bit PCM bytes')


def put_disk(directory,packed,bit_tstates=BIT_TSTATES,repeat=False):
    directory.mkdir(parents=True,exist_ok=True)
    disk,metadata=build_disk(packed,bit_tstates,repeat)
    (directory/'audiobook-preview.trd').write_bytes(disk)
    (directory/'soundtrack.pdm.gz').write_bytes(gzip.compress(packed,mtime=0))
    save(directory/'player.json',metadata)
    return metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path); p.add_argument('--ffmpeg',required=True)
    p.add_argument('--fuse',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--start',type=float,default=60); p.add_argument('--kib',type=int,default=96)
    p.add_argument('--bit-tstates',type=int,choices=(52,46),default=52)
    p.add_argument('--pcm8k',action='store_true',help='quantize source to 8000 Hz, unsigned 8-bit mono before PDM')
    p.add_argument('--repeat',action='store_true',help='loop the resident bitstream without disk reloads')
    p.add_argument('--resume-render',action='store_true',help='reuse complete, matching pilot/speech verification after a render-only interruption')
    args=p.parse_args()
    if not 1<=args.kib<=96 or args.start<0: p.error('need 1..96 KiB and nonnegative start')
    if args.output.exists() and any(args.output.iterdir()) and not args.resume_render:
        p.error('output must be new or empty, or use --resume-render with complete verification')
    with args.input.open('rb') as stream: source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    archived=json.loads((HERE.parent/'audiobook-ay/preview/report.json').read_bytes())
    if source_hash!=archived['source_sha256']: raise ValueError('source audiobook changed')
    # All output instructions have the same timing for 0 and 1. The pilot
    # measures ULA delays and every bank boundary before encoding speech.
    pilot=args.output/'timing-pilot'
    def reuse(directory,packed):
        disk,metadata=build_disk(packed,args.bit_tstates,args.repeat)
        proof=json.loads((directory/'verification.json').read_bytes())
        if (disk!=(directory/'audiobook-preview.trd').read_bytes() or
            sha(disk)!=proof['fuse']['trd_sha256'] or not proof['complete'] or
            not proof['fuse']['every_bit_exact'] or proof['fuse']['minimum_instantaneous_bit_rate_hz']<40000 or
            gzip.decompress((directory/'soundtrack.pdm.gz').read_bytes())!=packed):
            raise ValueError('cannot reuse changed/incomplete PDM verification')
        for name,digest in proof['verification_sources_sha256_lf'].items():
            if sha((HERE/name).read_bytes().replace(b'\r\n',b'\n'))!=digest:
                raise ValueError('verification source changed')
        return metadata,proof
    if args.resume_render:
        _,pilot_report=reuse(pilot,b'\x55'*(args.kib*1024))
    else:
        put_disk(pilot,b'\x55'*(args.kib*1024),args.bit_tstates,args.repeat)
        print('Measuring complete PDM output schedule in cold Fuse',flush=True)
        pilot_report=verify(pilot,args.fuse)
    times=np.frombuffer(gzip.decompress((pilot/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    duration=float(times[-1]/CPU_CLOCK)
    context=min(1.,args.start)
    command=[args.ffmpeg,'-v','error','-nostdin','-ss',str(args.start-context),'-i',str(args.input.resolve()),
        '-t',str(context+duration+1),'-map','0:a:0','-ac','1','-af',
        'highpass=f=70,lowpass=f=3800:p=2,lowpass=f=3800:p=2','-ar',str(RATE),'-f','f32le','-']
    raw=subprocess.run(command,check=True,capture_output=True).stdout
    source=np.frombuffer(raw,'<f4').astype(float)
    offset=round(context*RATE); count=int(np.floor(duration*RATE))
    original=source[offset:offset+count]
    if len(original)!=count: raise ValueError('source ends before complete preview')
    gain=.65/max(float(np.max(abs(original))),1e-12)
    original*=gain
    # Fade only the first/last 20 ms of the bounded listening excerpt.
    t=np.arange(count)/RATE
    envelope=np.minimum(1,np.minimum(t/.020,(duration-t)/.020))
    original*=np.maximum(0,envelope)
    source_pcm=dict(sample_rate_hz=RATE,representation='floating-point working signal',channels=1)
    if args.pcm8k:
        original,source_pcm=pcm8k(original,args.ffmpeg,args.output/'pcm8k-preview.wav')
    centres=(times[:-1]+np.diff(times)/2)/CPU_CLOCK
    samples=np.interp(centres,t,original,left=0,right=0)
    bits,modulator=sigma_delta(samples,np.diff(times))
    packed=np.packbits(bits).tobytes()
    if not np.array_equal(np.unpackbits(np.frombuffer(packed,dtype=np.uint8)),bits):
        raise AssertionError('PDM pack/unpack failed')
    if args.resume_render:
        metadata,final=reuse(args.output,packed)
    else:
        metadata=put_disk(args.output,packed,args.bit_tstates,args.repeat)
        print('Checking every speech bit and actual output interval through '+('two complete loops' if args.repeat else 'EOF'),flush=True)
        final=verify(args.output,args.fuse)
    actual_times=np.frombuffer(gzip.decompress((args.output/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    max_deviation=int(np.max(abs(actual_times-times)))
    phase_delta=final['fuse']['first_out_phase_tstates']-pilot_report['fuse']['first_out_phase_tstates']
    # EI/HALT can enter the interrupt on adjacent T-states. Permit only this
    # bounded startup uncertainty, not accumulating schedule drift. The >40 kHz
    # all-interval gate is unchanged; reconstruction uses the final trace.
    if abs(phase_delta)>3 or max_deviation>3:
        raise AssertionError('output schedule drift exceeds 3-T startup tolerance')
    alignment=dict(exact=bool(np.array_equal(actual_times,times)),maximum_deviation_tstates=max_deviation,
                   first_out_phase_difference_tstates=phase_delta,tolerance_tstates=3,
                   maximum_deviation_microseconds=max_deviation*1e6/CPU_CLOCK)
    duration=float(actual_times[-1]/CPU_CLOCK)
    reconstructed=reconstruct(bits,actual_times)
    if len(reconstructed)!=len(original): raise AssertionError('reconstruction duration mismatch')

    def audio_filter(signal,lowpass):
        filters='highpass=f=70'
        if lowpass: filters+=',lowpass=f=4500:p=2,lowpass=f=4500:p=2'
        pcm=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1',
            '-i','-','-af',filters,'-ar','44100','-f','f32le','-'],input=signal.astype('<f4').tobytes(),
            capture_output=True,check=True).stdout
        return np.frombuffer(pcm,'<f4').astype(float)
    signals=dict(original=audio_filter(original,True),beeper=audio_filter(reconstructed,True),
                 wideband=audio_filter(reconstructed,False))
    common_gain=min(1.,.9/max(float(np.max(abs(s))) for s in signals.values()))
    for name,signal in signals.items(): write_wav(args.output/f'{name}-preview.wav',signal*common_gain)
    margin=round(.1*44100); reference=signals['original'][margin:-margin]; candidate=signals['beeper'][margin:-margin]
    error=candidate-reference
    metrics=dict(waveform_correlation=float(np.corrcoef(reference,candidate)[0,1]),
                 reconstruction_snr_db=float(10*np.log10(np.mean(reference**2)/max(np.mean(error**2),1e-30))),
                 excluded_edge_seconds=.1,scope='same 4.5 kHz reconstruction filter; not a listener intelligibility score')
    report=dict(complete=True,preview_only=True,source=str(args.input.resolve()),source_sha256=source_hash,
        start_seconds=args.start,duration_seconds=duration,source_pcm_sha256=sha(raw),
        original_source_sha256=archived['source_sha256'],source_gain=gain,edge_fade_seconds=.020,
        pdm_source_pcm=source_pcm,working_sample_rate_hz=RATE,
        listening_wav=dict(sample_rate_hz=44100,bits_per_sample=16,channels=1),
        source_filter='70 Hz highpass; two 2-pole 3800 Hz lowpasses',modulator=modulator,
        packed_bytes=len(packed),bits=len(bits),bit_order='MSB first',output='ULA FE bit 4; MIC and border bits zero',
        nominal_cpu_bit_rate_hz=metadata['nominal_bit_rate_hz'],actual_timing=final['fuse'],
        pilot_schedule_alignment=alignment,all_bits_verified=True,pack_roundtrip=True,
        metrics=metrics,preview_common_gain=common_gain,
        preview_scope='actual FE hold times integrated at 192 kHz, resampled to 44100; no physical speaker model',
        beeper_preview_filter='70 Hz highpass; two 2-pole 4500 Hz lowpasses; ideal reconstruction for listening',
        wideband_preview_filter='70 Hz highpass and sample-rate-conversion antialiasing only',
        irq_during_playback=False,runtime_disk_reads=0,ay_enabled=False,repeat=args.repeat,
        native_tests='test_pdm.py: all 256 byte values, six banks, partial bank, stack/code guards and invalid lengths',
        producer_sources_sha256_lf={name:sha((HERE/name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('pdm_player.py','verify_pdm.py','build_pdm.py')},
        artifacts={f.relative_to(args.output).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
            for f in sorted(args.output.rglob('*')) if f.is_file() and f.name!='fuse-stderr.txt'})
    save(args.output/'report.json',report)
    print(json.dumps(dict(duration=duration,actual=final['fuse'],metrics=metrics,modulator=modulator)),flush=True)


if __name__=='__main__': main()
