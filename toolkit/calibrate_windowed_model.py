"""Calibrate window costs from archived foreground boundaries, without Fuse.

This reads existing evidence only. It does not qualify a release or identify
the untraced audio/IRQ/keepalive components as deterministic CPU time.
"""
import argparse
from functools import cache
import gzip
import json
from pathlib import Path
from statistics import mean

from build_fap3_trd import sha
from calibrated_windowed_model import CalibratedModel, frame_costs
from profile_integrated_timing import analyze, stats
from windowed_zx0_planner import FIELD, PERIOD

ROOT = Path(__file__).parent


@cache
def archive_index(folder):
    manifest = json.loads((folder/'manifest.json').read_bytes())
    if not manifest['complete']:
        raise ValueError('complete evidence required')
    return {entry['file']: entry for entry in manifest['files']}


def archived_json(folder, name):
    packed = (folder/(name+'.gz')).read_bytes()
    raw = gzip.decompress(packed)
    entry = archive_index(folder)[name+'.gz']
    if (sha(packed) != entry['sha256'] or sha(raw) != entry['decoded_sha256']
            or len(raw) != entry['decoded_bytes']):
        raise ValueError('archived input changed')
    return json.loads(raw)


def read_case(folder, part, cpu):
    def read(name):
        return archived_json(folder, f'part{part:02}.{name}')
    run, metadata = read('json'), read('metadata.json')
    if metadata['raw_sha256'] != cpu['raw_sha256'] or metadata['frames'] != cpu['checked_frames']:
        raise ValueError('different frame CPU reference')
    return run, metadata, analyze(run, metadata, cpu)['frames']


def foreground_costs(run, frames, packet_sizes):
    stages = [f['stages'] for f in frames]
    before_prepare, before_draw, ready_transfers = [], [], []
    for i in range(1, len(frames)):
        current, previous = stages[i], stages[i-1]
        # Draw i-1, read i if required, service, then reconstruct i.
        if i > 1:
            gap = current['prepare']['start'] - max(previous['draw']['end'], current['metadata']['end'])
            if gap < 0:
                raise ValueError('foreground preparation order differs')
            before_prepare.append(dict(frame=i, tstates=gap))
        # Only sample the draw-entry gap when foreground work had already
        # overrun the previous publication, so no background quantum fits.
        finish = current['prepare']['end']
        if i+1 < len(frames) and stages[i+1]['metadata']['end'] < current['draw']['start']:
            finish = max(finish, stages[i+1]['metadata']['end'])
        if finish >= run['publications'][i-1]['tstate']:
            gap = current['draw']['start']-finish
            if gap < 0:
                raise ValueError('foreground drawing order differs')
            before_draw.append(dict(frame=i, tstates=gap))
        # With no empty wait, the transfer is packet transport, not ZX0 or
        # input acquisition. Remaining elapsed time can include IRQ/ULA.
        transfer = current['transfer']
        if not transfer['empty_wait'] and not transfer['disk_service']:
            ready_transfers.append(dict(frame=i, bytes=packet_sizes[i], tstates=transfer['elapsed']))
    return dict(before_prepare=before_prepare, before_draw=before_draw, ready_transfers=ready_transfers)


def fit_copy(rows):
    if len(rows) < 2:
        raise ValueError('at least two ready transfers required')
    x, y = mean(r['bytes'] for r in rows), mean(r['tstates'] for r in rows)
    denominator = sum((r['bytes']-x)**2 for r in rows)
    if not denominator:
        raise ValueError('copy samples must have different lengths')
    slope = sum((r['bytes']-x)*(r['tstates']-y) for r in rows)/denominator
    intercept = y-slope*x
    if slope < 16 or intercept < 0:
        raise ValueError('copy fit contradicts the native LDI lower cost')
    return dict(tstates_per_byte=slope, fixed_tstates=intercept, samples=len(rows),
                residual_absolute=stats([abs(r['tstates']-(slope*r['bytes']+intercept)) for r in rows]))


def inspect():
    profile_path = ROOT/'fast_reservoir_profile.json'
    cpu_path = ROOT/'cached_huffman_lookahead_cpu.json'
    profile, cpu = [json.loads(p.read_bytes()) for p in (profile_path, cpu_path)]
    volumes = []
    for part, reference in enumerate(profile['volumes'], 1):
        run, metadata, frames = read_case(ROOT/'fast_zx0_player_evidence', part, cpu['volumes'][part-1])
        costs = foreground_costs(run, frames, [f['packet_bytes'] for f in reference['frames']])
        volumes.append(dict(part=part, copy_fit=fit_copy(costs['ready_transfers']),
            before_prepare=stats([r['tstates'] for r in costs['before_prepare']]),
            before_draw=stats([r['tstates'] for r in costs['before_draw']]), samples=costs))
    return dict(complete=True, release=False, player_changed=False, player_tstates_delta=0,
        volumes=volumes, references={path.name: sha(path.read_bytes()) for path in (profile_path, cpu_path)})


def errors(predicted, run, window_frames=64):
    origin = run['publications'][0]['tstate']
    actual = [p['tstate']-origin for p in run['publications']]
    if len(actual) != len(predicted):
        raise ValueError('publication coverage differs')
    windows = []
    for start in range(0, len(actual), window_frames):
        stop = min(start+window_frames, len(actual))
        predicted_late = [max(0, predicted[i]-i*PERIOD) for i in range(start, stop)]
        actual_late = [max(0, actual[i]-i*PERIOD) for i in range(start, stop)]
        windows.append(dict(start=start, end_exclusive=stop,
            predicted_late_frames=sum(t > 64 for t in predicted_late),
            actual_late_frames=sum(t > 64 for t in actual_late),
            absolute_error=stats([abs(actual[i]-predicted[i]) for i in range(start, stop)]),
            falsely_predicted_on_time=sum(a > 64 and p <= 64 for a, p in zip(actual_late, predicted_late)),
            falsely_predicted_late=sum(a <= 64 and p > 64 for a, p in zip(actual_late, predicted_late))))
    return dict(estimated_only=True, actual_late_frames=run['nominal_late_frames'],
        predicted_late_frames=sum(t-i*PERIOD > 64 for i, t in enumerate(predicted)),
        actual_max_late_fields=run['max_late_fields'],
        predicted_max_late_fields=max((t-i*PERIOD)//FIELD for i, t in enumerate(predicted)),
        absolute_error=stats([abs(a-p) for a, p in zip(actual, predicted)]),
        falsely_predicted_on_time=sum(w['falsely_predicted_on_time'] for w in windows),
        falsely_predicted_late=sum(w['falsely_predicted_late'] for w in windows), windows=windows)


def benchmark(report):
    all_costs = {key: [r for v in report['volumes'] for r in v['samples'][key]]
                 for key in ('ready_transfers', 'before_draw', 'before_prepare')}
    calibration = dict(copy=fit_copy(all_costs['ready_transfers']),
        draw_entry_tstates=round(mean(r['tstates'] for r in all_costs['before_draw'])),
        prepare_entry_tstates=round(mean(r['tstates'] for r in all_costs['before_prepare'])),
        fitted_from='Fast baseline foreground events only; no candidate publication labels',
        producer_step_overhead_tstates=0,
        limitations=['Entry means mix control, AY, keepalive and IRQ; these were not separately traced.',
                     'Phase-dependent ULA, disk rotation and variable decoder demands remain approximate.'])
    profile = json.loads((ROOT/'fast_reservoir_profile.json').read_bytes())
    probe = json.loads((ROOT/'fast_zx0_tokens_probe.json').read_bytes())
    report['references']['fast_zx0_tokens_probe.json'] = sha((ROOT/'fast_zx0_tokens_probe.json').read_bytes())
    cases = []
    for name, folder in (
            ('fast', 'fast_zx0_player_evidence'), ('unweighted', 'fast_token_player_evidence'),
            ('pressure4', 'pressure_token_evidence/weight4'), ('pressure16', 'pressure_token_evidence/weight16'),
            ('windowed', 'windowed_player_evidence')):
        rows = []
        report['references'][folder+'/manifest.json'] = sha((ROOT/folder/'manifest.json').read_bytes())
        for part in (1, 2, 3):
            directory = ROOT/folder
            run = archived_json(directory, f'part{part:02}.json')
            metadata = archived_json(directory, f'part{part:02}.metadata.json')
            if (not run['complete'] or run['errors'] or run['failure'] or not run['trace_nonce_exact']
                    or run['trd_sha256'] != metadata['trd_sha256'] or run['frames'] != metadata['frames']
                    or len(run['publications']) != metadata['frames']):
                raise ValueError('incomplete final reference run')
            chosen = metadata.get('fast_token_selection', {}).get('names')
            if chosen is None:
                if name != 'fast':
                    raise ValueError('selected token names missing')
                chosen = ['min0']*len(probe['volumes'][part-1]['blocks'])
            trials = {}
            for label, moves, transport, entries in (
                    ('original', False, False, False), ('metadata_at_read', True, False, False),
                    ('measured_transport', True, True, False), ('measured_entries', True, True, True)):
                frames = frame_costs(profile['volumes'][part-1]['frames'], calibration,
                    move_metadata=moves, fit_transport=transport, include_entries=entries)
                model = CalibratedModel(frames, probe['volumes'][part-1]['blocks'])
                model.run(chosen)
                trials[label] = errors(model.publications, run)
            rows.append(dict(part=part, models=trials))
        cases.append(dict(name=name, volumes=rows))
    report.update(calibration=calibration, evaluations=cases,
        new_trds_built=0, new_fuse_runs=0, metadata_stage_moved_to_packet_read=True,
        release_timing_verified=False,
        source_sha256_lf={name: sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) for name in
            ('calibrate_windowed_model.py', 'calibrated_windowed_model.py', 'windowed_zx0_planner.py',
             'profile_integrated_timing.py', 'test_calibrated_windowed_model.py')})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'windowed_model_calibration.json')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    report = benchmark(inspect())
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif report != json.loads(args.output.read_bytes()):
        raise ValueError('saved calibration differs')
    for volume in report['volumes']:
        print(json.dumps({k: v for k, v in volume.items() if k != 'samples'}), flush=True)
    print(json.dumps(report['calibration']), flush=True)
    for case in report['evaluations']:
        print(json.dumps(dict(name=case['name'], models={label: dict(
            actual=[v['models'][label]['actual_late_frames'] for v in case['volumes']],
            predicted=[v['models'][label]['predicted_late_frames'] for v in case['volumes']],
            error=sum(v['models'][label]['absolute_error']['total'] for v in case['volumes']))
            for label in case['volumes'][0]['models']})), flush=True)


if __name__ == '__main__':
    main()
