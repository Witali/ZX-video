"""Execute every FAP3 frame with combined no-op checks and compare exact cycles.

Z80 executes metadata, reconstruction, Huffman, cache and native output.
Host supplies original packet inputs; ZX0, AY, ULA, ROM and disk excluded.
Baseline totals are derived with formulas checked by paired opcode tests;
the executed scanner histogram must also equal the absolute formula.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha
from probe_fast_noop_scan import frame_runs, scanner_tstates


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('raw','states','output'): p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args();raw = args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets = frames(cells);meta = serialized_masks(cells)
    r = Reader(raw);_,_,count,_,_ = read_header(r,magic=b'FAP3')
    details = [read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    if count != len(states) or count != len(packets): raise ValueError('frame counts differ')
    options = dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,selective_cache=True,
        constant_attribute_borders=True,skip_black_borders=True,unrolled_cache=True,skip_noop_runs=True,
        skip_static_stripes=True,attribute_groups=True,attribute_flags=True,gray_cells=True,sparse_patches=True)
    old,h = [Harness(tables,mapping,fast_noop_scan=v,**options) for v in (False,True)]
    rows = []
    report = dict(complete=False,release=False,scope=__doc__,baseline_commit='491db7b',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames_expected=count,options=options,
        full_player_verified=False,nominal_deadlines_verified=False,disk_delivery_verified=False,
        stream_delta_bytes=0,new_buffer_bytes=0,disk_ring_bytes=65536,extra_stack_bytes=0,
        baseline_scanner_bytes=old.recon['noop_scanner_end']-0x7a00,scanner_bytes=h.recon['noop_scanner_end']-0x7a00,
        baseline_scanner_hex=bytes(old.cpu.read8(a) for a in range(0x7a00,old.recon['noop_scanner_end'])).hex(),
        scanner_hex=bytes(h.cpu.read8(a) for a in range(0x7a00,h.recon['noop_scanner_end'])).hex(),
        instruction_listing=[v for v in h.instructions.values() if v['stage'] == 'noop_control'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        baseline_comparison='Exact formula; paired execution in test_fast_noop_scan, every vector alignment.',
        frames=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): args.output.write_text(json.dumps(report,indent=2)+'\n')
    previous = 0
    try:
        for i,((group,native),state,detail) in enumerate(zip(packets,states,details)):
            result = h.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=detail['cache'])
            runs,patches = frame_runs(group[3],group[4])
            # tile dispatch=37 T; tile_done=71 T, neither is scanner stage.
            before = sum(scanner_tstates(k,t)-37 for k,t in runs)+patches*(257-37-71)
            after = sum(scanner_tstates(k,t,True)-37 for k,t in runs)+patches*(251-37-71)
            total = sum(t*n for (pc,t),n in h.histogram.items() if h.instructions[pc]['stage'] == 'noop_control')
            if total-previous != after: raise AssertionError(f'absolute scanner cycle mismatch at {i}: {total-previous} != {after}')
            previous = total;delta = after-before
            rows.append(dict(frame=i,baseline_scanner_tstates=before,scanner_tstates=after,delta_tstates=delta,
                baseline_total_tstates=result['total_tstates']-delta,total_tstates=result['total_tstates']))
            if i % 250 == 0: save();print(f'Exact scanner cycles, compact and both screens: {i+1}/{count}',flush=True)
        stages = Counter()
        for (pc,t),n in h.histogram.items():
            row = h.instructions[pc];stages[row['phase']+'/'+row['stage']] += t*n
        report.update(complete=True,checked_frames=len(rows),exact_all_compact_and_native_screens=True,
            baseline_scanner_tstates=sum(v['baseline_scanner_tstates'] for v in rows),
            scanner_tstates=sum(v['scanner_tstates'] for v in rows),
            delta_tstates=sum(v['delta_tstates'] for v in rows),
            baseline_total_tstates=sum(v['baseline_total_tstates'] for v in rows),
            total_tstates=sum(v['total_tstates'] for v in rows),
            slower_frames=sum(v['delta_tstates']>0 for v in rows),
            max_extra_frame_tstates=max(v['delta_tstates'] for v in rows),stages=dict(stages))
    except Exception as exc:
        report['failure'] = repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in report.items() if k not in
        ('frames','instruction_listing','baseline_scanner_hex','scanner_hex')}),flush=True)


if __name__ == '__main__': main()
