"""Verify full retained-value table training and actual ZX0 storage coverage.

Optional complete CPU evidence applies only to the best FHF1 clustered16
variant. No other variant or complete frame-delivery performance is inferred.
"""
import argparse
import json
from pathlib import Path

import causal_tile_z80 as machine
from probe_hybrid_tiles import OFFSETS
from probe_lossless_layouts import sha
from summarize_spatial_extended import cpu_summary, STATE_SHA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--cpu-report', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    def load(name):
        value = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not value['complete']:
            raise ValueError('incomplete '+name)
        return value
    baseline = load('unrolled_fast_cpu')
    base_storage = load('unrolled_fast_zx0')
    results = []
    for kind in ('fhf', 'fhc'):
        trained = load('retuned_fragment_contexts_'+kind)
        old_storage = base_storage if kind == 'fhf' else load('raw_intra_zx0')
        if trained['states_sha256'] != STATE_SHA or trained['input_sha256'] != old_storage['input_sha256']:
            raise AssertionError('different input')
        for choice in trained['rows']:
            name = 'retuned_contexts_'+kind+'_'+choice['name']+'_zx0'
            storage = load(name)
            if (not choice['accepted'] or choice['frames'] != 4971 or not choice['exact_causal_frame_decode']
                    or storage['input_sha256'] != choice['sha256'] or storage['input_bytes'] != choice['raw_bytes']
                    or len(storage['blocks']) != storage['blocks_expected']
                    or sum(b['decoded_bytes'] for b in storage['blocks']) != choice['raw_bytes']
                    or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']):
                raise AssertionError('storage coverage differs')
            code, _, _, _ = machine.build([bytes(t) for t in choice['tables']], bytes(choice['context_map']), OFFSETS,
                hybrid=True, skip_empty=True, intra_above=True, intra_extended=True,
                fast_fragments=True, unrolled_motion=True, raw_intra=kind == 'fhc')
            old_code = baseline['code_hex'] if kind == 'fhf' else load('raw_intra_summary')['code_hex']
            if code.hex() != old_code:
                raise AssertionError('decoder binary changed with tables')
            video = storage['zx0_with_headers_bytes']
            results.append(dict(format=kind.upper()+'1', variant=choice['name'], input_sha256=choice['sha256'],
                raw_bytes=choice['raw_bytes'], video_bytes=video, blocks=storage['blocks_expected'],
                delta_from_same_format_bytes=video-old_storage['zx0_with_headers_bytes'],
                delta_from_unrolled_fhf_bytes=video-base_storage['zx0_with_headers_bytes'],
                video_plus_ay_bytes=video+77696, preliminary_three_trd_margin_bytes=1937664-video-77696,
                huffman_bits=choice['bits'], huffman_bit_delta=choice['bits']-trained['before']['bits'],
                long_values=choice['long_values'], long_value_delta=choice['long_values']-trained['before']['long_values'],
                prefix_bank_bytes=choice['prefix_bank_bytes'], decoder_binary_unchanged=True))
    report = dict(scope=__doc__, complete=True, states_sha256=STATE_SHA, rows=results,
        full_pc_decode_verified=True, no_additional_pixel_changes=True, player_changed=False,
        integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        full_z80_reconstruction_verified=False)
    if args.cpu_report:
        cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
        selected = next(row for row in results if row['format'] == 'FHF1' and row['variant'] == 'clustered16')
        zx0 = load('retuned_contexts_fhf_clustered16_zx0_cpu')
        if (cpu['input_sha256'] != selected['input_sha256'] or cpu['code_hex'] != baseline['code_hex']
                or zx0['input_sha256'] != selected['input_sha256']
                or zx0['storage_report_sha256'] != sha((args.reports/'retuned_contexts_fhf_clustered16_zx0.json').read_bytes())
                or len(zx0['blocks']) != selected['blocks']
                or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
            raise AssertionError('CPU source/coverage differs')
        current = cpu_summary(cpu)
        for before, after in zip(baseline['frames'], cpu['frames']):
            for key in ('values', 'intra_tiles', 'intra_modes', 'fast_tiles', 'fast_kinds', 'motion_vectors', 'cache'):
                if before[key] != after[key]:
                    raise AssertionError('frame modes differ: '+key)
            for stage in set(before['stages']) | set(after['stages']):
                if stage not in ('huffman', 'fast_fragment') and before['stages'].get(stage, 0) != after['stages'].get(stage, 0):
                    raise AssertionError('non-entropy stage changed')
        report.update(full_z80_reconstruction_verified=True, cpu_variant='FHF1 clustered16', cpu=current,
            reconstruction_delta_tstates=current['total_tstates']-baseline['summary']['total_tstates'],
            zx0_cpu=zx0['summary'], two_stage_total_tstates=current['total_tstates']+zx0['summary']['total_tstates'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'cpu'}))


if __name__ == '__main__':
    main()
