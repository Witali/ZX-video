"""Validate screen-output evidence and combine separately measured CPU costs.

The queue bounds below are optimistic CPU-only bounds. Work from two
independent runs is added; this does not claim an integrated memory map,
real decoded-frame queue, sector schedule, or smooth playback.
"""
import argparse
import json
from pathlib import Path

import compact_screen_z80 as machine
from probe_lossless_layouts import sha
from summarize_spatial_extended import cpu_summary, STATE_SHA
from summarize_context_cpu import minimum_capacity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(stem):
        report = json.loads((args.reports/(stem+'.json')).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+stem)
        return report

    draw = load('compact_screen_cpu')
    recon = load('cache_aware_fragments_cpu')
    zx0 = load('cache_aware_fragments_zx0_cpu')
    dirty = load('native_dirty_tiles')
    reconstructed = cpu_summary(recon)
    if (any(row['states_sha256'] != STATE_SHA for row in (draw, recon, dirty))
            or draw['reconstruction_report_sha256'] != sha((args.reports/'cache_aware_fragments_cpu.json').read_bytes())
            or recon['input_sha256'] != dirty['input_sha256'] or zx0['input_sha256'] != recon['input_sha256']
            or len(draw['frames']) != 4971 or len(dirty['rows']) != 4971):
        raise AssertionError('different movie/CPU reports')
    code, labels, listing, regions = machine.build(**draw['options'])
    old_code, old_labels, old_listing, _ = machine.build(**draw['baseline_options'])
    if (code.hex() != draw['code_hex'] or labels != draw['labels'] or listing != draw['instruction_listing']
            or old_code.hex() != draw['baseline_code_hex'] or old_labels != draw['baseline_labels']
            or old_listing != draw['baseline_instruction_listing']
            or [dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in regions] != draw['tables']):
        raise AssertionError('decoder/listing/tables changed')
    expected = machine.expected_tstates(**draw['options'])
    previous = machine.expected_tstates(**draw['baseline_options'])
    work = []
    for i, (a, b) in enumerate(zip(draw['frames'], recon['frames'])):
        if (a['index'] != i or a['tstates'] != expected or sum(a['stages'].values()) != expected
                or a['reconstruction_and_output_tstates'] != a['tstates']+b['total_tstates']
                or a['target_bank'] != (7 if i % 2 == 0 else 5)
                or a['page_writes'] != ([0x17, 0x16] if i % 2 == 0 else [0x1f, 0x1e])):
            raise AssertionError('frame coverage or timing differs')
        work.append(a['reconstruction_and_output_tstates'])
    total = expected*4971
    if (sum(r['count']*r['tstates'] for r in draw['instruction_histogram']) != total
            or draw['summary']['output_tstates'] != total
            or any(r['tstates'] != previous for r in draw['baseline_frames'])
            or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
        raise AssertionError('instruction/block sums differ')
    result = dict(scope=__doc__, complete=True, baseline_commit='d4f2b15', states_sha256=STATE_SHA,
        frames=4971, rows=draw['options'], code_bytes=labels['state']-machine.CODE,
        baseline_code_bytes=old_labels['state']-machine.CODE, state_bytes=labels['end']-labels['state'],
        tables_bytes=sum(len(v) for _, v in regions), code_end_hex=hex(labels['end']),
        output_per_frame_tstates=expected, baseline_per_frame_tstates=previous,
        output_delta_per_frame_tstates=expected-previous, output_total_tstates=total,
        output_delta_total_tstates=4971*(expected-previous),
        reconstruction_and_output_tstates=sum(work), reconstruction_and_output_max_tstates=max(work),
        frames_over_nominal_425448=sum(t > 425448 for t in work),
        three_stage_total_tstates=sum(work)+zx0['summary']['total_tstates'],
        three_stage_mean_tstates=(sum(work)+zx0['summary']['total_tstates'])/4971,
        remaining_nominal_mean_tstates=425448-(sum(work)+zx0['summary']['total_tstates'])/4971,
        idealized_reconstruction_output_queues=[dict(budget=b, frames=minimum_capacity(work, b))
            for b in (425448, 400000, 375000, 350000)],
        dirty_metadata_summary=dirty['summary'], dirty_generation_measured_on_z80=False,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
