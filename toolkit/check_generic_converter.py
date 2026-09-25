"""Reproduce generic media -> TRD -> CPU/Fuse tests using generated sources."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from convert_video import executable, write_json
from test_fap3_disk import verify_swaps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True, help='new test directory')
    for tool in ('ffmpeg', 'ffprobe', 'zx0'): p.add_argument('--'+tool)
    p.add_argument('--fuse', type=Path)
    p.add_argument('--trdos-rom', type=Path)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--noise-frames', type=int, default=48, help='384 exercises automatic size-based splitting')
    p.add_argument('--only-noise', action='store_true')
    p.add_argument('--inline-matches', action='store_true')
    p.add_argument('--startup-delta', action='store_true')
    p.add_argument('--fast-noop-scan', action='store_true')
    p.add_argument('--static-cache-borders', action='store_true')
    p.add_argument('--carry-huffman', action='store_true')
    p.add_argument('--irq-safe-paging', action='store_true')
    args = p.parse_args()
    if args.noise_frames < 1: p.error('--noise-frames must be positive')
    programs = {name: executable(getattr(args, name), name) for name in ('ffmpeg', 'ffprobe', 'zx0')}
    args.output.mkdir(parents=True, exist_ok=False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    def generate(name, inputs, encoding):
        path = args.output/name
        subprocess.run([programs['ffmpeg'], '-v', 'error', '-nostdin', '-y', *inputs, *encoding, str(path)], check=True)
        return path
    sources = [
        (generate('single.mp4', ['-f', 'lavfi', '-i', 'color=black:s=48x80:r=25:d=0.04'],
                  ['-c:v', 'mpeg4']), 1, [], 'single black frame; no audio'),
        (generate('portrait.mkv', ['-f', 'lavfi', '-i', 'color=white:s=90x120:r=25:d=0.36'],
                  ['-c:v', 'ffv1']), 3, [], 'portrait; no audio; letterbox geometry'),
        (generate('colour.avi', ['-f', 'lavfi', '-i', 'testsrc2=s=192x108:r=25:d=1',
                  '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=22050:duration=1'],
                  ['-c:v', 'mpeg4', '-q:v', '2', '-c:a', 'pcm_s16le']),
         9, ['--max-frames-per-disk', '4'], 'mono sound; three disks and two automatic continuations'),
        (generate('anamorphic.mov', ['-f', 'lavfi', '-i', 'color=white:s=64x64:r=25:d=0.24'],
                  ['-vf', 'setsar=2', '-c:v', 'mpeg4']), 2, [], 'non-square input pixels; display aspect 2:1'),
        (generate('audio-tail.mkv', ['-f', 'lavfi', '-i', 'color=red:s=64x64:r=25:d=0.24',
                  '-f', 'lavfi', '-i', 'sine=frequency=330:sample_rate=22050:duration=0.5'],
                  ['-c:v', 'ffv1', '-c:a', 'pcm_s16le']), 5, [], 'audio outlasts video; retained through EOF'),
    ]
    noise = np.random.default_rng(20260921).integers(0, 256, (args.noise_frames, 72, 128, 3), dtype=np.uint8)
    rgb = args.output/'noise.rgb'; rgb.write_bytes(noise.tobytes())
    noisy_video = generate('noise.avi', ['-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '128x72',
        '-framerate', '25/3', '-i', str(rgb)], ['-c:v', 'ffv1'])
    if args.only_noise: sources = []
    sources.append((noisy_video, args.noise_frames, [], 'high entropy; runtime disk reads beyond the 64 KiB preload'))
    report = dict(complete=False, release=False, generator_seed=20260921, inline_matches=args.inline_matches,
                  startup_delta=args.startup_delta, fast_noop_scan=args.fast_noop_scan, irq_safe_paging=args.irq_safe_paging,
                  static_cache_borders=args.static_cache_borders,carry_huffman=args.carry_huffman,cases=[])
    write_json(args.report, report)
    for source, expected_frames, extra, objective in sources:
        out = args.output/(source.stem+'-out')
        command = [sys.executable, str(Path(__file__).with_name('convert_video.py')), str(source),
                   '--output', str(out), '--verify', 'fuse' if args.fuse else 'cpu', *extra]
        for name, path in programs.items(): command += ['--'+name, path]
        if args.fuse: command += ['--fuse', str(args.fuse)]
        if args.trdos_rom: command += ['--disk-profile', 'trdos503', '--trdos-rom', str(args.trdos_rom)]
        if args.inline_matches: command += ['--inline-matches']
        if args.startup_delta: command += ['--startup-delta']
        if args.fast_noop_scan: command += ['--fast-noop-scan']
        if args.static_cache_borders: command += ['--static-cache-borders']
        if args.carry_huffman: command += ['--carry-huffman']
        if args.irq_safe_paging: command += ['--irq-safe-paging']
        subprocess.run(command, check=True)
        meta = json.loads((out/'conversion.json').read_text(encoding='utf-8'))
        if meta['frames'] != expected_frames: raise AssertionError((source.name, meta['frames'], expected_frames))
        if source.stem == 'portrait':
            image = np.fromfile(out/'work/frames.rgb', dtype=np.uint8).reshape(-1, 72, 128, 3)[0]
            ys, xs = np.where(image.any(axis=2))
            if (xs.max()-xs.min()+1, ys.max()-ys.min()+1) != (54, 72): raise AssertionError('portrait stretched/cropped')
        if source.stem == 'anamorphic':
            image = np.fromfile(out/'work/frames.rgb', dtype=np.uint8).reshape(-1, 72, 128, 3)[0]
            ys, xs = np.where(image.any(axis=2))
            if (xs.max()-xs.min()+1, ys.max()-ys.min()+1) != (128, 64): raise AssertionError('sample aspect lost')
        timing = json.loads((out/'timing.json').read_text(encoding='utf-8'))
        if source.stem == 'noise' and args.fuse and not sum(d['disk_timing']['runtime_disk_reads'] for d in timing['disks']):
            raise AssertionError('stress clip did not exercise runtime disk delivery')
        verify_swaps(out, out/'swaps.json')
        case = dict(source=source.name, objective=objective, frames=meta['frames'], ay_ticks=meta['ay_ticks'],
            disks=len(meta['volumes']), source_sha256=meta['source_sha256'],
            stream_sha256=meta['stream_sha256'], timing=timing,
            swaps=json.loads((out/'swaps.json').read_text(encoding='utf-8')),
            cpu=[])
        case['filtered_boot_tables']=sum(any(s.get('startup_delta') for s in json.loads((out/r['metadata']).read_text())['sections'])
            for r in meta['volumes'])
        for record in timing['disks']:
            cpu = json.loads((out/record['cpu_report']).read_text(encoding='utf-8'))
            case['cpu'].append({k: cpu[k] for k in ('complete', 'frames', 'foreground_tstates',
                'foreground_stages', 'irq_tstates', 'idle_tstates', 'played_ay_ticks',
                'full_compact_and_native_comparison', 'nominal_frame_budget_tstates')})
        report['cases'].append(case)
        write_json(args.report, report)
    report['complete'] = True
    write_json(args.report, report)


if __name__ == '__main__':
    main()
