"""Automatically plan, build and verify one window-selected prepared movie set.

Input is a matching encoded movie, frame-cost profile and measured block
candidate cache. Selection never builds alternative TRDs. Only the selected
set is built and then cold-played through EOF in Fuse. This entry point does
not yet replace media decoding/encoding in convert_video.py.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from benchmark_bank_local_zx0 import disk_blocks
from benchmark_faster_zx0 import fixture
from benchmark_inplace_streaming import finish
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from build_inplace_keepalive import prime
from fast_token_player import Builder
from plan_windowed_tokens import plan
from profile_fap3 import summarize_fuse
from test_fap3_disk import verify_swaps

ROOT = Path(__file__).parent


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key, default in (('baseline-build', 'fast_zx0_player_build.json'),
                         ('probe', 'fast_zx0_tokens_probe.json'), ('profile', 'fast_reservoir_profile.json')):
        p.add_argument('--'+key, type=Path, default=ROOT/default)
    for key in ('raw-directory', 'states', 'zx0', 'fuse', 'output'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--read-cache', type=Path, action='append', default=[])
    p.add_argument('--window-frames', type=int, default=64)
    p.add_argument('--timeout', type=float, default=300)
    a = p.parse_args()
    if a.output.exists(): p.error('output directory must be new')
    paths = (a.probe, a.profile, a.baseline_build)
    probe, profile, old = [json.loads(path.read_bytes()) for path in paths]
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if sha(states.tobytes()) != old['contract']['states_sha256']: raise ValueError('different frame states')
    if len(old['volumes']) != len(old['contract']['ends']): raise ValueError('different volume coverage')
    if not a.fuse.is_file() or not a.zx0.is_file(): raise ValueError('Fuse and ZX0 executable files required')
    # The measured candidate cache must refer to exactly the current generator.
    for name, digest in probe['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest:
            raise ValueError(('candidate implementation changed', name))
    a.output.mkdir(parents=True)
    began = time.perf_counter(); selection = plan(probe, profile, old, a.window_frames)
    selection['planning_seconds'] = time.perf_counter()-began
    selection['references'] = {path.name: sha(path.read_bytes()) for path in paths}
    save(a.output/'selection.json', selection)
    print(f'Window selection finished in {selection["planning_seconds"]:.3f}s; building one set', flush=True)
    decisions = [{k: v['selection'][k] for k in ('names', 'stream_bytes', 'decoder_tstates', 'selected_counts')}
                 for v in selection['volumes']]
    contract = dict(old['contract'], version='resident-window-token-1',
        window_frames=a.window_frames, selections=decisions)
    fingerprint = b'AYH1IPW1'+bytes.fromhex(sha(json.dumps(contract, sort_keys=True).encode()))[:6]
    report = dict(complete=False, release=False, scope=__doc__, contract=contract,
        alternative_trds_built=0, alternative_fuse_runs=0, final_trds_built=0, final_fuse_runs=0,
        source_references={path.name: sha(path.read_bytes()) for path in paths}, volumes=[])
    native = dict(complete=False, release=False, volumes=[])
    timing = dict(complete=False, release=False, all_nominal_deadlines_met=False, disks=[])
    def checkpoint():
        save(a.output/'build.json', report); save(a.output/'native-cpu.json', native); save(a.output/'timing.json', timing)
    records = []; start = 0
    try:
        for part, end in enumerate(contract['ends'], 1):
            print(f'Final selected disk {part}: frames {start}..{end-1}', flush=True)
            raw_path = a.raw_directory/f'volume-{part}.raw'; raw = raw_path.read_bytes()
            if sha(raw) != contract['raw_sha256'][part-1]: raise ValueError('different encoded movie')
            b = Builder(raw, states, a.zx0.resolve(), a.output/'zx0', series_fingerprint=fingerprint,
                token_volume=probe['volumes'][part-1], token_selection=decisions[part-1], **contract['options'])
            b.ends = contract['ends']; b.read_cache = a.read_cache
            image, m = b.volume(start, end, part)
            if image is None: raise ValueError(('selected volume exceeds capacity', part, m['used_sectors']))
            stem = f'ZX-video-huffman-preview_part{part:02}'
            image_path = a.output/(stem+'.trd'); meta_path = a.output/(stem+'.json')
            image_path.write_bytes(image); save(meta_path, m); report['final_trds_built'] += 1
            _, stream, blocks = disk_blocks(a.output, part); video, sound = b.separated(start, end)
            if b''.join(chunk for _, chunk in blocks) != video: raise ValueError('TRD video differs')
            row = dict(part=part, frames=end-start, used_sectors=m['used_sectors'], free_sectors=m['free_sectors'],
                video_bytes=m['video_bytes'], video_sectors=m['video_sectors'], video_start_sector=m['video_start_sector'],
                trd_sha256=sha(image), metadata_sha256=sha(meta_path.read_bytes()), stream_sha256=sha(stream),
                raw_video_sha256=sha(video), audio_sha256=sha(sound), fast_zx0=m['fast_zx0'],
                fast_token_selection=m['fast_token_selection'], independently_bootable=m['independently_bootable'],
                exact_video_field_roundtrip=True)
            for key in ('frames', 'raw_video_sha256', 'audio_sha256'):
                if row[key] != old['volumes'][part-1][key]: raise ValueError('different decoded content')
            row.update(check_cold(image, m, b.expected_banks)); row.update(prime(image, m, states))
            report['volumes'].append(row)
            records.append(dict(part=part, file=image_path.name, metadata=meta_path.name, sha256=sha(image),
                frame_start=start, frame_end_exclusive=end))
            # Native verification runs only the selected stream, not every trial.
            h, layout = fixture(stream, m['video_start_sector'], 'fast')
            nr = dict(part=part, trd_sha256=sha(image), stream_sha256=sha(stream), layout=layout, blocks=h.results)
            native['volumes'].append(nr)
            for index, (payload, raw_block) in enumerate(blocks):
                actual = h.block(payload, raw_block, index)
                expected = probe['volumes'][part-1]['blocks'][index]['variants'][decisions[part-1]['names'][index]]
                if actual['payload_sha256'] != expected['payload_sha256'] or actual['decoder_tstates'] != expected['decoder_tstates']:
                    raise ValueError('selected CPU result differs from local candidate')
            nr['summary'] = finish(h); checkpoint()
            # One final full EOF check per output disk; never inside search.
            target = a.output/f'part{part:02}.json'
            command = [sys.executable, str(ROOT/'measure_fap3_fuse.py'), '--fuse', str(a.fuse.resolve()),
                '--trd', str(image_path.resolve()), '--metadata', str(meta_path.resolve()), '--raw', str(raw_path.resolve()),
                '--states', str(a.states.resolve()), '--output', str(target.resolve()), '--timeout', str(a.timeout),
                '--trace-pipeline', '--trace-fields']
            completed = subprocess.run(command, capture_output=True, text=True)
            (a.output/f'part{part:02}.log').write_text(completed.stdout+completed.stderr, encoding='utf-8')
            completed.check_returncode(); report['final_fuse_runs'] += 1
            run = json.loads(target.read_bytes())
            if not run['complete'] or run['failure'] or run['errors'] or run['trd_sha256'] != sha(image):
                raise ValueError('final playback incomplete or inexact')
            gates = summarize_fuse(run)
            timing['disks'].append(dict(part=part, report=target.name, report_sha256=sha(target.read_bytes()), **gates))
            checkpoint(); start = end
            print(f'Disk {part}: {run["nominal_late_frames"]} late frames, {run["audio_underruns"]} AY underruns', flush=True)
        save(a.output/'volumes.json', records)
        verify_swaps(a.output, a.output/'swaps.json')
        report.update(complete=True, mocked_rom_swaps=json.loads((a.output/'swaps.json').read_bytes()))
        native['complete'] = True
        native['totals'] = {k: sum(v['summary'][k] for v in native['volumes']) for k in
            ('producer_tstates', 'decoder_tstates', 'total_tstates', 'sector_reads', 'carry_copy_bytes')}
        timing.update(complete=True, all_nominal_deadlines_met=all(r['nominal_deadlines_met'] for r in timing['disks']),
            fallback_met=all(r['fallback_one_field_met'] for r in timing['disks']),
            ay_50hz_met=all(r['actual_ay_50hz'] for r in timing['disks']))
        if start != len(states) or report['final_trds_built'] != len(records) or report['final_fuse_runs'] != len(records):
            raise AssertionError('final set coverage differs')
    except Exception as exc: report['failure'] = repr(exc); raise
    finally:
        names = ('optimize_prepared_player.py', 'plan_windowed_tokens.py', 'windowed_zx0_planner.py',
            'fast_token_player.py', 'zx0_speed.py', *old['source_sha256_lf'].keys())
        report['source_sha256_lf'] = {n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in names}
        checkpoint()
    print(json.dumps(dict(output=str(a.output), disks=len(records), **{k: timing[k] for k in
        ('all_nominal_deadlines_met', 'fallback_met', 'ay_50hz_met')})), flush=True)


if __name__ == '__main__': main()
