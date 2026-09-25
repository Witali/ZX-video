"""Execute all frame stages and check register-fragment deltas against the baseline.

Host supplies packets; ZX0, IRQ/ULA and disk are excluded. Every compact/native
byte is checked by the pipeline, and every instruction uses its timing table.
"""
import argparse
from collections import Counter
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
from test_register_fragments import DELTAS,primitive_cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','baseline','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();raw=args.raw.read_bytes();baseline=json.loads(args.baseline.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    options=dict(OPTIONS,static_cache_borders=True,carry_huffman=True)
    if (not baseline['complete'] or baseline['raw_sha256']!=sha(raw)
        or baseline['states_sha256']!=sha(states.tobytes()) or baseline['options']!=options):
        raise ValueError('baseline input/options differ')
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells);meta=serialized_masks(cells)
    r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
    details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    if count!=len(states) or count!=len(baseline['frames']):raise ValueError('partial baseline')
    h=Harness(tables,mapping,register_fragments=True,**options)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='7152e10',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        baseline_report_sha256=sha(args.baseline.read_bytes()),options=dict(options,register_fragments=True),
        baseline_code_end=baseline['code_end'],code_end=h.recon['end'],extra_buffer_bytes=0,extra_stack_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_player_verified=False,primitive_cases=primitive_cases(),frames=[])
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    try:
        for i,((group,native),state,detail) in enumerate(zip(packets,states,details)):
            frame=h.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=detail['cache'])
            modes=Counter(v for v in group[3] if v in DELTAS)
            delta=sum(DELTAS[v]*n for v,n in modes.items());before=baseline['frames'][i]['tstates']
            if frame['total_tstates']!=before+delta:raise AssertionError(('frame cycles',i,before,frame,delta))
            result['frames'].append(dict(frame=i,fragment_counts=dict(modes),baseline_tstates=before,
                tstates=frame['total_tstates'],delta_tstates=delta))
            if i%250==0:save();print(f'Exact compact/both screens and fragment cycles: {i+1}/{count}',flush=True)
        for key in ('baseline_tstates','tstates','delta_tstates'):
            result[key]=sum(v[key] for v in result['frames'])
        result.update(complete=True,checked_frames=count,full_compact_and_both_native_exact=True,
            slower_frames=sum(v['delta_tstates']>0 for v in result['frames']))
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k not in ('frames','primitive_cases')}),flush=True)


if __name__=='__main__':main()
