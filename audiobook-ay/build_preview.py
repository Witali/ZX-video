"""Convert a bounded audiobook excerpt with the existing movie AY50 synthesizer."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolkit'))
import ay_fidelity as ay
import ay_interrupt
from build_long_video_trd import AyFrame
import compare_ay_fidelity as quality
from player import build_disk


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--start', type=float, default=0)
    p.add_argument('--duration', type=float, default=120)
    p.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = p.parse_args()
    ticks = round(args.duration * 50)
    if args.start < 0 or not 1 <= ticks <= 5 * (16384 // 11):
        p.error('start must be nonnegative; resident preview duration must be 0.02..148.9 seconds')
    if abs(ticks / 50 - args.duration) > 1e-8:
        p.error('duration must be a multiple of 20 ms')
    if abs(round(args.start * 50) / 50 - args.start) > 1e-8:
        p.error('start must be a multiple of 20 ms')
    if not args.ffmpeg:
        p.error('install FFmpeg or pass --ffmpeg')
    if args.output.exists() and any(args.output.iterdir()):
        p.error('output must be a new or empty directory')
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.input.resolve(strict=True)
    # One second of context avoids artificial analysis edges when --start > 0.
    rate = 22050
    context = min(args.start, 1.0)
    command = [args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(args.start - context),
               '-i', str(source), '-t', str(args.duration + context + 1),
               '-map', '0:a:0', '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']
    result = subprocess.run(command, capture_output=True, check=True)
    samples = np.frombuffer(result.stdout, '<f4').astype(float)
    first = round(context * rate)
    required = first + round(args.duration * rate)
    if len(samples) < required:
        raise ValueError('source ends before the requested excerpt; no silent padding is substituted')
    count = (len(samples) + 440) // 441
    print(f'Analysing {ticks} preview ticks with the unchanged movie synthesizer', flush=True)
    magnitude, rms = ay.spectra(samples, rate, 50, count)
    periods, volumes, notes, noise, explained, fit = ay.arrange_for_chip(magnitude, rms, rate)
    all_frames = [AyFrame(tuple(map(int, a)), tuple(map(int, b)), int(c))
                  for a, b, c in zip(periods, volumes, noise)]
    lo = round(context * 50)
    frames = all_frames[lo:lo + ticks]
    original = samples[first:required]
    # Preview starts with the same fresh AY phase as a cold player start.
    rendered = ay.render(frames, 50, rate)
    levels = [float(np.sqrt(np.mean(s * s))) for s in (original, rendered)]
    target = min(.12, *(0.9 * r / max(float(np.max(np.abs(s))), 1e-12)
                       for s, r in zip((original, rendered), levels)))
    for name, signal, rms_value in zip(('original', 'ay'), (original, rendered), levels):
        quality.write_wav(args.output / f'{name}-preview.wav', signal * target / max(rms_value, 1e-12), rate)
    metrics = quality.compare(quality.features(original, rate, 10, (ticks + 4) // 5),
                              quality.features(rendered, rate, 10, (ticks + 4) // 5))
    packed = b''.join(frame.serialize() for frame in frames)
    registers = b''.join(ay_interrupt.registers(frame) for frame in frames)
    (args.output / 'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
    disk, metadata = build_disk(registers)
    (args.output / 'audiobook-preview.trd').write_bytes(disk)
    save(args.output / 'player.json', metadata)
    with source.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(complete=True, preview_only=True, full_audiobook=False,
        source=str(source), source_sha256=source_hash, start_seconds=args.start,
        duration_seconds=args.duration, ticks=ticks, update_rate_hz=50,
        source_mix='FFmpeg mono downmix', mode='unchanged refined movie AY synthesizer',
        square_fit=fit, analysis_context_before_seconds=context,
        analysis_context_after_seconds=(len(samples)-required)/rate,
        noise_ticks=sum(bool(f.noise_period) for f in frames),
        raw_packed_bytes=len(packed), raw_register_bytes=len(registers),
        registers_sha256=sha(registers), packed_sha256=sha(packed),
        preview_model='band-limited AY tones / sampled noise; not analogue or cycle-exact audio',
        equal_rms_preview=target, metrics=metrics,
        metrics_scope='spectral/rhythm proxies, not speech intelligibility or percent accuracy',
        disk_timing_verified=False, hardware_tested=False,
        artifacts={path.name: dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
                   for path in sorted(args.output.iterdir()) if path.is_file()})
    save(args.output / 'report.json', report)
    print(json.dumps(dict(duration_seconds=args.duration, ticks=ticks, metrics=metrics,
                          disks=1, used_sectors=metadata['capacity']['used_sectors'])), flush=True)


if __name__ == '__main__':
    main()
