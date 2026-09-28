"""Adapt saved block/frame measurements to automatic sliding-window selection.

No alternative images or emulator runs are made. Frame-stage elapsed costs
are held fixed from the reference run; the candidate schedule is an estimate.
This adapter accepts arbitrary volume/frame counts with matching report data.
"""
import argparse
import json
from pathlib import Path
import time

from build_fap3_trd import sha
from windowed_zx0_planner import Model, PERIOD, select

ROOT = Path(__file__).parent


def plan(probe, profile, baseline, window_frames=64):
    if not all(r['complete'] for r in (probe, profile, baseline)): raise ValueError('complete inputs required')
    volumes = []
    for candidates, reference, built in zip(probe['volumes'], profile['volumes'], baseline['volumes'], strict=True):
        if candidates['part'] != reference['part'] or reference['part'] != built['part']:
            raise ValueError('volume order differs')
        if candidates['stream_sha256'] != built['stream_sha256']: raise ValueError('different baseline stream')
        rows = reference['frames']
        if len(rows) != built['frames']: raise ValueError('different frame coverage')
        frames = [dict(packet_end=f['raw_position']+f['packet_bytes'],
            draw_tstates=f['stages']['draw']['elapsed']-f['stages']['draw']['disk_service'],
            prepare_tstates=sum(f['stages'][s]['elapsed']-f['stages'][s]['disk_service'] for s in ('metadata', 'prepare')),
            copy_tstates=16*f['packet_bytes']+800) for f in rows]
        # Two sectors may be consumed by physical sector interleave.
        capacity = candidates['capacity_bytes']-4*256
        result = select(frames, candidates['blocks'], capacity, window_frames=window_frames,
            disk_tstates_per_byte=candidates['disk_charge_tstates_per_byte'])
        model = Model(frames, candidates['blocks'], disk_tstates_per_byte=candidates['disk_charge_tstates_per_byte'])
        model.run(['min0']*len(candidates['blocks']))
        result['baseline_model'] = dict(estimated_score=list(model.score(0)),
            actual_late_frames=sum(bool(f['late_fields']) for f in rows),
            actual_max_late_fields=max(f['late_fields'] for f in rows),
            estimated_publications=model.publications,
            note='Calibration diagnostic only; model and actual runs have different contention/demand timing.')
        volumes.append(dict(part=built['part'], selection=result))
    return dict(complete=True, release=False, scope=__doc__, volumes=volumes,
        player_instruction_delta_tstates=0, decoded_pixels_and_ay_unchanged=True,
        alternative_trds_built=0, alternative_fuse_runs=0, actual_publication_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key, default in (('probe', 'fast_zx0_tokens_probe.json'), ('profile', 'fast_reservoir_profile.json'),
                         ('baseline-build', 'fast_zx0_player_build.json')):
        p.add_argument('--'+key, type=Path, default=ROOT/default)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--window-frames', type=int, default=64)
    args = p.parse_args()
    if args.output.exists(): p.error('refuse to overwrite evidence')
    paths = (args.probe, args.profile, args.baseline_build)
    began = time.perf_counter()
    result = plan(*(json.loads(p.read_bytes()) for p in paths), window_frames=args.window_frames)
    result['planning_seconds'] = time.perf_counter()-began
    result['references'] = {p.name: sha(p.read_bytes()) for p in paths}
    result['source_sha256_lf'] = {n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
        ('plan_windowed_tokens.py', 'windowed_zx0_planner.py', 'benchmark_adaptive_zx0.py')}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(planning_seconds=result['planning_seconds'], volumes=[dict(part=v['part'],
        **{k: v['selection'][k] for k in ('stream_bytes', 'decoder_tstates', 'estimated_score',
            'local_comparisons', 'maximum_evaluated_horizon_frames')},
        baseline_estimate=v['selection']['baseline_model']['estimated_score'],
        baseline_actual_late_frames=v['selection']['baseline_model']['actual_late_frames'])
        for v in result['volumes']])), flush=True)


if __name__ == '__main__': main()
