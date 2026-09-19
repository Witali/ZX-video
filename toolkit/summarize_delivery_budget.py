"""Compare adaptive frame delivery against the measured 6103e11 baseline.

CPU baseline uses eight-frame groups, candidate one-frame groups and real
337-T handoff. ZX0 block timing is separate; no uniform per-frame ZX0/disk
charge, six-field publication schedule or playable TRD count is inferred.
"""
import argparse
import json
import math
from pathlib import Path

from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        r = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not r['complete']:
            raise ValueError('incomplete '+name)
        return r

    timeline = load('no_credits_timeline')
    base = load('cell_output_summary')
    reconstruction = load('no_credits_reconstruction_cpu')
    draw = load('cell_output_cpu')
    choice = load('delivery_budget_375')
    cpu = load('delivery_budget_375_pipeline_cpu')
    sound = load('delivery_budget_375_audio_stream')
    storage = load('delivery_budget_375_audio_zx0')
    zx0 = load('delivery_budget_375_audio_zx0_cpu')
    count, states = timeline['frames_after'], timeline['states_sha256']
    if (any(r['states_sha256'] != states for r in (base, reconstruction, draw, choice, cpu))
            or cpu['stream_sha256'] != choice['stream_sha256']
            or sound['cells_sha256'] != cpu['stream_sha256']
            or sound['audio_pairs_sha256'] != timeline['ay_pairs_sha256']
            or sound['raw_ay_sha256'] != timeline['ay_sha256']
            or sound['stream_sha256'] != storage['input_sha256']
            or zx0['input_sha256'] != sound['stream_sha256']
            or cpu['reconstruction_code_sha256'] != sha(bytes.fromhex(reconstruction['code_hex']))
            or cpu['output_code_sha256'] != sha(bytes.fromhex(draw['code_hex']))
            or [r['index'] for r in cpu['frames']] != list(range(count))):
        raise ValueError('inconsistent evidence')
    costs = [r['total_tstates'] for r in cpu['frames']]
    histogram = sum(r['tstates']*r['count'] for r in cpu['instruction_histogram'])
    if histogram != sum(costs) or sum(costs) != cpu['summary']['total_tstates']:
        raise ValueError('CPU histogram differs')
    for current, previous in zip(cpu['frames'], draw['frames']):
        if (current['stages']['output'] != previous['tstates']
                or current['stages']['handoff'] != 337
                or sum(current['stages'].values()) != current['total_tstates']):
            raise ValueError('frame stages differ')
    if sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']:
        raise ValueError('ZX0 coverage differs')
    attempts = []
    for budget in (375, 385):
        candidate, packed = load(f'delivery_budget_{budget}'), load(f'delivery_budget_{budget}_zx0')
        if candidate['stream_sha256'] != packed['input_sha256']:
            raise ValueError('candidate storage mismatch')
        total = packed['zx0_with_headers_bytes']+timeline['ay_pair_bytes']
        attempts.append(dict(frame_budget_tstates=budget*1000, fast_tiles=candidate['fast_tiles'],
            fsc_zx0_bytes=packed['zx0_with_headers_bytes'], with_uncompressed_ay_bytes=total,
            preliminary_three_trd_margin_bytes=1937664-total,
            shared_pipeline_measured=budget == 375))
    decoded = zx0['summary']['total_tstates']
    old = base['reconstruction_and_output_tstates']
    report = dict(scope=__doc__, complete=True, frames=count, states_sha256=states,
        separate_ay_attempts=attempts,
        reconstruction_output_handoff=dict(baseline_total_tstates=old,
            total_tstates=sum(costs), delta_tstates=sum(costs)-old,
            mean_tstates=sum(costs)/count, max_tstates=max(costs), worst_frame=costs.index(max(costs)),
            baseline_max_tstates=base['reconstruction_and_output_max_tstates'],
            baseline_frames_over_nominal_425448=base['frames_over_nominal_425448'],
            frames_over_nominal_425448=sum(v > 425448 for v in costs),
            frames_over_selection_budget_375000=sum(v > 375000 for v in costs),
            model_frames_unable_to_reach_selection_limit=choice['choice']['estimated_frames_over_target'],
            wrapper_tstates=337, cold_init_tstates=cpu['cold_init']['total_tstates'],
            note='Baseline groups <=8 and host glue; candidate groups 1 and actual wrapper. Reconstruction/drawing code byte-identical.'),
        multiplexed_video_audio=dict(zx0_with_headers_bytes=storage['zx0_with_headers_bytes'],
            preliminary_three_trd_margin_bytes=1937664-storage['zx0_with_headers_bytes'],
            delta_bytes_vs_separate_ay=storage['zx0_with_headers_bytes']-attempts[0]['with_uncompressed_ay_bytes'],
            max_ay_bytes_per_frame=sound['max_audio_bytes_per_frame'],
            zx0_tstates=decoded, zx0_max_block_tstates=zx0['summary']['max_block_tstates']),
        measured_separated_stage_total_tstates=sum(costs)+decoded,
        measured_separated_stage_mean_tstates=(sum(costs)+decoded)/count,
        remaining_nominal_mean_tstates=425448-(sum(costs)+decoded)/count,
        max_coded_input_bytes=cpu['summary']['max_coded_input_bytes'],
        exact_ay_register_replay=True, no_additional_pixel_changes=True,
        metadata_expanded_by_host=True, ay_scheduling_included=False,
        ula_contention_included=False, rom_and_disk_included=False,
        frame_pacing_verified=False, release_disks_changed=False,
        full_frame_delivery_measured=False, player_changed=False, integrated_player_delta_tstates=0)
    # Relative to the previous four separated stages, not a schedule proof.
    added = storage['zx0_with_headers_bytes']-base['separate_streams_plus_ay_bytes']
    saved = base['four_separated_stage_tstates']-sum(costs)-decoded
    sectors = math.ceil(added/256)
    report['disk_tradeoff'] = dict(added_bytes=added, added_sectors_roundup=sectors,
        net_measured_cpu_saving_tstates=saved,
        break_even_added_sector_ms=saved/3545400/sectors*1000 if sectors > 0 else None,
        note='Average break-even only; metadata/AY parsing and changed disk-read deadlines still need actual integration.')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
