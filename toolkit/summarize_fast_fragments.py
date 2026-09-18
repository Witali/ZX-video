"""Verify FHF1 full-movie reconstruction, storage and separate ZX0 CPU runs.

These are CPU fixtures, not a streaming player. No metadata decode, screen
expansion, input refill/paging, AY/ULA/ROM or disk delivery is timed here.
"""
import argparse
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
    p.add_argument('--baseline-fhs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        report = json.loads((args.reports/name).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+name)
        return report

    old = load('spatial_extended_cpu.json')
    new = load('fast_fragments_target_300000_cpu.json')
    targets = load('fast_fragments_targets.json')
    choices = load('fast_fragments_measurements.json')
    target = next(r for r in targets['rows'] if r['name'] == 'target_300000')
    storage = load('fast_fragments_target_300000_zx0.json')
    zx0 = load('fast_fragments_target_300000_zx0_cpu.json')
    old_zx0 = load('spatial_extended_zx0_cpu.json')
    old_storage = load('spatial_predictors_cost_1_zx0.json')
    if (any(r['states_sha256'] != STATE_SHA for r in (old, new, targets, choices))
            or any(r['input_sha256'] != target['sha256'] for r in (new, storage, zx0))
            or old['input_sha256'] != targets['input_sha256']
            or old['input_sha256'] != choices['input_sha256']
            or old['input_sha256'] != old_zx0['input_sha256']
            or old['input_sha256'] != old_storage['input_sha256']):
        raise ValueError('different sources')
    if (sum(g['frames'] for g in new['groups']) != 4971
            or sum(g['bits'] for g in new['groups']) != target['bits']
            or sum(f['bits'] for f in new['frames']) != target['bits']
            or new['summary']['values'] != target['values']
            or new['summary']['fast_kinds'] != target['fast_kinds']
            or sum(f['fast_formula_tstates'] for f in new['frames']) != new['summary']['stages']['fast_fragment']):
        raise AssertionError('frame/bit/fast-tile coverage differs')
    for packed, decoded in ((old_storage, old_zx0), (storage, zx0)):
        if len(packed['blocks']) != len(decoded['blocks']) or len(packed['blocks']) != packed['blocks_expected']:
            raise AssertionError('ZX0 block count differs')
        for i, (a, b) in enumerate(zip(packed['blocks'], decoded['blocks'])):
            if (b['index'] != i or a['sha256'] != b['raw_sha256']
                    or a['decoded_bytes'] != b['raw_bytes'] or a['zx0_bytes'] != b['compressed_bytes']):
                raise AssertionError('ZX0 input coverage differs')
        if (sum(b['tstates'] for b in decoded['blocks']) != decoded['summary']['total_tstates']
                or sum(b['zx0_bytes']+4 for b in packed['blocks']) != packed['zx0_with_headers_bytes']):
            raise AssertionError('ZX0 totals differ')
    data = args.baseline_fhs.read_bytes()
    model, _, count, mapping, tables = read_header(Reader(data))
    if sha(data) != old['input_sha256'] or model != 0 or count != 4971:
        raise ValueError('different binary compatibility input')
    for enabled, cpu in ((False, old), (True, new)):
        code, labels, listing, regions = machine.build(tables, mapping, OFFSETS,
            hybrid=True, skip_empty=True, intra_above=True, intra_extended=True, fast_fragments=enabled)
        if (code.hex() != cpu['code_hex'] or labels != cpu['labels'] or listing != cpu['instruction_listing']
                or [dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in regions] != cpu['tables']):
            raise AssertionError('recorded binary differs')
    rows = [cpu_summary(r) for r in (old, new)]
    storage_rows = []
    selections = choices['rows']+targets['rows']
    for name in ('allowance_16', 'allowance_64', 'target_300000'):
        s = load('fast_fragments_'+name+'_zx0.json')
        choice = next(r for r in selections if r['name'] == name)
        if s['input_sha256'] != choice['sha256'] or len(s['blocks']) != s['blocks_expected']:
            raise AssertionError('storage choice differs')
        video = s['zx0_with_headers_bytes']
        storage_rows.append(dict(name=name, blocks=s['blocks_expected'], video_bytes=video,
            delta_video_bytes=video-old_storage['zx0_with_headers_bytes'], video_plus_ay_bytes=video+77696,
            preliminary_three_trd_margin_bytes=1937664-video-77696))
    before = rows[0]['total_tstates']+old_zx0['summary']['total_tstates']
    after = rows[1]['total_tstates']+zx0['summary']['total_tstates']
    delta = dict(reconstruction_tstates=rows[1]['total_tstates']-rows[0]['total_tstates'],
        zx0_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
        two_stage_tstates_before=before, two_stage_tstates_after=after, two_stage_delta_tstates=after-before,
        code_delta_bytes=new['code_bytes']-old['code_bytes'],
        stages={k: rows[1]['stages'].get(k, 0)-rows[0]['stages'].get(k, 0)
                for k in sorted(set(rows[0]['stages']) | set(rows[1]['stages']))})
    report = dict(scope=__doc__, baseline_commit='15b5638', complete=True,
        states_sha256=STATE_SHA, fast_fragments_disabled_binary_unchanged=True,
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        cpu=rows, zx0_before=old_zx0['summary'], zx0_after=zx0['summary'], delta=delta, storage=storage_rows,
        instruction_timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        fast_body_tstates_including_ret=dict(raw='546 +10*unaligned', repeated_row='541 +10*unaligned',
            two_rows='818 +10*(8-popcount(selector)) +10*unaligned', fill='513 +10*unaligned'),
        caller_and_outer_traversal_not_in_fragment_formula=True,
        unchanged_fhs_retained_intra_dispatch_delta_tstates=27,
        control_stream_calculated_delta_tstates=27*old['summary']['intra_tiles'],
        control_delta_is_formula_not_full_run=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    compact = {k: v for k, v in rows[1].items() if k != 'worst_frames'}
    print(json.dumps(dict(delta=delta, storage=storage_rows, new=compact), indent=2))


if __name__ == '__main__':
    main()
