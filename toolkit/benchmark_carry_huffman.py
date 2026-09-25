"""Execute every frame and verify the Huffman-only delta against a full baseline.

This stage includes metadata/reconstruction/output, but no ZX0, IRQ or disk.
The saved baseline has the same entropy source and options except bit position.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_static_cache_borders import OPTIONS
from bulk_frame_stream import unpack as unpack_bulk,read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness,frames,serialized_masks
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','baseline','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();raw=args.raw.read_bytes();baseline=json.loads(args.baseline.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if (not baseline['complete'] or baseline['raw_sha256']!=sha(raw)
        or baseline['states_sha256']!=sha(states.tobytes()) or baseline['options']!=OPTIONS):
        raise ValueError('baseline input/options differ')
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells);meta=serialized_masks(cells)
    r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
    details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    if count!=len(states) or count!=len(baseline['frames']):raise ValueError('partial baseline')
    h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,**OPTIONS)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='0cf64be',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        baseline_report_sha256=sha(args.baseline.read_bytes()),options=dict(OPTIONS,static_cache_borders=True,carry_huffman=True),
        code_end=h.recon['end'],code_growth_bytes=0,extra_buffer_bytes=0,extra_stack_bytes=0,
        baseline_comparison='Saved complete stage execution; each changed instruction path also checked in paired primitive cases.',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_player_verified=False,frames=[])
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    old_short=old_long=0
    try:
        for i,((group,native),state,detail) in enumerate(zip(packets,states,details)):
            frame=h.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=detail['cache'])
            short=h.histogram[h.recon['short_position'],7]
            long=h.histogram[h.recon['long_shift_page'],8]
            delta=-8*(short-old_short)+8*(long-old_long)
            before=baseline['frames'][i]['total_tstates']
            if frame['total_tstates']!=before+delta:raise AssertionError(('frame cycles',i,before,frame,delta))
            result['frames'].append(dict(frame=i,short_values=short-old_short,long_unaligned_values=long-old_long,
                baseline_tstates=before,tstates=frame['total_tstates'],delta_tstates=delta))
            old_short,old_long=short,long
            if i%250==0:save();print(f'Exact compact/both screens and Huffman cycles: {i+1}/{count}',flush=True)
        for key in ('short_values','long_unaligned_values','baseline_tstates','tstates','delta_tstates'):
            result[key]=sum(v[key] for v in result['frames'])
        result.update(complete=True,checked_frames=count,full_compact_and_both_native_exact=True,
            slower_frames=sum(v['delta_tstates']>0 for v in result['frames']))
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k!='frames'}),flush=True)


if __name__=='__main__':main()
