"""Combine full edited-movie cell-output evidence and separated CPU stages.

The one-frame FSC1 prototype is a storage/memory-window result, not an
integrated timing result. No uniform per-frame ZX0 or disk cost is assumed.
"""
import argparse
import json
import math
from pathlib import Path

import cell_screen_z80 as machine
from probe_lossless_layouts import sha
from summarize_context_cpu import minimum_capacity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    def load(stem):
        r = json.loads((args.reports/(stem+'.json')).read_text(encoding='utf-8'))
        if not r['complete']:
            raise ValueError('incomplete '+stem)
        return r
    draw, mask = load('cell_output_cpu'), load('cell_output_masks')
    recon, video_zx0 = load('no_credits_reconstruction_cpu'), load('no_credits_zx0_cpu')
    map_storage, map_zx0 = load('cell_output_zx0'), load('cell_output_zx0_cpu')
    timeline = load('no_credits_timeline')
    prototype, prototype_storage = load('one_frame_cell_stream'), load('one_frame_cell_zx0')
    maps = args.masks.read_bytes()
    count = timeline['frames_after']
    code, labels, listing, _ = machine.build()
    if (any(r['states_sha256'] != timeline['states_sha256'] for r in (draw, mask, recon, prototype))
            or sha(maps) != mask['stream_sha256'] or draw['masks_sha256'] != sha(maps)
            or video_zx0['input_sha256'] != recon['input_sha256']
            or map_storage['input_sha256'] != sha(maps) or map_zx0['input_sha256'] != sha(maps)
            or prototype_storage['input_sha256'] != prototype['stream_sha256']
            or len(draw['frames']) != count or len(recon['frames']) != count
            or draw['code_hex'] != code.hex() or draw['labels'] != labels or draw['instruction_listing'] != listing):
        raise ValueError('different inputs or machine code')
    work = []
    for i, (a, b) in enumerate(zip(draw['frames'], recon['frames'])):
        if (a['index'] != i or b['index'] != i or a['tstates'] != machine.expected_tstates(maps[80*i:80*i+80])
                or sum(a['stages'].values()) != a['tstates'] or sum(b['stages'].values()) != b['total_tstates']):
            raise ValueError('invalid frame coverage/timing')
        work.append(a['tstates']+b['total_tstates'])
    for r, total in ((draw, sum(f['tstates'] for f in draw['frames'])),
                     (recon, sum(f['total_tstates'] for f in recon['frames']))):
        if sum(h['tstates']*h['count'] for h in r['instruction_histogram']) != total:
            raise ValueError('histogram total differs')
    for r in (video_zx0, map_zx0):
        if sum(b['tstates'] for b in r['blocks']) != r['summary']['total_tstates']:
            raise ValueError('ZX0 total differs')
    extra = map_storage['zx0_with_headers_bytes']
    saved = 154089*count-draw['summary']['total_tstates']-map_zx0['summary']['total_tstates']
    total = sum(work)+video_zx0['summary']['total_tstates']+map_zx0['summary']['total_tstates']
    payload = video_zx0['summary']['bytes_with_headers']+extra+timeline['ay_pair_bytes']
    prototype_payload = prototype_storage['zx0_with_headers_bytes']+timeline['ay_pair_bytes']
    report = dict(scope=__doc__, complete=True, frames=count, states_sha256=timeline['states_sha256'],
        native_output=draw['summary'], map_zx0_tstates=map_zx0['summary']['total_tstates'],
        net_cpu_saving_tstates=saved, mean_net_cpu_saving_tstates=saved/count,
        reconstruction_and_output_tstates=sum(work), reconstruction_and_output_max_tstates=max(work),
        worst_frame=work.index(max(work)), frames_over_nominal_425448=sum(x > 425448 for x in work),
        four_separated_stage_tstates=total, mean_four_stage_tstates=total/count,
        remaining_nominal_mean_tstates=425448-total/count,
        optimistic_reconstruction_output_queue=[dict(budget=b, frames=minimum_capacity(work, b)) for b in (425448, 400000, 375000, 350000)],
        added_map_bytes=extra, separate_streams_plus_ay_bytes=payload,
        preliminary_three_trd_margin_bytes=1937664-payload,
        extra_sectors_roundup=math.ceil(extra/256),
        break_even_added_sector_ms=saved/3545400/math.ceil(extra/256)*1000,
        disk_note='CPU saving only pays for added disk time below this average; actual TR-DOS/physical latency and deadline distribution still need measurement.',
        one_frame_fsc=dict(zx0_bytes=prototype_storage['zx0_with_headers_bytes'],
            plus_ay_bytes=prototype_payload, preliminary_three_trd_margin_bytes=1937664-prototype_payload,
            max_coded_bytes_with_guards=prototype['max_coded_bytes_with_guards'],
            cpu_timing_inherited=False, integrated_memory_verified=False),
        code_bytes=labels['state']-machine.CODE, state_bytes=labels['end']-labels['state'],
        no_additional_pixel_changes=True, full_frame_delivery_measured=False,
        player_changed=False, integrated_player_delta_tstates=0)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
