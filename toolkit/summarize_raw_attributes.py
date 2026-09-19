"""Combine full raw-attribute, sparse-mask and separate ZX0 evidence.

The common CPU run includes mask expansion, reconstruction and screen output.
Host still parses headers and supplies/copies all input. ZX0/AY/disk clocks
are not integrated, so neither the size nor CPU sum proves a release.
"""
import argparse
import json
from pathlib import Path

import frame_metadata_z80
from frame_output_pipeline import serialized_masks
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stream', type=Path, required=True)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        data = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not data['complete']:
            raise ValueError('incomplete '+name)
        return data

    baseline = load('delivery_budget_375_pipeline_cpu')
    old_zx0 = load('delivery_budget_375_audio_zx0_cpu')
    choice = load('raw_attributes_128')
    raw = load('raw_attributes_128_pipeline_cpu')
    full = load('raw_attributes_128_metadata_cpu')
    audio = load('raw_attributes_128_audio_stream')
    zx0 = load('raw_attributes_128_zx0_cpu')
    storage = load('raw_attributes_128_zx0')
    data = args.stream.read_bytes()
    if (any(r['states_sha256'] != baseline['states_sha256'] for r in (choice, raw, full))
            or any(r['stream_sha256'] != sha(data) for r in (choice, raw, full))
            or raw['reconstruction_code_sha256'] != full['reconstruction_code_sha256']
            or raw['output_code_sha256'] != full['output_code_sha256']
            or raw['wrapper_code_hex'] != full['wrapper_code_hex']
            or full['metadata_expanded_by_host']
            or full['metadata_code_hex'] != frame_metadata_z80.build()[0].hex()
            or audio['cells_sha256'] != sha(data)
            or storage['input_sha256'] != audio['stream_sha256']
            or zx0['input_sha256'] != audio['stream_sha256']):
        raise ValueError('different input or machine-code evidence')
    rows, masks = [], serialized_masks(data)
    count = len(masks)
    if any(len(r['frames']) != count for r in (baseline, raw, full)) or len(choice['rows']) != count:
        raise ValueError('different frame counts')
    for index, (old, current, integrated, selected, mask) in enumerate(zip(
            baseline['frames'], raw['frames'], full['frames'], choice['rows'], masks)):
        extra = frame_metadata_z80.expected_tstates(mask)
        delta = current['total_tstates']-old['total_tstates']
        if (any(r['index'] != index for r in (old, current, integrated, selected))
                or integrated['total_tstates'] != current['total_tstates']+extra
                or integrated['stages']['metadata'] != extra
                or (delta >= 0 if selected['raw_attributes'] else delta != 55)):
            raise ValueError('per-frame delta differs at '+str(index))
        rows.append(dict(index=index, raw_attributes=selected['raw_attributes'],
            baseline_tstates=old['total_tstates'], raw_tstates=current['total_tstates'],
            raw_delta_tstates=delta, metadata_tstates=extra,
            full_tstates=integrated['total_tstates']))
    for r in (raw, full):
        if (sum(h['tstates']*h['count'] for h in r['instruction_histogram']) != r['summary']['total_tstates']
                or sum(f['total_tstates'] for f in r['frames']) != r['summary']['total_tstates']):
            raise ValueError('histogram mismatch')
    summary = dict(baseline=baseline['summary'], raw_attributes=raw['summary'],
        including_metadata=full['summary'],
        raw_delta_total_tstates=raw['summary']['total_tstates']-baseline['summary']['total_tstates'],
        metadata_total_tstates=sum(r['metadata_tstates'] for r in rows),
        metadata_max_tstates=max(r['metadata_tstates'] for r in rows),
        coded_attribute_path_delta_tstates=55, raw_attribute_routine_tstates=16209,
        new_wrapper_tstates=363, baseline_wrapper_tstates=337,
        zx0_total_tstates=zx0['summary']['total_tstates'],
        zx0_delta_tstates=zx0['summary']['total_tstates']-old_zx0['summary']['total_tstates'],
        zx0_bytes=storage['zx0_with_headers_bytes'],
        zx0_delta_bytes=storage['zx0_with_headers_bytes']-old_zx0['summary']['bytes_with_headers'],
        preliminary_three_trd_margin_bytes=1937664-storage['zx0_with_headers_bytes'])
    total = full['summary']['total_tstates']+zx0['summary']['total_tstates']
    summary.update(measured_separated_total_tstates=total,
        measured_separated_mean_tstates=total/count,
        remaining_nominal_mean_tstates=425448-total/count)
    report = dict(scope=__doc__, complete=True, baseline_commit='11dc864', frames=count,
        states_sha256=baseline['states_sha256'], stream_sha256=sha(data), summary=summary,
        metadata_code_bytes=len(frame_metadata_z80.build()[0]),
        no_additional_pixel_changes=True, existing_ay_50hz_byte_exact=True,
        packet_headers_and_input_copy_by_host=True, full_frame_delivery_measured=False,
        frame_pacing_verified=False, disk_delivery_verified=False, release_disks_changed=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', rows=rows)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
