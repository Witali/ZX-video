"""Exercise generic media -> five-level CB41 -> independent disks and Fuse.

Optional saved movie inputs prove byte-identical representation of the
already verified full movie, without requantization or another disk sweep.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from convert_video import executable, write_json
from generic_cell_codebook import representation


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'report', 'trdos-rom'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('ffmpeg', 'ffprobe', 'zx0', 'lzsa'):
        p.add_argument('--'+name)
    p.add_argument('--fuse', type=Path)
    p.add_argument('--only', help='run one named generated case')
    p.add_argument('--movie-states', type=Path)
    p.add_argument('--movie-measurements', type=Path)
    a = p.parse_args()
    if bool(a.movie_states) != bool(a.movie_measurements):
        p.error('supply both saved movie inputs or neither')
    tools = {n: executable(getattr(a, n), n) for n in ('ffmpeg', 'ffprobe', 'zx0', 'lzsa')}
    a.output.mkdir(parents=True, exist_ok=False)
    report = dict(complete=False, release=False, baseline_commit='9885483', cases=[],
                  native_instruction_delta_tstates=0, actual_fuse_requested=bool(a.fuse))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    write_json(a.report, report)
    cases = [
        ('single', ['-f', 'lavfi', '-i', 'color=black:s=48x80:r=25:d=0.04'], ['-c:v', 'ffv1'], 1, []),
        ('portrait', ['-f', 'lavfi', '-i', 'color=white:s=90x120:r=25:d=0.36'], ['-c:v', 'ffv1'], 3, []),
        ('colour', ['-f', 'lavfi', '-i', 'testsrc2=s=192x108:r=25:d=1',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=22050:duration=1'],
                    ['-c:v', 'ffv1', '-c:a', 'pcm_s16le'], 9, ['--max-frames-per-disk', '4']),
        ('anamorphic', ['-f', 'lavfi', '-i', 'color=white:s=64x64:r=25:d=0.24'],
                      ['-vf', 'setsar=2', '-c:v', 'ffv1'], 2, []),
        ('audio-tail', ['-f', 'lavfi', '-i', 'color=red:s=64x64:r=25:d=0.24',
                       '-f', 'lavfi', '-i', 'sine=frequency=330:sample_rate=22050:duration=0.5'],
                       ['-c:v', 'ffv1', '-c:a', 'pcm_s16le'], 5, []),
    ]
    for name, inputs, encoding, count, extra in cases:
        if a.only and name != a.only:
            continue
        source = a.output/(name+'.mkv')
        subprocess.run([tools['ffmpeg'], '-v', 'error', '-nostdin', '-y', *inputs,
                        *encoding, str(source)], check=True)
        target = a.output/(name+'-out')
        command = [sys.executable, str(Path(__file__).with_name('convert_video.py')), str(source),
            '--output', str(target), '--video-codec', 'cb41', '--trdos-rom', str(a.trdos_rom),
            '--verify', 'fuse' if a.fuse else 'cpu', *extra]
        for key, value in tools.items():
            command += ['--'+key, value]
        if a.fuse:
            command += ['--fuse', str(a.fuse)]
        with (a.output/(name+'.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'{name} failed: see {a.output/(name+".log")}')
        conversion = json.loads((target/'conversion.json').read_bytes())
        quality = json.loads((target/'video-quality.json').read_bytes())
        timing = json.loads((target/'timing.json').read_bytes())
        assert conversion['complete'] and conversion['frames'] == count
        assert conversion['ay_ticks'] == 6*count and conversion['brightness_levels'] == 5
        assert quality['refinement_never_increased_rgb_error']
        assert sum(r['frames'] for r in conversion['volumes']) == count
        assert all(r['free_sectors'] >= 0 for r in conversion['volumes'])
        assert timing['complete'] and len(timing['disks']) == len(conversion['volumes'])
        assert all(d['cold']['dirty_ram_boot_exact'] and d['cpu_all_native_screens_exact'] for d in timing['disks'])
        if a.fuse:
            assert conversion['timing_verified'] and timing['all_nominal_deadlines_met']
            assert all(d['full_fuse_screens_exact'] for d in timing['disks'])
        geometry = None
        if name in ('portrait', 'anamorphic'):
            rgb = np.fromfile(target/'work/frames.rgb', dtype=np.uint8).reshape(-1, 72, 128, 3)[0]
            yy, xx = np.where(rgb.any(axis=2))
            geometry = [int(xx.min()), int(xx.max())+1, int(yy.min()), int(yy.max())+1]
            assert geometry == ([37, 91, 0, 72] if name == 'portrait' else [0, 128, 4, 68]), geometry
        if name == 'colour':
            swaps = json.loads((target/'disk-swaps.json').read_bytes())
            assert len(swaps) == 2 and all(s['bootstrap_ram_exact'] for s in swaps)
        row = dict(name=name, frames=count, ay_ticks=count*6, volumes=len(conversion['volumes']),
            source_sha256=digest(source), conversion_sha256=digest(target/'conversion.json'),
            native_screens_exact=True, dirty_cold_boots_exact=True,
            actual_fuse_nominal_deadlines_met=conversion['timing_verified'],
            compared_full_fuse_bytes=count*6912 if a.fuse else 0,
            native_geometry=geometry, used_sectors=[v['used_sectors'] for v in conversion['volumes']])
        report['cases'].append(row)
        write_json(a.report, report)
        print(json.dumps(row), flush=True)
    if a.movie_states:
        with np.load(a.movie_states, allow_pickle=False) as saved:
            frames = saved['five_states']
        measured = json.loads(a.movie_measurements.read_bytes())
        checks = []
        for volume in measured['volumes']:
            lo, hi = volume['start'], volume['end']
            encoded = representation(frames, lo, hi)
            original = a.movie_measurements.parent/f'volume-{volume["volume"]}'/'codebook.raw'
            assert encoded['raw'] == original.read_bytes()
            assert encoded['raw_sha256'] == volume['raw_sha256']
            assert encoded['screen_sha256'] == volume['screen_sha256']
            checks.append(dict(start=lo, end=hi, raw_sha256=encoded['raw_sha256'],
                               bytes=len(encoded['raw']), full_host_screens_exact=True))
            print(f'Movie volume {volume["volume"]}: exact {hi-lo} frames and CB41 bytes', flush=True)
        assert sum(c['end']-c['start'] for c in checks) == len(frames)
        report['movie'] = dict(frames=len(frames), volumes=checks,
            states_archive_sha256=digest(a.movie_states), measurements_sha256=digest(a.movie_measurements),
            compressed_streams_or_root_images_changed=False, playback_evidence_reused='cell_codebook_balanced_profile.json')
    report['source_sha256_lf'] = {n:hashlib.sha256(Path(__file__).with_name(n).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        for n in ('generic_cell_codebook.py', 'convert_cb41.py', 'convert_video.py', 'check_generic_cb41.py')}
    report['complete'] = True
    write_json(a.report, report)


if __name__ == '__main__':
    main()
