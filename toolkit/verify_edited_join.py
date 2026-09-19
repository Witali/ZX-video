"""Execute FSF1 reconstruction and native output near edited joins on Z80.

Partial CPU fixture: host supplies one preceding state and expanded group
metadata. Screen output is a separate CPU instance. This excludes combined
memory placement, ZX0, disk/ROM/ULA/IRQ and cannot establish playback speed.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_causal_tiles import Harness
from benchmark_compact_screen import Harness as ScreenHarness
import causal_tile_z80 as machine
from probe_fast_fragments import SIZES
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, read_group, OFFSETS
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--timeline-report', type=Path, required=True)
    p.add_argument('--baseline-cpu', type=Path, required=True)
    p.add_argument('--baseline-screen', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = (args.build/'fsf/separated.raw').read_bytes()
    with np.load(args.build/'fsf/motion.npz', allow_pickle=False) as saved:
        states = saved['states']
    timeline = json.loads(args.timeline_report.read_text(encoding='utf-8'))
    old = json.loads(args.baseline_cpu.read_text(encoding='utf-8'))
    old_screen = json.loads(args.baseline_screen.read_text(encoding='utf-8'))
    r = Reader(source)
    model, _, count, mapping, tables = read_header(r, magic=b'FSF1')
    if (model != 0 or len(states) != count or not timeline['complete']
            or sha(states.tobytes()) != timeline['states_sha256']
            or not old['complete'] or not old_screen['complete']):
        raise ValueError('mismatched or incomplete inputs')
    joins = [j['output_frame'] for j in timeline['joins']]
    if not joins:
        raise ValueError('no join to verify')
    h = Harness(tables, mapping, OFFSETS, skip_empty=True, hybrid=True, intra_above=True,
        intra_extended=True, fast_fragments=True, unrolled_motion=True, split_literals=True)
    screen = ScreenHarness(first=8, rows=80)
    if h.code.hex() != old['code_hex'] or screen.code.hex() != old_screen['code_hex']:
        raise ValueError('decoder code differs from the measured baseline')
    rows, first, previous_end = [], 0, None
    while first < count:
        n, flags, bits, vectors, bm, at, encoded = read_group(r, count-first, fast_fragments=True)
        literals = r.take(sum(SIZES.get(v, 0) for v in vectors))
        if any(first < j+9 and first+n > j-8 for j in joins):
            if previous_end != first:
                h.cpu.guarding = False
                previous = states[first-1].tobytes() if first else bytes(3840)
                for i, value in enumerate(previous):
                    h.cpu.write8(machine.FRAME+i, value)
            h.begin(encoded, vectors, bm, at, literals=literals)
            for i in range(n):
                result = h.run(i, states[first+i].tobytes())
                drawn = screen.run(states[first+i].tobytes(), first+i)
                if result['cache'] != bool(flags & (128 >> i)):
                    raise AssertionError('cache flag mismatch')
                rows.append(dict(index=first+i, reconstruction=result,
                    native_output_tstates=drawn['tstates'], output_sha256=drawn['output_sha256'],
                    two_stages_tstates=result['total_tstates']+drawn['tstates']))
            if h.position() != bits or h.literal_position() != len(literals):
                raise AssertionError('group consumption differs')
            previous_end = first+n
        first += n
    r.end()
    report = dict(scope=__doc__, complete=True, full_movie_cpu_verified=False,
        input_sha256=sha(source), states_sha256=sha(states.tobytes()), frames_total=count,
        frames_verified=len(rows), rows=rows, joins=joins,
        reconstruction_code_sha256=sha(h.code), native_output_code_sha256=sha(screen.code),
        code_unchanged_from_baseline=True, instruction_delta_tstates=0,
        two_stages_max_tstates=max(row['two_stages_tstates'] for row in rows),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_frame_delivery_measured=False, release_disks_changed=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
