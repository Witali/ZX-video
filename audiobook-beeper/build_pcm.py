"""Build and verify the looping PCM8-to-PDM player; render measured port holds."""
from __future__ import annotations
import argparse,gzip,json,subprocess,wave
from pathlib import Path
import numpy as np
from pcm_player import build_disk,CPU_CLOCK
from verify_pcm import verify,reference,save
from build_pdm import sha,reconstruct,write_wav,RATE

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path); p.add_argument('--ffmpeg',required=True)
    p.add_argument('--fuse',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--quarter-nops',type=int,default=4)
    p.add_argument('--fast',action='store_true',help='reproduce the noisier 13-pulse speed experiment')
    args=p.parse_args()
    if args.output.exists() and any(args.output.iterdir()): p.error('output must be empty')
    with wave.open(str(args.input),'rb') as wav:
        if (wav.getframerate(),wav.getsampwidth(),wav.getnchannels())!=(8000,1,1):
            p.error('input must be unsigned PCM8, mono, 8000 Hz')
        raw=wav.readframes(wav.getnframes())
    prior=json.loads((HERE/'preview-8k8-loop/report.json').read_bytes())
    if sha(raw)!=prior['pdm_source_pcm']['data_sha256']: raise ValueError('comparison PCM changed')
    padding=(-len(raw))%256; pcm=raw+bytes([128])*padding
    disk,meta=build_disk(pcm,args.quarter_nops if args.fast else 0,steady=not args.fast)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'audiobook-preview.trd').write_bytes(disk)
    (args.output/'soundtrack.pcm.gz').write_bytes(gzip.compress(pcm,mtime=0))
    (args.output/'pcm8k-preview.wav').write_bytes(args.input.read_bytes())
    save(args.output/'player.json',meta)
    print('Verifying live conversion, every PCM value and every output bit over two loops',flush=True)
    proof=verify(args.output,args.fuse)
    times=np.frombuffer(gzip.decompress((args.output/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    oversample=meta['oversample']
    bits,_=reference(pcm,oversample=oversample); count=meta['bits_per_cycle']
    first_times=times[:count+1]; duration=first_times[-1]/CPU_CLOCK
    actual=reconstruct(bits[:count],first_times)
    # Align PCM with the register pipeline, then hold it over the actual slots.
    indices=np.maximum(np.arange(count)-3,0)//oversample
    levels=(np.frombuffer(pcm,dtype=np.uint8)[indices].astype(float)-128)/128
    levels[:3]=-1
    source=reconstruct((levels+1)/2,first_times)
    def audio_filter(samples,lowpass):
        filters='highpass=f=70'
        if lowpass: filters+=',lowpass=f=4500:p=2,lowpass=f=4500:p=2'
        data=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
            '-af',filters,'-ar','44100','-f','f32le','-'],input=samples.astype('<f4').tobytes(),
            capture_output=True,check=True).stdout
        return np.frombuffer(data,'<f4').astype(float)
    signals=dict(original=audio_filter(source,True),beeper=audio_filter(actual,True),wideband=audio_filter(actual,False))
    gain=min(1.,.9/max(float(np.max(abs(s))) for s in signals.values()))
    for name,signal in signals.items(): write_wav(args.output/f'{name}-preview.wav',signal*gain)
    ref=signals['original'][4410:-4410]; candidate=signals['beeper'][4410:-4410]
    metrics=dict(waveform_correlation=float(np.corrcoef(ref,candidate)[0,1]),
        reconstruction_snr_db=float(10*np.log10(np.mean(ref**2)/np.mean((candidate-ref)**2))),
        scope='same actual-timing PCM holds, pipeline aligned, same 4.5 kHz filters; not intelligibility')
    report=dict(complete=True,preview_only=True,date='2026-10-02',baseline_commit='e06cec8',
        source_pcm_wav=str(args.input.resolve()),source_pcm_wav_sha256=sha(args.input.read_bytes()),source_pcm_sha256=sha(raw),
        original_audiobook_sha256=prior['source_sha256'],source_start_seconds=60,source_sample_rate_hz=8000,
        bits_per_pcm_sample=8,channels=1,original_pcm_samples=len(raw),silence_padding_samples=padding,
        stored_pcm_bytes=len(pcm),old_pdm_bytes=98304,saved_payload_bytes=98304-len(pcm),
        disk_storage='raw unsigned PCM8 in PCM0..PCM5; gzip only archives evidence on the host',
        precomputed_pdm_on_disk=False,pdm_buffer_bytes=0,pdm_lookup_table_bytes=0,runtime_disk_reads=0,
        native_pdm_conversion=True,repeat=True,oversample=oversample,quarter_nops=meta['quarter_nops'],steady=meta['steady'],
        modulator=meta['modulator'],timing=proof['fuse'],deterministic_timing=meta['timing'],
        duration_seconds=float(duration),metrics=metrics,preview_common_gain=gain,
        preview_scope='first loop actual port holds; 192 kHz integration, 44100 Hz/16-bit mono WAV; not physical speaker',
        limits=['first-order modulator, unlike the previous host second-order modulator',
                'PCM is held between updates; no band-limited interpolation in Z80',
                'fixed software clock; actual PCM rate and ULA jitter are measured, not assumed to be exactly 8 kHz',
                'standard 7FFD paging; native and machine-specific emulator gates define verified compatibility'],
        producer_sources_sha256_lf={name:sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('pcm_player.py','verify_pcm.py','build_pcm.py','build_pdm.py')},
        artifacts={f.relative_to(args.output).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
            for f in sorted(args.output.rglob('*')) if f.is_file() and f.name!='fuse-stderr.txt'})
    save(args.output/'report.json',report)
    print(json.dumps(dict(duration=duration,timing=proof['fuse'],metrics=metrics,saved_bytes=report['saved_payload_bytes'])),flush=True)


if __name__=='__main__': main()
