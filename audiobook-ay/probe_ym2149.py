"""Render a single 50 Hz LPC-to-YM2149 candidate with Spectrum-style mono mixing."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from probe_lpc2 import formant_frames, HERE, ay_interrupt, quality, AyFrame
from build_preview import save, sha
from lpc2_stream import read_stream
from player import build_disk


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lpc-source', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--source-pcm', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    previous = json.loads((HERE/'lpc-probe/report.json').read_bytes())
    old_analysis = json.loads((HERE/'lpc-probe/lpc2-analysis.json').read_bytes())
    raw = args.source_pcm.read_bytes()
    if sha(raw) != old_analysis['input_pcm_sha256']:
        raise ValueError('source PCM does not match the accepted 24-second excerpt')
    if sha(args.lpc_source.read_bytes()) != old_analysis['source_sha256']:
        raise ValueError('LPC codec changed')
    if args.output.exists() and any(args.output.iterdir()):
        p.error('output must be new or empty')
    args.output.mkdir(parents=True, exist_ok=True)
    lpc = args.output/'lpc'
    lpc.mkdir()
    subprocess.run([args.node, str(HERE/'lpc2_bridge.js'), str(args.lpc_source.resolve()),
                    str(args.source_pcm.resolve()), str(lpc.resolve()), 'detail50'], check=True)
    analysis = json.loads((lpc/'lpc2-analysis.json').read_bytes())
    check = read_stream((lpc/'reference.lp2').read_bytes())
    assert check['quantized_frames_sha256'] == analysis['quantized_frames_sha256']
    assert check['hop'] == 160 and check['frames'] == 1200 and check['samples'] == 192000
    # Use the emulator's measured YM DAC table for fixed (non-envelope) volumes.
    core = (HERE/'vendor/ayumi-js/ayumi.js').read_text()
    levels = np.array(json.loads(re.search(r'const YM_DAC_TABLE = (\[[\s\S]*?\])',core)[1]))[1::2]
    samples = np.frombuffer(raw, '<f4').astype(float)
    candidate, _ = formant_frames(analysis['frames'], samples, hop=160, clock_hz=1773450, levels=levels)
    packed = b''.join(f.serialize() for f in candidate)
    registers = b''.join(ay_interrupt.registers(f) for f in candidate)
    (args.output/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
    baseline = gzip.decompress((HERE/'lpc-probe/soundtrack.ay9.gz').read_bytes())
    baseline_frames = [AyFrame.deserialize(baseline[i:i+9]) for i in range(0,len(baseline),9)]
    baseline_regs = b''.join(ay_interrupt.registers(f) for f in baseline_frames)
    assert sha(baseline_regs) == previous['registers_sha256']
    signals = {}
    for name,regs in (('baseline',baseline_regs),('ym2149',registers)):
        register_path = args.output/f'{name}-registers.gz'
        register_path.write_bytes(gzip.compress(regs, mtime=0))
        pcm = args.output/f'{name}.f32'
        subprocess.run([args.node, str(HERE/'render_ym2149.js'), str(register_path.resolve()),
                        str(pcm.resolve()), '50', str((args.output/f'{name}-render.json').resolve())],check=True)
        signals[name] = np.frombuffer(pcm.read_bytes(), '<f4').astype(float)

    def resample(blob):
        return np.frombuffer(subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le',
            '-ar','8000','-ac','1','-i','-','-ar','44100','-f','f32le','-'], input=blob,
            capture_output=True,check=True).stdout,'<f4').astype(float)

    signals['original'] = resample(raw)
    signals['lpc-reference'] = resample((lpc/'lpc2-reference.f32').read_bytes())
    if any(len(s)!=1058400 or not np.isfinite(s).all() for s in signals.values()):
        raise ValueError('incomplete or nonfinite rendered audio')
    levels_rms = {name:float(np.sqrt(np.mean(s*s))) for name,s in signals.items()}
    common = min(.1,*(.9*levels_rms[name]/max(float(np.max(abs(s))),1e-12) for name,s in signals.items()))
    peaks = {}
    for name,s in signals.items():
        matched = s*common/max(levels_rms[name],1e-12)
        peaks[name] = float(np.max(abs(matched)))
        quality.write_wav(args.output/f'{name}-preview.wav',matched,44100)
    # Same band metric as before, recomputed at a common 22050 Hz rate.
    def metric_signal(s):
        return np.frombuffer(subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le',
            '-ar','44100','-ac','1','-i','-','-ar','22050','-f','f32le','-'],input=s.astype('<f4').tobytes(),
            capture_output=True,check=True).stdout,'<f4').astype(float)
    features = {name:quality.features(metric_signal(s),22050,10,240) for name,s in signals.items()}
    metrics = {name:quality.compare(features['original'],f) for name,f in features.items() if name!='original'}
    disk, metadata = build_disk(registers)
    (args.output/'audiobook-preview.trd').write_bytes(disk)
    save(args.output/'player.json',metadata)
    report = dict(complete=True,preview_only=True,source_sha256=previous['source_sha256'],
        source_pcm_sha256=sha(raw),start_seconds=60,duration_seconds=24,ticks=1200,update_rate_hz=50,
        chip='YM2149',clock_hz=1773450,mixing='equal mono A+B+C; no stereo expansion',
        three_tone_generators=True,shared_noise_generators=1,high_rate_pcm_volume_output=False,
        offline_lpc_profile=analysis['config'],lpc_bytes=check['payload_bits']//8+36+(check['payload_bits']%8!=0),
        independent_lpc_bitstream_check=check,baseline_listener_accepted=False,
        candidate_listener_accepted=False,selected_as_quality_improvement=False,
        decision='50 Hz hardware-constrained listening candidate; full LPC clarity is not preserved by assumption',
        metrics=metrics,metrics_scope='signal proxies only; not a perceptual speech score',
        native_lpc_decoder=False,pcm_dac_player=False,disk_timing_verified=False,
        player_hot_path_delta_tstates=0,registers_sha256=sha(registers),packed_sha256=sha(packed),
        equal_rms_preview=common,preview_peak=peaks,
        limitations=['Ayumi chip simulation, not a physical recording or exact analogue circuit model',
            'Preview uses atomic 50 Hz updates; TRD writes R0..R10 sequentially within each interrupt field',
            'LPC runs only on the host; the Spectrum replays precomputed chip register states'],
        producer_sources_sha256_lf={name:sha((HERE/name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('probe_ym2149.py','render_ym2149.js','probe_lpc2.py','lpc2_bridge.js','lpc2_stream.py')},
        artifacts={f.relative_to(args.output).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
            for f in sorted(args.output.rglob('*')) if f.is_file() and f.suffix!='.f32'})
    save(args.output/'report.json',report)
    print(json.dumps(dict(metrics=metrics,lpc_bytes=report['lpc_bytes'],peak=peaks,
        ticks=report['ticks'],rms=common)),flush=True)


if __name__ == '__main__':
    main()
