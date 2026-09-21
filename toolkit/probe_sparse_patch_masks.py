"""Count original FAP3 masks and compare exact sparse-patch instruction costs.

No CPU, IRQ or disk executes here. The post-Huffman variant is a rejected
unimplemented cost model: test LD A,B / OR A after applying each correction.
The implemented variant branches on SLA's existing Z flag before Huffman.
Both variants keep the compressed input and the decoded pixel values fixed.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import causal_tile_z80 as machine
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha


def post_decode_half(mask, half):
    cost = 18
    if not mask: return cost+(22 if half == 0 else 10)
    checks = range(6 if half == 0 else 7)
    for j in range(8):
        active = mask & 128; mask = (mask << 1) & 255; cost += 18
        if active:
            cost += 39
            if j in checks:
                cost += 18 if half == 0 else 19 if not mask else 13
                if not mask: return cost+22 if half == 0 else cost
        if j < 7: cost += 4 if j % 2 == 0 else 15
    return cost+(22 if half == 0 else 10)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw','output'): p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(); raw = args.raw.read_bytes()
    r = Reader(raw); _, _, count, _, _ = read_header(r, magic=b'FAP3')
    hist = [Counter(), Counter()]; rows = []
    for i in range(count):
        _, detail = read_packet(r, stored_guards=False)
        pos = sum(map(len, detail['ticks']))+8
        vectors = detail['payload'][pos:pos+192]
        masks = restore(detail['payload'][pos+192:pos+192+detail['mask_bytes']], 1, 480, 4)
        totals = dict(baseline=0, post_decode_checks=0, sparse_patches=0); selected = 0
        for v, b, c in zip(vectors, masks[:384:2], masks[1:384:2]):
            if v > 81 or not (b or c): continue
            selected += 1
            totals['baseline'] += 24; totals['post_decode_checks'] += 24; totals['sparse_patches'] += 20
            for half, m in enumerate((b, c)):
                hist[half][m] += 1
                totals['baseline'] += machine.patch_half_tstates(m, half)
                totals['post_decode_checks'] += post_decode_half(m, half)
                totals['sparse_patches'] += machine.patch_half_tstates(m, half, sparse_patches=True)
        delta = totals['sparse_patches']-totals['baseline']
        if delta != machine.patch_delta_tstates(vectors, masks[:384]): raise AssertionError('delta differs')
        rows.append(dict(index=i, selected_tiles=selected, delta_tstates=delta, **totals))
    r.end(); totals = {key:sum(v[key] for v in rows) for key in ('baseline','post_decode_checks','sparse_patches')}
    report = dict(scope=__doc__, complete=True, estimated_only=True, release=False, baseline_commit='a8f28c2',
        raw_sha256=sha(raw), frames=count, compressed_stream_delta_bytes=0,
        measured_player_cpu=False, nominal_deadlines_verified=False,
        cost_scope='patches_nonzero through RET; Huffman bodies and caller/mask-read prologue excluded',
        post_decode_model_checks=[[0,1,2,3,4,5],[0,1,2,3,4,5,6]],
        totals=totals, post_decode_delta=totals['post_decode_checks']-totals['baseline'],
        implemented_delta=totals['sparse_patches']-totals['baseline'],
        slower_frames=sum(v['delta_tstates'] > 0 for v in rows),
        max_extra_frame_tstates=max(v['delta_tstates'] for v in rows),
        masks_by_half=[dict(sorted(c.items())) for c in hist],
        popcount_histogram={str(n):sum(c[m] for c in hist for m in c if m.bit_count() == n) for n in range(9)},
        all_half_costs=[dict(mask=m,half=h,before=machine.patch_half_tstates(m,h),
                            after=machine.patch_half_tstates(m,h,sparse_patches=True))
                        for h in range(2) for m in range(256)], frames_detail=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ('frames','totals','post_decode_delta','implemented_delta',
        'slower_frames','max_extra_frame_tstates','popcount_histogram')},indent=2))


if __name__ == '__main__': main()
