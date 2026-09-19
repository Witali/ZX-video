"""Cross-check full-movie FSF1 selection, storage and actual Z80 evidence.

Both candidates reconstruct the same pixels with the same decoder binary.
This verifies reconstruction and separate ZX0 decoding, not screen output,
metadata parsing, paging, IRQ/ULA/ROM, or sustained physical disk delivery.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from probe_lossless_layouts import sha
from summarize_spatial_extended import cpu_summary, STATE_SHA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        report = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not report['complete']:
            raise ValueError('incomplete '+name)
        return report

    selection = load('cache_aware_fragments')
    storage = load('cache_aware_fragments_zx0')
    zx0 = load('cache_aware_fragments_zx0_cpu')
    cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    old = load('fragment_channels_cpu')
    old_storage = load('fragment_channels_zx0')
    old_zx0 = load('fragment_channels_zx0_cpu')
    old_selection = load('fragment_channels')
    source_cpu = load('unrolled_motion_fhs_cpu')
    raw = args.raw.read_bytes()
    digest = sha(raw)
    if (selection['sha256'] != digest or len(raw) != selection['raw_bytes']
            or selection['frames'] != 4971 or selection['states_sha256'] != STATE_SHA
            or not selection['exact_causal_frame_decode'] or not selection['exact_interleaved_roundtrip']
            or selection['input_sha256'] != source_cpu['input_sha256']
            or selection['cpu_report_sha256'] != sha((args.reports/'unrolled_motion_fhs_cpu.json').read_bytes())
            or any(row['input_sha256'] != digest for row in (cpu, storage, zx0))
            or zx0['storage_report_sha256'] != sha((args.reports/'cache_aware_fragments_zx0.json').read_bytes())
            or any(row['input_sha256'] != old_selection['sha256'] for row in (old, old_storage, old_zx0))):
        raise AssertionError('source/coverage differs')
    for key in ('code_hex', 'labels', 'instruction_listing', 'tables', 'code_bytes', 'state_bytes',
                'intra_extended', 'fast_fragments', 'unrolled_motion', 'split_literals'):
        if cpu[key] != old[key]:
            raise AssertionError('decoder configuration changed: '+key)
    current = cpu_summary(cpu)
    previous = cpu_summary(old)
    modes = Counter()
    for frame in cpu['frames']:
        modes.update(frame['fast_kinds'])
        if (frame['fast_formula_tstates'] != frame['stages'].get('fast_fragment', 0)
                or frame['motion_formula_tstates'] != frame['stages'].get('motion', 0)
                or frame['fast_unaligned']):
            raise AssertionError('instruction timing formula differs')
    if (dict(modes) != selection['fast_kinds']
            or sum(modes.values()) != selection['fast_tiles']
            or sum(f['cache'] for f in cpu['frames']) != selection['cache_frames_after']
            or sum(g['frames'] for g in cpu['groups']) != 4971
            or len(cpu['groups']) != selection['groups']
            or sum(g['literal_bytes'] for g in cpu['groups']) != selection['literal_bytes']
            or sum(f['bits'] for f in cpu['frames']) != selection['huffman_bits']):
        raise AssertionError('selected modes/channel coverage differs')
    if (len(storage['blocks']) != storage['blocks_expected']
            or len(zx0['blocks']) != storage['blocks_expected']
            or sum(b['decoded_bytes'] for b in storage['blocks']) != len(raw)
            or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']
            or sum(b['tstates'] for b in zx0['blocks']) != zx0['summary']['total_tstates']):
        raise AssertionError('ZX0 block totals differ')
    offset = 0
    for index, (packed, measured) in enumerate(zip(storage['blocks'], zx0['blocks'])):
        expected = raw[offset:offset+packed['decoded_bytes']]
        offset += len(expected)
        if (measured['index'] != index or measured['raw_sha256'] != packed['sha256']
                or sha(expected) != packed['sha256'] or measured['raw_bytes'] != len(expected)
                or measured['compressed_bytes'] != packed['zx0_bytes']):
            raise AssertionError('ZX0 block differs')
    cache = selection['cache_cost']
    if (cache['enabled']['total_tstates']-cache['disabled']['total_tstates'] != cache['delta_tstates']
            or any(sum(cache[k]['stages'].values()) != cache[k]['total_tstates'] for k in ('enabled', 'disabled'))):
        raise AssertionError('cache timing differs')
    video = storage['zx0_with_headers_bytes']
    report = dict(scope=__doc__, complete=True, baseline_commit='1659579', input_sha256=digest,
        states_sha256=STATE_SHA, frames=4971, groups=len(cpu['groups']),
        full_pc_decode_verified=True, full_z80_reconstruction_verified=True,
        decoder_binary_unchanged=True, no_additional_pixel_changes=True,
        raw_bytes=len(raw), raw_delta_bytes=len(raw)-old_selection['raw_bytes'],
        video_bytes=video, video_delta_bytes=video-old_storage['zx0_with_headers_bytes'],
        unchanged_ay_bytes=77696, video_plus_ay_bytes=video+77696,
        preliminary_three_trd_margin_bytes=1937664-video-77696,
        cache_cost=cache, cache_frames_before=sum(f['cache'] for f in old['frames']),
        cache_frames_after=sum(f['cache'] for f in cpu['frames']),
        cpu=current, reconstruction_delta_tstates=current['total_tstates']-previous['total_tstates'],
        maximum_frame_delta_tstates=current['max_frame_tstates']-previous['max_frame_tstates'],
        stage_delta_tstates={k: current['stages'].get(k, 0)-previous['stages'].get(k, 0)
            for k in sorted(set(current['stages']) | set(previous['stages']))},
        zx0_cpu=zx0['summary'], zx0_delta_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
        two_stage_tstates=current['total_tstates']+zx0['summary']['total_tstates'],
        two_stage_delta_tstates=current['total_tstates']+zx0['summary']['total_tstates']
            -previous['total_tstates']-old_zx0['summary']['total_tstates'],
        estimated_target_tstates=selection['target_tstates'],
        measured_frames_over_selection_target=sum(f['total_tstates'] > selection['target_tstates'] for f in cpu['frames']),
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('cpu', 'cache_cost')}))


if __name__ == '__main__':
    main()
