"""Check saved frame-profile evidence and aggregate it without rerunning Z80.

This validates pinned files, frame/stage/instruction totals, the earlier
per-frame baseline minus 499 T, and native-mask candidate arithmetic.
It does not repeat pixel comparisons or measure playback, IRQ, ULA or disk.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(name):
    return json.loads((ROOT / name).read_bytes())


def pins(report):
    for name, expected in report['source_sha256'].items():
        require(sha((ROOT / name).read_bytes()) == expected, f'source differs: {name}')


def audit():
    profile = read('frame_hotspot_profile.json')
    dense = read('dense_band_threshold_profile.json')
    baseline = read('inline_huffman_patches_cpu.json')
    pins(profile)
    pins(dense)
    require(profile['complete'] and profile['full_compact_and_both_native_exact'], 'partial profile')
    require(not profile['release'] and not profile['implemented_optimization'], 'wrong profile scope')
    require(profile['player_cpu_delta_tstates'] == profile['stream_delta_bytes'] == 0, 'profile changed player')
    require(profile['baseline_report_sha256'] == sha((ROOT / 'inline_huffman_patches_cpu.json').read_bytes()),
            'baseline differs')
    require(profile['states_sha256'] == baseline['states_sha256'], 'states differ')
    require(dense['complete'] and dense['cpu_formula_only'] and not dense['implemented'], 'wrong probe scope')
    require(dense['manifest_sha256'] == sha((ROOT / 'streaming_zx0_input_evidence.json').read_bytes()),
            'stream manifest differs')
    stages = Counter()
    indexed = Counter()
    motion_entries = 0
    histogram = Counter()
    by_part = []
    for volume, old in zip(profile['volumes'], baseline['volumes'], strict=True):
        require(all(volume[k] == old[k] for k in ('part', 'start', 'end', 'raw_sha256')), 'volume differs')
        frames = volume['frames']
        require(len(frames) == volume['checked_frames'] == volume['end'] - volume['start'], 'missing frames')
        from_frames = Counter()
        for local, (frame, previous) in enumerate(zip(frames, old['frames'], strict=True)):
            require(frame['frame'] == volume['start'] + local, 'frame order differs')
            require(frame['tstates'] == previous['tstates'] - 499, 'per-frame baseline differs')
            require(sum(frame['stages'].values()) == frame['tstates'], 'frame stages differ')
            from_frames.update(frame['stages'])
        from_instructions = Counter()
        for row in volume['instruction_histogram']:
            require(row['count'] > 0 and row['total'] == row['count'] * row['tstates'], 'bad instruction count')
            require(row['bank'] in (-1, 6, 7), 'unexpected code bank')
            from_instructions[row['stage']] += row['total']
            key = row['bank'], row['address'], row['instruction'], row['stage']
            histogram[key] += row['total']
            if row['stage'] == 'reconstruct/motion' and row['instruction'] == 'PUSH HL':
                motion_entries += row['count']
            if '(IX' in row['instruction'] or '(IY' in row['instruction']:
                require(row['tstates'] == 19 and row['instruction'].startswith('LD '), 'unexpected indexed operation')
                indexed['loads'] += row['count']
                indexed['tstates'] += row['total']
        require(from_frames == from_instructions == Counter(volume['stages']), 'stage totals differ')
        require(sum(from_frames.values()) == volume['tstates'], 'volume total differs')
        stages.update(from_frames)
        by_part.append(dict(part=volume['part'], frames=len(frames), tstates=volume['tstates']))
    require(sum(v['frames'] for v in by_part) == profile['checked_frames'] == 4221, 'incomplete movie')
    require(sum(stages.values()) == profile['tstates'], 'profile total differs')
    phases = Counter()
    for stage, total in stages.items():
        phases[stage.split('/')[0]] += total

    band_hist = Counter()
    groups = Counter()
    hl = read('hl_mask_reader_summary.json')
    for volume, reference, frames in zip(dense['volumes'], hl['volumes'], by_part, strict=True):
        require(volume['part'] == reference['part'] == frames['part'], 'mask part differs')
        require(volume['stream_sha256'] == reference['hl']['stream_sha256'], 'mask stream differs')
        require(len(volume['frames']) == reference['hl']['frames'] == frames['frames'], 'mask frame count differs')
        actual = Counter()
        for index, frame in enumerate(volume['frames']):
            require(index == frame['local_frame'] and len(frame['bands']) == 18, 'missing bands')
            for band, (common, marked, odd) in enumerate(frame['bands'], 1):
                require(odd == band % 2 and 0 <= common <= 255 and 0 <= marked <= 32, 'bad band')
                actual[common, marked, odd] += 1
        stored = Counter({(r['common'], r['marked'], r['odd']): r['count'] for r in volume['band_histogram']})
        require(actual == stored, 'band histogram differs')
        group = Counter({int(k): v for k, v in volume['partial_band_group_histogram'].items()})
        require(sum(group.values()) == 4 * sum(n for (c, m, o), n in actual.items() if c != 255),
                'partial-group count differs')
        require(sum(k.bit_count() * n for k, n in group.items()) ==
                sum(m * n for (c, m, o), n in actual.items() if c != 255), 'partial-group pixels differ')
        band_hist.update(actual)
        groups.update(group)
    require(dense['frames'] == 4221 and len(dense['candidates']) == 37, 'partial candidate scan')
    for candidate in dense['candidates']:
        mask = candidate['mask']
        require(mask.bit_count() <= 2, 'invalid candidate mask')
        per_volume = []
        deltas = []
        accepted = 0
        for volume in dense['volumes']:
            local_deltas = []
            for frame in volume['frames']:
                delta = 126 if mask else 0
                for common, marked, odd in frame['bands']:
                    if common != 255 and common | mask == 255:
                        require(marked >= 24, 'candidate with a zero mask byte needs another formula')
                        delta += 5853 + 4 * odd - 261 * marked
                        accepted += 1
                local_deltas.append(delta)
            per_volume.append(sum(local_deltas))
            deltas.extend(local_deltas)
        require(candidate['delta_tstates'] == sum(deltas) and candidate['per_volume_delta'] == per_volume,
                'candidate total differs')
        require(candidate['additional_dense_bands'] == accepted and
                candidate['slower_frames'] == sum(d > 0 for d in deltas) and
                candidate['max_frame_penalty'] == max(deltas), 'candidate distribution differs')
    eight = dense['dense_eight_cell_candidate']
    require(eight['baseline_group_tstates'] == 8 * (4 + 17 + 254 + 4 + 4), 'group baseline differs')
    require(eight['candidate_helper_tstates'] == 15 + 32 * 51 + 4 * 22 + 3 * 48 + 40, 'helper estimate differs')
    nonzero = sum(n for b, n in groups.items() if b)
    require(eight['full_groups'] == groups[255] and eight['nonzero_groups'] == nonzero, 'group frequency differs')
    require(eight['predicted_delta_tstates'] == 17 * nonzero - 345 * groups[255], 'group estimate differs')
    marked_hist = Counter()
    for (_, marked, _), count in band_hist.items():
        marked_hist[marked] += count
    return dict(scope=__doc__, complete_saved_evidence_audit=True, release=False,
        source_sha256=sha(Path(__file__).read_bytes()),
        report_sha256={name: sha((ROOT / name).read_bytes()) for name in
                       ('frame_hotspot_profile.json', 'dense_band_threshold_profile.json')},
        frames=profile['checked_frames'], total_tstates=profile['tstates'], volumes=by_part,
        phases=[dict(phase=p, tstates=n, percent=100*n/profile['tstates']) for p,n in phases.most_common()],
        stages=[dict(stage=s, tstates=n) for s,n in stages.most_common()],
        hottest_instructions=[dict(bank=b, address=a, instruction=i, stage=s, tstates=n)
                              for (b,a,i,s),n in histogram.most_common(30)],
        indexed_loads=dict(indexed), indexed_load_only_gross_saving_at_12_t=12*indexed['loads'],
        nonzero_motion_target_setup=dict(implemented=False, entries=motion_entries,
            baseline_tstates=45*motion_entries, proposed_tstates=28*motion_entries,
            estimated_delta_tstates=-17*motion_entries,
            assumption='Move the shared target load into phase zero; use EXX/LD DE,(target)/EXX for phases 2/4/6 with no extra saves. Not assembled or IRQ-tested.'),
        marked_cells_per_band=dict(sorted(marked_hist.items())),
        dense_candidates=dense['candidates'], dense_eight_cell_candidate=eight)


def main():
    result = audit()
    target = ROOT / 'frame_hotspot_summary.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: result[k] for k in ('frames', 'total_tstates', 'phases', 'indexed_loads',
                                           'indexed_load_only_gross_saving_at_12_t')}, indent=2))


if __name__ == '__main__':
    main()
