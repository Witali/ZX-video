"""Execute selected-fragment frames with the current full frame-stage CPU.

Compare every compact byte and both full screens on the entire specified
independent volume. Baseline uses a saved complete stage execution with an
identical instruction count. No ZX0, queue, IRQ, ULA or disk time is included.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_static_cache_borders import OPTIONS
from bulk_frame_stream import unpack as unpack_bulk,read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness,frames,serialized_masks,display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('raw','states','model','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--part',type=int,required=True)
    args=p.parse_args();model=json.loads(args.model.read_bytes())
    if not model['complete']:raise ValueError('partial baseline')
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if sha(states.tobytes())!=model['states_sha256']:raise ValueError('states differ')
    v=next(v for v in model['volumes'] if v['part']==args.part)
    start,end=v['start'],v['end'];raw=args.raw.read_bytes()
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells);meta=serialized_masks(cells)
    r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
    details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    if count!=len(states):raise ValueError('different frame count')
    h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,register_fragments=True,**OPTIONS)
    c=h.cpu;c.guarding=False
    if start:c.banks[5][0x2400:0x3300]=states[start-1].tobytes()
    for bank,i in ((7,start-2),(5,start-1)):
        if i>=0:
            screen=display_screen(states[i].tobytes(),black_borders=True)
            screen=bytes(6144)+screen[6144:]
            c.banks[bank][:6912]=screen;h.expected_screens[bank]=screen
    result=dict(complete=False,release=False,scope=__doc__,raw_sha256=sha(raw),
        states_sha256=sha(states.tobytes()),baseline_report_sha256=sha(args.model.read_bytes()),
        part=args.part,start=start,end=end,whole_movie_verified=False,frames=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for i in range(start,end):
            local=i-start;group,native=packets[i]
            if start and local<2:native=b'\xff'*80
            actual=h.run(group,native,states[i].tobytes(),local,encoded_metadata=meta[i],cache_map=details[i]['cache'])
            before=v['frames'][local]['tstates'];after=actual['total_tstates']
            result['frames'].append(dict(frame=i,baseline_tstates=before,tstates=after,delta_tstates=after-before))
            if local%100==0:save();print(f'Exact compact and both screens: {local+1}/{end-start}',flush=True)
        result.update(complete=True,checked_frames=end-start,full_volume_compact_and_both_native_exact=True,
            **{k:sum(f[k] for f in result['frames']) for k in ('baseline_tstates','tstates','delta_tstates')},
            slower_frames=sum(f['delta_tstates']>0 for f in result['frames']))
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k!='frames'}),flush=True)


if __name__=='__main__':main()
