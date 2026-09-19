"""Verify FHC1 storage/ZX0 evidence and optionally complete reconstruction.

The result is an offline experiment, never proof of sustained frame delivery.
Omitting --cpu-report explicitly leaves full reconstruction unverified here.
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
    p.add_argument('--interrupted', type=Path, help='compare a saved interrupted prefix with the completed run')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    def load(name):
        report = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+name)
        return report
    source = args.raw.read_bytes()
    selection = load('raw_intra_selection'); chosen = selection['rows'][0]
    storage = load('raw_intra_zx0'); zx0 = load('raw_intra_zx0_cpu')
    prior_storage = load('unrolled_fast_zx0'); prior_zx0 = load('unrolled_fast_zx0_cpu')
    prior_cpu = load('unrolled_fast_cpu')
    if (chosen['sha256'] != sha(source) or storage['input_sha256'] != sha(source)
            or zx0['input_sha256'] != sha(source) or selection['states_sha256'] != STATE_SHA
            or chosen['frames'] != 4971 or len(source) != chosen['raw_bytes']
            or zx0['storage_report_sha256'] != sha((args.reports/'raw_intra_zx0.json').read_bytes())
            or len(zx0['blocks']) != storage['blocks_expected'] or len(storage['blocks']) != storage['blocks_expected']):
        raise AssertionError('input/coverage mismatch')
    for i, (a, b) in enumerate(zip(zx0['blocks'], storage['blocks'])):
        if a['index'] != i or a['raw_sha256'] != b['sha256'] or a['raw_bytes'] != b['decoded_bytes'] or a['compressed_bytes'] != b['zx0_bytes']:
            raise AssertionError('ZX0 block mismatch')
    if (sum(b['decoded_bytes'] for b in storage['blocks']) != len(source)
            or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']
            or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
        raise AssertionError('ZX0 totals mismatch')
    model, _, count, mapping, tables = read_header(Reader(source), magic=b'FHC1')
    if model != 0 or count != 4971:
        raise AssertionError('header mismatch')
    builds = [machine.build(tables, mapping, OFFSETS, hybrid=True, skip_empty=True,
        intra_above=True, intra_extended=True, fast_fragments=True, unrolled_motion=True, raw_intra=v)
        for v in (False, True)]
    old, new = builds[0][1], builds[1][1]
    video = storage['zx0_with_headers_bytes']
    report = dict(scope=__doc__, complete=True, baseline_commit='eea5d62', states_sha256=STATE_SHA,
        input_sha256=sha(source), frames=4971, full_pc_decode_verified=chosen['exact_causal_frame_decode'],
        storage=dict(video_bytes=video, blocks=storage['blocks_expected'], video_plus_ay_bytes=video+77696,
            preliminary_three_trd_margin_bytes=1937664-video-77696,
            delta_from_unrolled_fhf_bytes=video-prior_storage['zx0_with_headers_bytes']),
        zx0_cpu=dict(zx0['summary'], delta_tstates=zx0['summary']['total_tstates']-prior_zx0['summary']['total_tstates']),
        code_bytes=new['state']-machine.CODE, state_bytes=new['end']-new['state'], code_end_hex=hex(new['end']),
        code_delta_bytes=(new['state']-old['state']), state_delta_bytes=(new['end']-new['state'])-(old['end']-old['state']),
        code_hex=builds[1][0].hex(), labels=new, instruction_listing=builds[1][2],
        instruction_timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        primitive_example=dict(vector=82, tile=16, mask=65535, huffman_lengths=8, aligned=True,
            old_body_including_huffman_tstates=4301, new_body_tstates=1351, body_delta_tstates=-2950,
            old_with_dispatch_tstates=4362, new_with_dispatch_tstates=1403, delta_with_dispatch_tstates=-2959),
        retained_intra_dispatch_delta_tstates=18, retained_fast_dispatch_delta_tstates=28,
        retained_temporal_dispatch_delta_tstates=0,
        full_z80_reconstruction_verified=False, full_frame_delivery_measured=False,
        no_additional_pixel_changes=True, player_changed=False, integrated_player_delta_tstates=0)
    # This explicit example is also executed against both binaries in tests.
    if machine.raw_intra_tstates(82, 16, 65535) != 1351:
        raise AssertionError('timing example changed')
    if args.cpu_report:
        cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
        if (cpu['input_sha256'] != sha(source) or not cpu['raw_intra'] or cpu['code_hex'] != report['code_hex']
                or cpu['labels'] != new or cpu['instruction_listing'] != report['instruction_listing']
                or sum(g['bits'] for g in cpu['groups']) != chosen['bits']
                or cpu['summary']['values'] != chosen['values']
                or cpu['summary']['fast_tiles'] != chosen['fast_tiles']
                or cpu['summary']['raw_intra_tiles'] != chosen['raw_intra_tiles']
                or cpu['summary']['raw_intra_values'] != chosen['raw_intra_values']):
            raise AssertionError('reconstruction mismatch')
        current = cpu_summary(cpu)
        report['cpu'] = current
        report['reconstruction_delta_tstates'] = current['total_tstates']-prior_cpu['summary']['total_tstates']
        report['two_stage_total_tstates'] = current['total_tstates']+zx0['summary']['total_tstates']
        report['two_stage_delta_tstates'] = report['two_stage_total_tstates']-prior_cpu['summary']['total_tstates']-prior_zx0['summary']['total_tstates']
        report['full_z80_reconstruction_verified'] = True
        if args.interrupted:
            interrupted = json.loads(args.interrupted.read_text(encoding='utf-8'))
            done = len(interrupted['frames'])
            if (interrupted['complete'] or interrupted['input_sha256'] != sha(source)
                    or interrupted['code_hex'] != cpu['code_hex'] or not 0 < done < 4971
                    or interrupted['frames'] != cpu['frames'][:done]):
                raise AssertionError('interrupted prefix differs')
            report['interrupted_attempt'] = dict(saved_frames=done, saved_groups=len(interrupted['groups']),
                total_tstates=sum(f['total_tstates'] for f in interrupted['frames']),
                max_frame_tstates=max(f['total_tstates'] for f in interrupted['frames']),
                snapshot_sha256=sha(args.interrupted.read_bytes()), exact_match_with_completed_prefix=True)
    elif args.interrupted:
        p.error('--interrupted requires --cpu-report')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('code_hex', 'labels', 'instruction_listing', 'cpu')}))


if __name__ == '__main__':
    main()
