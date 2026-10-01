"""Compare one 10 ms/exact-repeat LPC2 profile against the accepted 24 s baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'toolkit'))
import compare_ay_fidelity as quality
from build_preview import save, sha
from lpc2_stream import read_stream


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--lpc-source', type=Path, required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline_dir = HERE/'lpc-probe'
    previous = json.loads((baseline_dir/'report.json').read_bytes())
    previous_analysis = json.loads((baseline_dir/'lpc2-analysis.json').read_bytes())
    with args.input.open('rb') as source:
        source_hash = hashlib.file_digest(source, 'sha256').hexdigest()
    if source_hash != previous['source_sha256']:
        raise ValueError('source differs from the accepted baseline')
    if sha(args.lpc_source.read_bytes()) != previous_analysis['source_sha256']:
        raise ValueError('LPC codec source changed; comparison would be confounded')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be new or empty')
    args.output.mkdir(parents=True, exist_ok=True)
    raw = subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(previous['start_seconds']),
        '-i', str(args.input.resolve()), '-t', str(previous['duration_seconds']), '-map', '0:a:0',
        '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    if sha(raw) != previous_analysis['input_pcm_sha256']:
        raise ValueError('decoded source excerpt differs from baseline')
    pcm = args.output/'source.f32'
    pcm.write_bytes(raw)
    analyses, checks, signals = {}, {}, {}

    def resample(blob):
        return np.frombuffer(subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le',
            '-ar', '8000', '-ac', '1', '-i', '-', '-ar', '22050', '-f', 'f32le', '-'],
            input=blob, capture_output=True, check=True).stdout, '<f4').astype(float)

    signals['original'] = resample(raw)
    for profile in ('baseline', 'detail'):
        folder = args.output/profile
        folder.mkdir()
        subprocess.run([args.node, str(HERE/'lpc2_bridge.js'), str(args.lpc_source.resolve()),
                        str(pcm.resolve()), str(folder.resolve()), profile], check=True)
        analysis = json.loads((folder/'lpc2-analysis.json').read_bytes())
        blob = (folder/'reference.lp2').read_bytes()
        if profile == 'baseline' and sha(blob) != previous['artifacts']['reference.lp2']['sha256']:
            raise ValueError('bridge no longer reproduces the accepted baseline stream')
        if analysis['extracted_core_sha256'] != previous_analysis['extracted_core_sha256']:
            raise ValueError('DSP core changed')
        check = read_stream(blob)
        if check['quantized_frames_sha256'] != analysis['quantized_frames_sha256']:
            raise ValueError('independent frame reader disagrees with JavaScript decoder')
        if check['samples'] != len(raw)//4 or check['hop'] != (160 if profile == 'baseline' else 80):
            raise ValueError('invalid duration or update rate')
        decoded = (folder/'lpc2-reference.f32').read_bytes()
        if len(decoded) != len(raw) or not np.isfinite(np.frombuffer(decoded, '<f4')).all():
            raise ValueError('incomplete or nonfinite output')
        signals[profile] = resample(decoded)
        analyses[profile] = {k:v for k,v in analysis.items() if k != 'frames'}
        checks[profile] = check
        checks[profile]['finite_output_samples'] = len(decoded)//4

    # Metrics use the same 10 Hz features as the archived comparison.
    count = round(previous['duration_seconds']*10)
    reference = quality.features(signals['original'], 22050, 10, count)
    metrics = {name:quality.compare(reference, quality.features(signal, 22050, 10, count))
               for name,signal in signals.items() if name != 'original'}
    for key,value in metrics['baseline'].items():
        if isinstance(value, float) and abs(value-previous['metrics']['lpc2-reference'][key]) > 1e-10:
            raise ValueError(f'baseline metric changed: {key}')
    levels = {name:float(np.sqrt(np.mean(signal**2))) for name,signal in signals.items()}
    common = min(.1, *(0.9*levels[name]/max(float(np.max(abs(signal))), 1e-12)
                      for name,signal in signals.items()))
    preview_checks = {}
    for name,signal in signals.items():
        matched = signal*common/max(levels[name], 1e-12)
        quality.write_wav(args.output/f'{name}-preview.wav', matched, 22050)
        preview_checks[name] = dict(samples=len(matched), rms=float(np.sqrt(np.mean(matched**2))),
                                    peak=float(np.max(abs(matched))))

    report = dict(complete=True, host_codec_comparison_only=True, native_lpc_decoder=False,
        native_timing_verified=False, ay_output_verified=False, candidate_listener_accepted=False,
        baseline_listener_accepted=True, source_sha256=source_hash,
        start_seconds=previous['start_seconds'], duration_seconds=previous['duration_seconds'],
        objective='preserve faster speech transitions using 10 ms frames and exact-only coefficient repeats',
        profiles=analyses, independent_bitstream_checks=checks, metrics=metrics,
        metrics_scope='signal proxies, not a measurement of intelligibility or perceived quality',
        equal_rms_preview=common, preview_checks=preview_checks,
        player_hot_path_changed=False, player_hot_path_delta_tstates=0,
        native_cost_note='No native LPC decoder exists. LPC polynomial updates double; no CPU feasibility claim.',
        producer_sources_sha256_lf={name:sha((HERE/name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('compare_lpc2_detail.py','lpc2_bridge.js','lpc2_stream.py')},
        artifacts={f.relative_to(args.output).as_posix():dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
            for f in sorted(args.output.rglob('*')) if f.is_file() and f.suffix != '.f32'})
    save(args.output/'report.json', report)
    print(json.dumps(dict(metrics=metrics, bytes={k:v['stats']['actualBytes'] for k,v in analyses.items()},
                         verified=checks, preview_checks=preview_checks)), flush=True)


if __name__ == '__main__':
    main()
