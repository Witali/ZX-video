"""Verify unchanged movie streams and exact motion-only Z80 cycle deltas.

Both complete FHS1 and FHF1 runs are required. No delivery/screen timing is
inferred from these reconstruction fixtures. ZX0 inputs are unchanged.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import causal_tile_z80 as machine
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from summarize_spatial_extended import cpu_summary, STATE_SHA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--fhs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--include-retuned-storage', action='store_true')
    args = p.parse_args()
    source = args.fhs.read_bytes()
    model, _, count, mapping, tables = read_header(Reader(source))
    if model != 0 or count != 4971:
        raise ValueError('unexpected source')

    def load(name):
        report = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+name)
        return report

    results = []
    for kind, prefix in (('fhs', 'spatial_extended'), ('fhf', 'fast_fragments_target_300000')):
        old = load(prefix+'_cpu'); new = load('unrolled_motion_'+kind+'_cpu')
        zx0 = load(prefix+'_zx0_cpu')
        if (old['input_sha256'] != new['input_sha256'] or new['input_sha256'] != zx0['input_sha256']
                or any(r['states_sha256'] != STATE_SHA for r in (old, new))
                or (kind == 'fhs' and old['input_sha256'] != sha(source))
                or new.get('unrolled_motion') is not True or old['groups'] != new['groups']):
            raise ValueError('different sources/settings/groups')
        old_summary, new_summary = cpu_summary(old), cpu_summary(new)
        counts = Counter()
        for before, after in zip(old['frames'], new['frames']):
            for field in ('index', 'values', 'bits', 'cache', 'literals', 'intra_tiles', 'intra_modes'):
                if before[field] != after[field]:
                    raise AssertionError('frame stream coverage differs')
            if kind == 'fhf':
                for field in ('fast_kinds', 'fast_tiles', 'fast_unaligned', 'fast_formula_tstates'):
                    if before[field] != after[field]:
                        raise AssertionError('fast tiles differ')
            frame_counts = {int(v): n for v, n in after['motion_vectors'].items()}
            expected_old = sum(machine.motion_tstates(v, OFFSETS)*n for v, n in frame_counts.items())
            expected_new = sum(machine.motion_tstates(v, OFFSETS, unrolled=True)*n for v, n in frame_counts.items())
            if (before['stages'].get('motion', 0) != expected_old or after['stages'].get('motion', 0) != expected_new
                    or after['total_tstates']-before['total_tstates'] != expected_new-expected_old):
                raise AssertionError('per-frame exact motion delta differs')
            for stage in set(before['stages']) | set(after['stages']):
                if stage != 'motion' and before['stages'].get(stage, 0) != after['stages'].get(stage, 0):
                    raise AssertionError('unrelated stage changed')
            counts.update(frame_counts)
        for enabled, report in ((False, old), (True, new)):
            code, labels, listing, regions = machine.build(tables, mapping, OFFSETS, hybrid=True,
                skip_empty=True, intra_above=True, intra_extended=True, fast_fragments=kind == 'fhf', unrolled_motion=enabled)
            if (code.hex() != report['code_hex'] or labels != report['labels'] or listing != report['instruction_listing']
                    or [dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in regions] != report['tables']):
                raise AssertionError('recorded binary differs')
        results.append(dict(kind=kind, old=old_summary, new=new_summary, input_sha256=new['input_sha256'],
            unchanged_zx0=zx0['summary'], video_byte_delta=0, all_other_cpu_stages_identical=True,
            total_delta_tstates=new_summary['total_tstates']-old_summary['total_tstates'],
            two_stage_total_tstates=new_summary['total_tstates']+zx0['summary']['total_tstates'],
            code_delta_bytes=new['code_bytes']-old['code_bytes'], state_delta_bytes=new['state_bytes']-old['state_bytes'],
            vector_histogram=dict(sorted(counts.items()))))
    report = dict(scope=__doc__, baseline_commit='d17f2ab', complete=True, states_sha256=STATE_SHA,
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        old_binaries_unchanged_when_disabled=True, instruction_timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        motion_tstates_by_vector=[dict(vector=v, offset=OFFSETS[v] if v < 81 else None,
            before=machine.motion_tstates(v, OFFSETS), after=machine.motion_tstates(v, OFFSETS, unrolled=True))
            for v in range(1, 82)], results=results)
    if args.include_retuned_storage:
        selection = load('unrolled_fast_selection')
        storage = load('unrolled_fast_zx0')
        row = selection['rows'][0]
        if (selection['states_sha256'] != STATE_SHA or not selection['unrolled_motion']
                or selection['input_sha256'] != sha(source)
                or selection['cpu_report_sha256'] != sha((args.reports/'unrolled_motion_fhs_cpu.json').read_bytes())
                or row['sha256'] != storage['input_sha256'] or row['frames'] != 4971
                or len(storage['blocks']) != storage['blocks_expected']
                or sum(b['decoded_bytes'] for b in storage['blocks']) != row['raw_bytes']
                or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']):
            raise AssertionError('retuned selection/storage differs')
        video = storage['zx0_with_headers_bytes']
        report['retuned_storage'] = dict(input_sha256=row['sha256'], raw_bytes=row['raw_bytes'],
            fast_tiles=row['fast_tiles'], video_bytes=video, blocks=storage['blocks_expected'],
            delta_from_previous_fhf_video_bytes=video-results[1]['unchanged_zx0']['bytes_with_headers'],
            video_plus_ay_bytes=video+77696, preliminary_three_trd_margin_bytes=1937664-video-77696,
            full_pc_decode_verified=True, full_z80_reconstruction_not_yet_included=True,
            full_frame_delivery_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    for row in results:
        print(json.dumps(dict(kind=row['kind'], delta=row['total_delta_tstates'], code_delta=row['code_delta_bytes'],
            new_total=row['new']['total_tstates'], new_maximum=row['new']['max_frame_tstates'],
            new_over_nominal=row['new']['frames_over_nominal_425448'], stages=row['new']['stages'])), flush=True)
    if 'retuned_storage' in report:
        print(json.dumps(report['retuned_storage']), flush=True)


if __name__ == '__main__':
    main()
