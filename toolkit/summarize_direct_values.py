"""Compare complete FPD1 round trips and actual optimal ZX0 storage runs.

The unchanged AY size and three-TRD allowance are inherited estimates.
Player/loaders, volume restarts, duplicated tables and sector padding are
not included. This is a storage experiment, not a release size forecast.
"""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        report = json.loads((args.reports/name).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError(f'incomplete report: {name}')
        return report

    source = load('direct_values_measurements.json')
    baseline = load('context_masks_group_split_zx0_measurements.json')
    rows = []
    for row in source['rows']:
        coded = load(f'direct_values_{row["name"]}_zx0.json')
        if (row['sha256'] != coded['input_sha256'] or row['raw_bytes'] != coded['input_bytes']
                or len(coded['blocks']) != coded['blocks_expected']
                or not row['exact_fpr1_restoration'] or not row['exact_causal_frame_decode']
                or row['decoded_states_sha256'] != source['states_sha256']):
            raise ValueError('input or verification coverage mismatch')
        size = sum(block['zx0_bytes']+4 for block in coded['blocks'])
        if size != coded['zx0_with_headers_bytes']:
            raise ValueError('size mismatch')
        rows.append(dict(**row, blocks=len(coded['blocks']), zx0_with_headers_bytes=size,
            delta_vs_fpc3_bytes=size-baseline['zx0_with_headers_bytes'],
            with_existing_ay_estimate_bytes=size+77696,
            minimum_three_trd_deficit_bytes=size+77696-1937664))
    result = dict(scope=__doc__, baseline_commit='fbf351e', complete=True,
        input_sha256=source['input_sha256'], states_sha256=source['states_sha256'],
        frames=source['frames'], baseline_bytes=baseline['zx0_with_headers_bytes'],
        unchanged_ay_estimate_bytes=77696, generous_three_trd_budget_bytes=1937664,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        independently_verified_zx0_blocks=sum(row['blocks'] for row in rows), rows=rows)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
