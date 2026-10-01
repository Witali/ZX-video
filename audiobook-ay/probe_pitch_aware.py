"""Compare one pitch-preserving AY50 speech candidate with the rejected mapper."""
from __future__ import annotations
import argparse,gzip,json,re,subprocess
from pathlib import Path
import numpy as np
from pitch_aware_ay import encode
from probe_lpc2 import HERE,ay_interrupt,quality
from build_preview import save,sha
from player import build_disk


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--node',required=True); p.add_argument('--ffmpeg',required=True)
    p.add_argument('--source-pcm',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    prior=json.loads((HERE/'ym2149-preview/report.json').read_bytes())
    analysis=json.loads((HERE/'ym2149-preview/lpc/lpc2-analysis.json').read_bytes())
    raw=args.source_pcm.read_bytes()
    if sha(raw)!=prior['source_pcm_sha256']: raise ValueError('source PCM changed')
    if args.output.exists() and any(args.output.iterdir()): p.error('output must be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    core=(HERE/'vendor/ayumi-js/ayumi.js').read_text()
    levels=np.array(json.loads(re.search(r'const YM_DAC_TABLE = (\[[\s\S]*?\])',core)[1]))[1::2]
    frames,details=encode(analysis['frames'],np.frombuffer(raw,'<f4').astype(float),levels)
    packed=b''.join(f.serialize() for f in frames)
    regs=b''.join(ay_interrupt.registers(f) for f in frames)
    (args.output/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed,mtime=0))
    save(args.output/'fit.json',details)
    signals={}
    for name,data in (('candidate',regs),('previous',gzip.decompress((HERE/'ym2149-preview/ym2149-registers.gz').read_bytes()))):
        regpath=args.output/f'{name}-registers.gz'; regpath.write_bytes(gzip.compress(data,mtime=0))
        out=args.output/f'{name}.f32'
        subprocess.run([args.node,str(HERE/'render_ym2149.js'),str(regpath.resolve()),str(out.resolve()),'50',
            str((args.output/f'{name}-render.json').resolve())],check=True)
        signals[name]=np.frombuffer(out.read_bytes(),'<f4').astype(float)
    def resample(data,old,new):
        return np.frombuffer(subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(old),
            '-ac','1','-i','-','-ar',str(new),'-f','f32le','-'],input=data,capture_output=True,check=True).stdout,'<f4').astype(float)
    signals['original']=resample(raw,8000,44100)
    assert all(len(s)==1058400 and np.isfinite(s).all() for s in signals.values())
    rms={n:float(np.sqrt(np.mean(s*s))) for n,s in signals.items()}
    common=min(.1,*(.9*rms[n]/max(float(np.max(abs(s))),1e-12) for n,s in signals.items()))
    for n,s in signals.items(): quality.write_wav(args.output/f'{n}-preview.wav',s*common/max(rms[n],1e-12),44100)
    features={n:quality.features(resample(s.astype('<f4').tobytes(),44100,22050),22050,10,240) for n,s in signals.items()}
    metrics={n:quality.compare(features['original'],features[n]) for n in ('previous','candidate')}
    disk,metadata=build_disk(regs)
    (args.output/'audiobook-preview.trd').write_bytes(disk); save(args.output/'player.json',metadata)
    report=dict(complete=True,preview_only=True,date='2026-10-02',baseline_commit='5c9200a',
        source_sha256=prior['source_sha256'],source_pcm_sha256=sha(raw),start_seconds=60,duration_seconds=24,
        analysis_sha256=sha((HERE/'ym2149-preview/lpc/lpc2-analysis.json').read_bytes()),
        chip='YM2149',clock_hz=1773450,update_rate_hz=50,ticks=len(frames),
        mixing='equal mono sum; three tone generators; one shared noise source',
        method='channel A anchors LPC F0; B/C jointly fit harmonic square-wave power; no musical-note quantization',
        analysis_window_ms=32,pitch_anchor_floor='0.01 * weighted target sum / weighted fundamental template sum',fit_frequency_emphasis_exponent=.35,
        maximum_harmonic_index=24,voiced_frames=sum(d['kind']=='voiced' for d in details),
        noise_frames=sum(d['kind']=='noise' for d in details),silence_frames=sum(d['kind']=='silence' for d in details),
        envelope_enabled=False,high_rate_pcm_volume_output=False,player_hot_path_delta_tstates=0,
        native_lpc_decoder=False,disk_timing_verified=False,candidate_listener_accepted=False,
        decision='bounded listening candidate; no intelligibility claim',metrics=metrics,equal_rms_preview=common,
        metrics_scope='signal proxies; source passage and chip renderer match previous build',
        registers_sha256=sha(regs),packed_sha256=sha(packed),
        producer_sources_sha256_lf={n:sha((HERE/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('pitch_aware_ay.py','probe_pitch_aware.py','render_ym2149.js','player.py')},
        artifacts={f.relative_to(args.output).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
            for f in sorted(args.output.rglob('*')) if f.is_file() and f.suffix!='.f32'})
    save(args.output/'report.json',report)
    print(json.dumps(dict(metrics=metrics,voiced_frames=report['voiced_frames'],noise_frames=report['noise_frames'])),flush=True)


if __name__=='__main__': main()
