"""Join complete context experiments with actual optimal ZX0 measurements.

Sizes include four bytes per ZX0 block and serialized code-length tables.
AY is the unchanged prior estimate, not a new audio encode. Deficits exclude
new player code, volume copies/alignment and any runtime-table conversion.
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
            raise ValueError(f'incomplete {name}')
        return report

    plain = load('context_values_measurements.json')
    prediction = load('prediction_values_measurements.json')
    memory = {row['bitmap_contexts']: row for row in load('context_tree_memory_measurements.json')['rows']}
    old = load('motion_metadata_zx0_measurements.json')
    control = load('context_global_zx0_measurements.json')
    report = dict(scope=__doc__, baseline_commit='8b3f83f', frames=4971,
        previous_fpm1_bytes=old['zx0_with_headers_bytes'],
        fpc1_control_bytes=control['zx0_with_headers_bytes'],
        audio_estimate_bytes=77696, three_trd_budget_bytes=1937664,
        player_changed=False, integrated_player_delta_tstates=0,
        no_additional_pixel_changes=True, complete=False, rows=[])
    selected = [('global', plain, 'context_global'), ('density_motion', plain, 'context_density')]
    selected += [(f'prediction_{n}', prediction, f'prediction_{n}') for n in (8, 16, 32, 64)]
    for name, source, prefix in selected:
        original = next(row for row in source['rows'] if row['name'] == name)
        packed = load(prefix+'_zx0_measurements.json')
        if (packed['input_sha256'] != original['sha256'] or packed['input_bytes'] != original['raw_bytes']
                or packed['block_bytes'] != 8192 or packed['encoder_mode'] != 'optimal ZX0 v2'
                or len(packed['blocks']) != packed['blocks_expected']
                or packed['encoder_sha256'] != old['encoder_sha256']):
            raise ValueError(f'input/encoder/coverage mismatch for {name}')
        amount = sum(b['zx0_bytes']+4 for b in packed['blocks'])
        if amount != packed['zx0_with_headers_bytes']:
            raise ValueError('block sum mismatch')
        row = dict(name=name, contexts=original['contexts'], raw_bytes=original['raw_bytes'],
            input_sha256=original['sha256'], blocks=len(packed['blocks']),
            zx0_with_headers_bytes=amount, saved_vs_previous_fpm1=report['previous_fpm1_bytes']-amount,
            saved_vs_fpc1_control=report['fpc1_control_bytes']-amount,
            with_audio_estimate_bytes=amount+report['audio_estimate_bytes'],
            deficit_before_extra_overheads=amount+report['audio_estimate_bytes']-report['three_trd_budget_bytes'],
            max_compressed_block=max(b['zx0_bytes'] for b in packed['blocks']))
        if 'bitmap_contexts' in original:
            row['canonical_runtime_table_bytes'] = memory[original['bitmap_contexts']]['canonical_counts']['total_table_bytes']
        report['rows'].append(row)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
