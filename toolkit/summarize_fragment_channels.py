"""Validate separated fragment storage and optional full Z80 reconstruction.

CPU fixture uses two bounded contiguous input regions with a guard byte
after each. Production paging/windows, screen expansion and disk schedule
are still outside scope, even when all movie frames are reconstructed.
"""
import argparse
import json
from pathlib import Path

import causal_tile_z80 as machine
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from probe_lossless_layouts import sha
from summarize_spatial_extended import cpu_summary, STATE_SHA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--cpu-report', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    def load(name):
        report = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+name)
        return report
    source = args.raw.read_bytes()
    transform = load('fragment_channels'); storage = load('fragment_channels_zx0')
    zx0 = load('fragment_channels_zx0_cpu'); baseline = load('unrolled_fast_cpu')
    base_storage = load('unrolled_fast_zx0'); base_zx0 = load('unrolled_fast_zx0_cpu')
    if (transform['sha256'] != sha(source) or storage['input_sha256'] != sha(source) or zx0['input_sha256'] != sha(source)
            or transform['input_sha256'] != baseline['input_sha256'] or transform['states_sha256'] != STATE_SHA
            or transform['frames'] != 4971 or not transform['exact_original_stream_roundtrip']
            or not transform['exact_causal_frame_decode'] or len(source) != transform['raw_bytes']
            or sum(g['frames'] for g in transform['groups']) != 4971
            or len(zx0['blocks']) != storage['blocks_expected']
            or zx0['storage_report_sha256'] != sha((args.reports/'fragment_channels_zx0.json').read_bytes())):
        raise AssertionError('input/coverage differs')
    if (len(storage['blocks']) != storage['blocks_expected']
            or sum(b['decoded_bytes'] for b in storage['blocks']) != len(source)
            or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']
            or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
        raise AssertionError('block sums differ')
    for index, (a, b) in enumerate(zip(zx0['blocks'], storage['blocks'])):
        if a['index'] != index or a['raw_sha256'] != b['sha256'] or a['raw_bytes'] != b['decoded_bytes'] or a['compressed_bytes'] != b['zx0_bytes']:
            raise AssertionError('block differs')
    _, _, _, mapping, tables = read_header(Reader(source), magic=b'FSF1')
    builds = [machine.build(tables, mapping, OFFSETS, hybrid=True, skip_empty=True,
        intra_above=True, intra_extended=True, fast_fragments=True, unrolled_motion=True, split_literals=v)
        for v in (False, True)]
    if builds[0][0].hex() != baseline['code_hex']:
        raise AssertionError('disabled binary changed')
    old, new = builds[0][1], builds[1][1]
    video = storage['zx0_with_headers_bytes']
    report = dict(scope=__doc__, complete=True, input_sha256=sha(source), states_sha256=STATE_SHA,
        frames=4971, full_pc_decode_verified=True, exact_original_stream_roundtrip=True,
        video_bytes=video, delta_video_bytes=video-base_storage['zx0_with_headers_bytes'],
        video_plus_ay_bytes=video+77696, preliminary_three_trd_margin_bytes=1937664-video-77696,
        zx0_cpu=zx0['summary'], zx0_cpu_delta_tstates=zx0['summary']['total_tstates']-base_zx0['summary']['total_tstates'],
        old_code_bytes=old['state']-machine.CODE, code_bytes=new['state']-machine.CODE,
        code_delta_bytes=new['state']-old['state'], old_state_bytes=old['end']-old['state'],
        state_bytes=new['end']-new['state'], code_end_hex=hex(new['end']),
        literal_body_tstates={str(v): dict(before=machine.fast_tstates(v), after=machine.fast_tstates(v, split_literals=True),
            delta=-54, delta_when_previously_unaligned=-64) for v in range(85, 89)},
        two_row_timing_note='Mode 87 formula shown for selector zero; add -10*popcount(selector) to both values.',
        code_hex=builds[1][0].hex(), labels=new, instruction_listing=builds[1][2],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_z80_reconstruction_verified=False, full_frame_delivery_measured=False,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0)
    if args.cpu_report:
        cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
        if (cpu['input_sha256'] != sha(source) or not cpu['split_literals'] or cpu['code_hex'] != report['code_hex']
                or cpu['labels'] != new or cpu['instruction_listing'] != report['instruction_listing']
                or sum(g['literal_bytes'] for g in cpu['groups']) != transform['literal_bytes']
                or sum(f['bits'] for f in cpu['frames']) != transform['huffman_bits']):
            raise AssertionError('CPU source/coverage differs')
        current = cpu_summary(cpu)
        previous = cpu_summary(baseline)
        for before, after in zip(baseline['frames'], cpu['frames']):
            for field in ('index', 'values', 'intra_tiles', 'intra_modes', 'fast_tiles', 'fast_kinds', 'motion_vectors', 'cache'):
                if before[field] != after[field]:
                    raise AssertionError('decoded frame mode changed')
            expected_delta = -54*before['fast_tiles']-10*before['fast_unaligned']
            if (after['stages'].get('fast_fragment', 0)-before['stages'].get('fast_fragment', 0) != expected_delta
                    or after['fast_unaligned']):
                raise AssertionError('fast path timing differs')
            for stage in set(before['stages']) | set(after['stages']):
                if stage not in ('huffman', 'fast_fragment') and before['stages'].get(stage, 0) != after['stages'].get(stage, 0):
                    raise AssertionError('unrelated stage differs')
        if current['huffman_branches'] != previous['huffman_branches']:
            raise AssertionError('different Huffman symbols/branches')
        report.update(full_z80_reconstruction_verified=True, cpu=current,
            reconstruction_delta_tstates=current['total_tstates']-previous['total_tstates'],
            two_stage_total_tstates=current['total_tstates']+zx0['summary']['total_tstates'],
            two_stage_delta_tstates=current['total_tstates']+zx0['summary']['total_tstates']-previous['total_tstates']-base_zx0['summary']['total_tstates'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('code_hex', 'labels', 'instruction_listing', 'cpu')}))


if __name__ == '__main__':
    main()
