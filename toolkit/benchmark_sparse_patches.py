"""Run all FAP3 frame reconstruction/metadata/native output with sparse exits.

Host unpacks packet containers and supplies their original per-frame inputs.
Z80 executes metadata decoding, prediction, Huffman, corrections, attributes,
cache copies, native rendering and screen publication. Baseline timing is
the same run minus the exact patch delta checked by paired old/new tests.
ZX0, AY/IRQ cadence, ULA, TR-DOS and disk are excluded from this stage run.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import causal_tile_z80 as machine
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw', 'states', 'output'): p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(); raw = args.raw.read_bytes()
    with np.load(args.states, allow_pickle=False) as f: states = f['states']
    cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)), 32, 4))[0]
    tables, mapping, packets = frames(cells); metadata = serialized_masks(cells)
    r = Reader(raw); _, _, count, _, _ = read_header(r, magic=b'FAP3')
    details = [read_packet(r, stored_guards=False)[1] for _ in range(count)]; r.end()
    if len(states) != count or len(packets) != count: raise ValueError('different frame counts')
    options = dict(raw_attributes=True, decode_metadata=True, fast_mask_dispatch=True, selective_cache=True,
        constant_attribute_borders=True, skip_black_borders=True, unrolled_cache=True, skip_noop_runs=True,
        skip_static_stripes=True, attribute_groups=True, attribute_flags=True, gray_cells=True)
    h = Harness(tables, mapping, sparse_patches=True, **options)
    before = machine.build(tables, mapping, OFFSETS,
        hybrid=True, skip_empty=True, intra_above=True, intra_extended=True, fast_fragments=True,
        unrolled_motion=True, split_literals=True, raw_attributes=True, selective_cache=True,
        skip_noop_runs=True, skip_static_stripes=True, unrolled_cache=True, attribute_flags=True)
    rows = []; masks = [Counter(), Counter()]
    report = dict(scope=__doc__, complete=False, release=False, baseline_commit='a8f28c2',
        raw_sha256=sha(raw), states_sha256=sha(states.tobytes()), frames_expected=count,
        compressed_stream_delta_bytes=0, stream_sector_delta=0, options=options,
        baseline_comparison='Exact per-mask instruction delta; paired execution in test_sparse_patches',
        full_player_verified=False, nominal_deadlines_verified=False, disk_delivery_verified=False,
        ula_verified=False, before_code_hex=before[0].hex(), code_hex=h.recon_code.hex(),
        labels=h.recon, instruction_listing=list(h.instructions.values()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        memory=dict(old_reconstruction_bytes=len(before[0]), reconstruction_bytes=len(h.recon_code),
                    reconstruction_end=h.recon['end'], new_tables_bytes=0, new_buffer_bytes=0,
                    disk_ring_bytes=65536, extra_stack_bytes=0), frames=rows)
    def save():
        head = json.dumps({k:v for k,v in report.items() if k != 'frames'}, indent=2)
        args.output.write_text(head[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in rows)+'\n  ]\n}\n', encoding='utf-8')
    previous_patch = 0
    try:
        for i, ((group, mask), state, detail) in enumerate(zip(packets, states, details)):
            result = h.run(group, mask, state.tobytes(), i, encoded_metadata=metadata[i], cache_map=detail['cache'])
            for v, b, c in zip(group[3], group[4][::2], group[4][1::2]):
                if v <= 81 and (b or c): masks[0][b] += 1; masks[1][c] += 1
            total_patch = sum(t*n for (pc, t), n in h.histogram.items() if h.instructions[pc]['stage'] == 'patch')
            patch = total_patch-previous_patch; previous_patch = total_patch
            delta = machine.patch_delta_tstates(group[3], group[4])
            rows.append(dict(index=i, target_bank=result['target_bank'], baseline_patch_tstates=patch-delta,
                patch_tstates=patch, delta_tstates=delta, baseline_total_tstates=result['total_tstates']-delta,
                total_tstates=result['total_tstates'], stages=result['stages'], compact_and_native_errors=0))
            if i % 250 == 0: save(); print(f'Sparse patches, compact and both native screens verified {i+1}/{count}', flush=True)
        stages = Counter()
        for (pc, t), n in h.histogram.items():
            row = h.instructions[pc]; stages[row['phase']+'/'+row['stage']] += t*n
        old = sum(v['baseline_patch_tstates'] for v in rows); new = sum(v['patch_tstates'] for v in rows)
        if sum(stages.values()) != sum(v['total_tstates'] for v in rows): raise AssertionError('histogram differs')
        report.update(complete=True, checked_frames=len(rows), baseline_patch_tstates=old, patch_tstates=new,
            delta_tstates=new-old, patch_change_percent=100*(new-old)/old,
            baseline_total_tstates=sum(v['baseline_total_tstates'] for v in rows),
            total_tstates=sum(v['total_tstates'] for v in rows),
            slower_frames=sum(v['delta_tstates'] > 0 for v in rows),
            max_extra_frame_tstates=max(v['delta_tstates'] for v in rows),
            exact_all_compact_and_native_screens=True, stages=dict(stages),
            masks_by_half=[dict(sorted(c.items())) for c in masks],
            histogram=[dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())])
    except Exception as exc:
        report['failure'] = repr(exc); save(); raise
    save(); print(json.dumps({k:report[k] for k in ('complete','checked_frames','baseline_patch_tstates',
        'patch_tstates','delta_tstates','patch_change_percent','slower_frames','max_extra_frame_tstates','memory')}, indent=2), flush=True)


if __name__ == '__main__': main()
