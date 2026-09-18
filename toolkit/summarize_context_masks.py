"""Join full mask-layout sizes and unchanged sparse-primitive CPU formulas.

Sparse totals use the previously executed 412+8*n primitive formula, not
a new full reader. ZX0 CPU is separately measured by actual instructions.
No permutation-reader, caller setup, paging, IRQ, ULA or disk costs are
included; inverse bit transposition is a PC verification operation only.
"""
import argparse
import json
from pathlib import Path

from probe_context_masks import split, permute, EXPECTED_SHA
from probe_motion_metadata import sparse
from probe_lossless_layouts import sha


def mask_cost(groups, mode):
    packets = nonzero = 0
    for n, _, masks, _ in groups:
        masks = permute(masks, n, mode)
        flags, _ = sparse(masks)
        for data in (masks, flags):
            packets += (len(data)+7)//8
            nonzero += sum(bool(b) for b in data)
    return dict(packets=packets, nonzero_bytes=nonzero, tstates=412*packets+8*nonzero)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpc', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.fpc.read_bytes()
    if sha(data) != EXPECTED_SHA:
        raise ValueError('unexpected FPC2')
    _, groups = split(data)

    def load(name):
        report = json.loads((args.reports/name).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError(f'incomplete {name}')
        return report

    profile = load('context_masks_measurements.json')
    before = load('prediction_64_zx0_measurements.json')
    old_cpu = load('prediction_64_zx0_cpu_measurements.json')
    cpu = load('context_masks_group_split_zx0_cpu_measurements.json')
    if old_cpu['input_sha256'] != sha(data) or old_cpu['decoder_sha256'] != cpu['decoder_sha256']:
        raise ValueError('ZX0 CPU baseline mismatch')
    report = dict(scope=__doc__, baseline_commit='8e0812b', input_sha256=sha(data),
        frames=4971, audio_estimate_bytes=77696, three_trd_budget_bytes=1937664,
        player_changed=False, integrated_player_delta_tstates=0,
        no_additional_pixel_changes=True, complete=False, rows=[])
    if profile['input_sha256'] != sha(data) or before['input_sha256'] != sha(data):
        raise ValueError('input mismatch')
    for name in ('control', 'frame_split', 'group_split', 'group_byte_planes'):
        row = next(r for r in profile['rows'] if r['name'] == name)
        zx0 = load(f'context_masks_{name}_zx0_measurements.json')
        if (zx0['input_sha256'] != row['sha256'] or zx0['input_bytes'] != row['raw_bytes']
                or len(zx0['blocks']) != zx0['blocks_expected'] or zx0['block_bytes'] != 8192
                or zx0['encoder_mode'] != 'optimal ZX0 v2' or zx0['encoder_sha256'] != before['encoder_sha256']):
            raise ValueError('ZX0/input mismatch')
        amount = sum(b['zx0_bytes']+4 for b in zx0['blocks'])
        if amount != zx0['zx0_with_headers_bytes']:
            raise ValueError('block sum mismatch')
        report['rows'].append(dict(name=name, blocks=len(zx0['blocks']),
            zx0_with_headers_bytes=amount, saved_vs_fpc2=before['zx0_with_headers_bytes']-amount,
            with_audio_estimate_bytes=amount+report['audio_estimate_bytes'],
            deficit_before_extra_overheads=amount+report['audio_estimate_bytes']-report['three_trd_budget_bytes'],
            mask_primitive_formula=mask_cost(groups, row['mode'])))
        if name == 'group_split' and cpu['input_sha256'] != row['sha256']:
            raise ValueError('CPU input mismatch')
    report['zx0_cpu_before'] = old_cpu['summary']
    report['zx0_cpu_after'] = cpu['summary']
    report['zx0_cpu_delta_tstates'] = cpu['summary']['total_tstates']-old_cpu['summary']['total_tstates']
    report['mask_primitive_delta_tstates'] = report['rows'][2]['mask_primitive_formula']['tstates']-report['rows'][0]['mask_primitive_formula']['tstates']
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
