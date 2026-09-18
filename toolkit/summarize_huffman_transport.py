"""Combine complete Z80 stage measurements, without claiming a player schedule.

Before: original FPR1 turbo ZX0, then copy its value bytes to the same kind
of staging output. After: FPE1 turbo ZX0, then nibble Huffman into staging.
The sum is measured work of separate stages, NOT integrated frame timing.
No assumption is made that staging copies or register setup match a future
player; drawing, motion, masks, audio, paging, IRQ, ULA and disk are absent.
"""
import argparse
import json
from pathlib import Path

from probe_lossless_layouts import sha
from benchmark_huffman_z80 import FPE_SHA
from probe_motion_entropy import EXPECTED_SHA
from inspect_frame_cadence import FIELD_TSTATES


def combine(before, after, huffman):
    if not all(row['complete'] for row in (before, after, huffman)):
        raise ValueError('measurements must be complete')
    if before['input_sha256'] != EXPECTED_SHA or after['input_sha256'] != FPE_SHA:
        raise ValueError('unexpected measured streams')
    if huffman['input_sha256'] != FPE_SHA or huffman['restored_sha256'] != EXPECTED_SHA:
        raise ValueError('Huffman round trip does not match the transport streams')
    if len(huffman['frames']) != 4971 or len(huffman['groups']) != 622:
        raise ValueError('incomplete full-movie coverage')
    frames = len(huffman['frames'])
    old_zx0, new_zx0 = before['summary']['total_tstates'], after['summary']['total_tstates']
    old_values = huffman['summary']['raw_tstates']['total']
    new_values = huffman['summary']['huffman_tstates']['total']
    budget = 6 * FIELD_TSTATES
    old_size, new_size = before['summary']['bytes_with_headers'], after['summary']['bytes_with_headers']
    rows = []
    for name, old, new in [('ZX0', old_zx0, new_zx0), ('value_staging', old_values, new_values),
                          ('sum_of_separate_stages', old_zx0+old_values, new_zx0+new_values)]:
        rows.append(dict(stage=name, before_tstates=old, after_tstates=new, delta_tstates=new-old,
                         before_per_frame_mean=old/frames, after_per_frame_mean=new/frames,
                         delta_per_frame_mean=(new-old)/frames))
    return dict(scope=__doc__, baseline_commit='f3f5390', frames=frames,
        stages=rows, nominal_six_field_budget_tstates=budget,
        huffman_only_frames_over_budget=[row for row in huffman['frames'] if row['huffman_tstates'] > budget],
        worst_huffman_group=max(huffman['groups'], key=lambda row: row['huffman_tstates']),
        before_video_bytes=old_size, after_video_bytes=new_size, saved_bytes=old_size-new_size,
        before_contiguous_video_sectors=(old_size+255)//256, after_contiguous_video_sectors=(new_size+255)//256,
        sector_scope='ceil(total stream bytes/256); excludes per-volume alignment and all other disk files',
        audio_bytes_previous_measurement=77696, generous_three_disk_budget=1937664,
        after_video_plus_audio_bytes=new_size+77696, minimum_excess_bytes=new_size+77696-1937664,
        huffman_table_bytes=huffman['table_bytes'], huffman_code_bytes=huffman['code_bytes'],
        benchmark_max_coded_group_bytes=huffman['summary']['max_group_input_bytes'],
        benchmark_max_decoded_group_values=huffman['summary']['max_group_output_bytes'],
        complete_stage_comparison=True, integrated_delivery_measured=False,
        player_changed=False, integrated_player_delta_tstates=0,
        decision='Do not integrate the synchronous whole-frame Huffman path: six frames exceed the full frame budget before other work. A bounded producer and faster decoder need measurement; three disks are not achieved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--huffman', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = [args.before, args.after, args.huffman]
    report = combine(*(json.loads(path.read_text()) for path in paths))
    report['source_reports'] = [dict(file=path.name, sha256=sha(path.read_bytes())) for path in paths]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
