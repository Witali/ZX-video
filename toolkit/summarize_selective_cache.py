"""Validate selective-cache CPU savings against added ZX0 and disk bytes."""
import argparse
import json
from pathlib import Path

from causal_tile_z80 import selective_cache_delta_tstates, build
from frame_output_pipeline import frames
from probe_sparse_motion_cache import unpack
from probe_spatial_contexts import OFFSETS
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'stream', 'cache-stream', 'old-zx0', 'new-zx0',
                 'old-storage', 'new-storage', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    def read(name):
        result = json.loads(getattr(args, name.replace('-', '_')).read_text(encoding='utf-8'))
        if not result['complete']: raise ValueError('incomplete '+name)
        return result
    before, after = read('baseline'), read('candidate')
    old_zx0, new_zx0 = read('old-zx0'), read('new-zx0')
    old_size, new_size = read('old-storage'), read('new-storage')
    data, cache_data = args.stream.read_bytes(), args.cache_stream.read_bytes()
    _, maps = unpack(cache_data, 32, 4, return_maps=True)
    tables, mapping, packets = frames(data)
    if (before['stream_sha256'] != sha(data) or after['stream_sha256'] != sha(data)
            or before['states_sha256'] != after['states_sha256']
            or after['cache_stream_sha256'] != sha(cache_data)
            or before['output_code_sha256'] != after['output_code_sha256']
            or old_zx0['input_sha256'] != old_size['input_sha256']
            or new_zx0['input_sha256'] != new_size['input_sha256']
            or new_zx0['input_sha256'] != sha(cache_data)
            or not len(before['frames']) == len(after['frames']) == len(maps) == len(packets)):
        raise ValueError('inconsistent source or report')
    deltas = []
    for index, (old, new, mask, (group, _)) in enumerate(zip(before['frames'], after['frames'], maps, packets)):
        expected = selective_cache_delta_tstates(mask, bool(group[1] & 128))
        delta = new['total_tstates']-old['total_tstates']
        if (delta != expected or old['index'] != index or new['index'] != index
                or old['page_writes'] != new['page_writes']
                or any(old['stages'][s] != new['stages'][s] for s in ('output', 'metadata', 'handoff'))):
            raise AssertionError('frame delta differs')
        deltas.append(dict(index=index, cached=bool(group[1] & 128), copied_groups=sum(v.bit_count() for v in mask),
                           delta_tstates=delta, total_tstates=new['total_tstates']))
    total = sum(r['total_tstates'] for r in after['frames'])
    if total != sum(r['count']*r['tstates'] for r in after['instruction_histogram']):
        raise AssertionError('instruction histogram differs')
    saving = -sum(r['delta_tstates'] for r in deltas)
    extra_zx0 = new_zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates']
    added = new_size['zx0_with_headers_bytes']-old_size['zx0_with_headers_bytes']
    sectors = (added+255)//256
    options = dict(hybrid=True, skip_empty=True, intra_above=True, intra_extended=True,
                   fast_fragments=True, unrolled_motion=True, split_literals=True, raw_attributes=True)
    old_code, old_labels, _, _ = build(tables, mapping, OFFSETS, **options)
    code, labels, _, _ = build(tables, mapping, OFFSETS, **options, selective_cache=True)
    combined = total+new_zx0['summary']['total_tstates']
    result = dict(scope=__doc__, complete=True, baseline_commit='73a1879', frames=len(deltas),
        stream_sha256=sha(data), cache_stream_sha256=sha(cache_data), states_sha256=after['states_sha256'],
        code_bytes_before=len(old_code), code_bytes_after=len(code), code_end_before=old_labels['end'],
        code_end_after=labels['end'], relocated_wrapper=after['wrapper_labels']['run'],
        pipeline=after['summary'], pipeline_saved_tstates=saving, added_banked_zx0_tstates=extra_zx0,
        net_measured_cpu_saving_tstates=saving-extra_zx0,
        zx0_bytes=new_size['zx0_with_headers_bytes'], added_bytes=added, added_sectors_roundup=sectors,
        preliminary_three_trd_margin_bytes=1937664-new_size['zx0_with_headers_bytes'],
        average_break_even_added_sector_ms=(saving-extra_zx0)/3545400/sectors*1000,
        separate_cpu_sum_tstates=combined, separate_cpu_mean_tstates=combined/len(deltas),
        nominal_mean_remaining_tstates=425448-combined/len(deltas), frame_deltas=deltas,
        slower_frames=sum(r['delta_tstates'] > 0 for r in deltas),
        unchanged_frames=sum(r['delta_tstates'] == 0 for r in deltas),
        frame_pacing_verified=False, disk_delivery_verified=False, release=False,
        note='Separate measured CPU sums only. Host packet input, map copies, AY/IRQ, ULA and disk excluded.')
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'frame_deltas'}, indent=2))


if __name__ == '__main__':
    main()
