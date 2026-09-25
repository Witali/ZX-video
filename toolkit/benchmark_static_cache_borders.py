"""Execute the full reconstruction/output stage; no ZX0, IRQ or disk timing claim."""
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


def delta(vectors, enabled):
    return ((37 if vectors[0] else -1607) +
            (45 if vectors[176] else -1585)) if enabled else 0


OPTIONS = dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,selective_cache=True,
    constant_attribute_borders=True,skip_black_borders=True,unrolled_cache=True,skip_noop_runs=True,
    skip_static_stripes=True,attribute_groups=True,attribute_flags=True,gray_cells=True,
    sparse_patches=True,fast_noop_scan=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','output'): p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); raw = args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets = frames(cells); meta = serialized_masks(cells)
    r = Reader(raw); _,_,count,_,_ = read_header(r,magic=b'FAP3')
    details = [read_packet(r,stored_guards=False)[1] for _ in range(count)]; r.end()
    if count != len(states) or count != len(packets): raise ValueError('frame counts differ')
    old,h = [Harness(tables,mapping,static_cache_borders=v,**OPTIONS) for v in (False,True)]
    rows = []; report = dict(complete=False,release=False,scope=__doc__,baseline_commit='6e724f4',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),options=OPTIONS,
        source_bytes_unchanged=True,extra_buffer_bytes=0,extra_stack_bytes=0,
        baseline_code_end=old.recon['end'],code_end=h.recon['end'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        cache_zero_four_rows_tstates=1610,top_baseline_tstates=1644,top_skipped_tstates=37,
        bottom_baseline_tstates=1634,bottom_skipped_tstates=49,
        active_edge_extra_tstates=[37,45],
        baseline_comparison='Formula checked by paired sequential opcode tests, not a second full baseline run.',
        full_player_verified=False,nominal_deadlines_verified=False,disk_delivery_verified=False,frames=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    zero_before = 0; cases = Counter()
    try:
        for i,((group,native),state,detail) in enumerate(zip(packets,states,details)):
            result = h.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=detail['cache'])
            enabled = bool(group[1]&128); vectors = group[3]
            change = delta(vectors,enabled)
            zero_after = sum(t*n for (pc,t),n in h.histogram.items()
                if h.recon['cache_zero'] <= pc < h.recon['motion'])
            wanted = 1610*(bool(vectors[0])+bool(vectors[176])) if enabled else 0
            if zero_after-zero_before != wanted: raise AssertionError(('virtual row cycles',i,zero_after-zero_before,wanted))
            zero_before = zero_after
            cases[f'{int(enabled)}:{int(bool(vectors[0]))}:{int(bool(vectors[176]))}'] += 1
            rows.append(dict(frame=i,cache_enabled=enabled,active_edges=[bool(vectors[0]),bool(vectors[176])],
                baseline_total_tstates=result['total_tstates']-change,total_tstates=result['total_tstates'],delta_tstates=change))
            if i%250 == 0: save(); print(f'Exact compact/both screens and virtual-row cycles: {i+1}/{count}',flush=True)
        stages = Counter()
        for (pc,t),n in h.histogram.items():
            row = h.instructions[pc]; stages[row['phase']+'/'+row['stage']] += t*n
        report.update(complete=True,checked_frames=len(rows),exact_all_compact_and_native_screens=True,
            cases=dict(cases),baseline_total_tstates=sum(v['baseline_total_tstates'] for v in rows),
            total_tstates=sum(v['total_tstates'] for v in rows),delta_tstates=sum(v['delta_tstates'] for v in rows),
            slower_frames=sum(v['delta_tstates']>0 for v in rows),stages=dict(stages))
    except Exception as exc:
        report['failure']=repr(exc);save();raise
    save(); print(json.dumps({k:v for k,v in report.items() if k!='frames'}),flush=True)


if __name__ == '__main__': main()
