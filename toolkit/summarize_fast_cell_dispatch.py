"""Compare complete shared-CPU runs with identical pictures, packets and AY."""
import argparse
from collections import Counter
import json
from pathlib import Path

import cell_screen_z80 as machine
from frame_output_pipeline import frames
from probe_lossless_layouts import sha


def summarize(baseline, candidate, stream, banked, storage):
    if not all(r['complete'] for r in (baseline, candidate, banked, storage)):
        raise ValueError('complete reports required')
    if (baseline['states_sha256'] != candidate['states_sha256']
            or baseline['stream_sha256'] != candidate['stream_sha256']
            or candidate['stream_sha256'] != sha(stream)
            or baseline['reconstruction_code_sha256'] != candidate['reconstruction_code_sha256']
            # Draw state moves with its code; wrapper operands change, but
            # instruction sequence, state layout and timing must stay equal.
            or baseline['wrapper_labels'] != candidate['wrapper_labels']
            or [(r['instruction'], r['tstates']) for r in baseline['instruction_listing'] if r['phase'] == 'handoff']
            != [(r['instruction'], r['tstates']) for r in candidate['instruction_listing'] if r['phase'] == 'handoff']
            or baseline['metadata_code_hex'] != candidate['metadata_code_hex']
            or storage['input_sha256'] != banked['input_sha256']):
        raise ValueError('inconsistent evidence')
    _, _, packets = frames(stream)
    if len(packets) != len(baseline['frames']) or len(packets) != len(candidate['frames']):
        raise ValueError('different frame count')
    stages, rows = Counter(), []
    for i, (old, new, (_, mask)) in enumerate(zip(baseline['frames'], candidate['frames'], packets)):
        delta = new['total_tstates']-old['total_tstates']
        expected = machine.expected_tstates(mask, fast_mask_dispatch=True)-machine.expected_tstates(mask)
        if (old['index'] != i or new['index'] != i or delta != expected or delta > 0
                or old['page_writes'] != new['page_writes']
                or {k:v for k,v in old['stages'].items() if k != 'output'}
                != {k:v for k,v in new['stages'].items() if k != 'output'}):
            raise AssertionError('per-frame timing or unchanged stages differ')
        for k, v in new['stages'].items():
            stages[k] += v
        rows.append(dict(index=i, baseline_output_tstates=old['stages']['output'],
                         output_tstates=new['stages']['output'], delta_tstates=delta))
    total = sum(stages.values())
    if sum(r['count']*r['tstates'] for r in candidate['instruction_histogram']) != total:
        raise AssertionError('instruction histogram differs')
    count = len(rows)
    zx0 = banked['summary']['total_tstates']
    before = sum(r['baseline_output_tstates'] for r in rows)
    after = stages['output']
    return dict(scope=__doc__, complete=True, baseline_commit='1ebb4ec',
        states_sha256=candidate['states_sha256'], stream_sha256=candidate['stream_sha256'],
        frames=count, old_code_bytes=len(machine.build()[0]),
        new_code_bytes=len(machine.build(fast_mask_dispatch=True)[0]),
        unchanged_compressed_bytes=storage['zx0_with_headers_bytes'],
        no_additional_pixel_changes=True, output_before_tstates=before,
        output_tstates=after, output_delta_tstates=after-before,
        output_mean_tstates=after/count, output_percent_saved=100*(before-after)/before,
        stages=stages, pipeline=candidate['summary'],
        separate_banked_zx0_tstates=zx0, separate_cpu_sum_tstates=total+zx0,
        separate_cpu_mean_tstates=(total+zx0)/count,
        nominal_mean_remaining_tstates=425448-(total+zx0)/count,
        frame_deltas=rows, frame_pacing_verified=False, disk_delivery_verified=False,
        note='Packet input, AY, contention and disk remain excluded; no playable release claim.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'stream', 'banked', 'storage', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    def read(n): return json.loads(getattr(args, n).read_text(encoding='utf-8'))
    result = summarize(read('baseline'), read('candidate'), args.stream.read_bytes(), read('banked'), read('storage'))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'frame_deltas'}, indent=2))


if __name__ == '__main__':
    main()
