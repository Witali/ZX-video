"""Execute relocated stages for all three independent volumes, byte for byte.

Host supplies packets, not a timed disk stream. Real Z80 instructions check
all compact/native bytes and the unchanged per-frame CPU counts against the
saved current volume model. ULA, disk, IRQ and queue time are excluded.
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
import uncontended_frame as relocation


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('directory','states','model','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--limit',type=int,help='Partial debugging only; never marks the run complete')
    args=p.parse_args();model=json.loads(args.model.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if not model['complete'] or sha(states.tobytes())!=model['states_sha256']:raise ValueError('input differs')
    result=dict(complete=False,release=False,baseline_commit='30de92c',scope=__doc__,
        states_sha256=model['states_sha256'],model_sha256=sha(args.model.read_bytes()),volumes=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for v in model['volumes']:
            part,start,end=v['part'],v['start'],v['end'];raw=(args.directory/f'volume-{part}.raw').read_bytes()
            if sha(raw)!=v['raw_sha256']:raise ValueError('raw differs')
            cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
            tables,mapping,packets=frames(cells);meta=serialized_masks(cells)
            r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
            details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
            h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,register_fragments=True,**OPTIONS)
            c=h.cpu;c.guarding=False
            if start:c.banks[5][0x2400:0x3300]=states[start-1].tobytes()
            for bank,i in ((7,start-2),(5,start-1)):
                if i>=0:
                    s=display_screen(states[i].tobytes(),black_borders=True);s=bytes(6144)+s[6144:]
                    c.banks[bank][:6912]=s;h.expected_screens[bank]=s
            audit=relocation.install_stage(h)
            volume=dict(part=part,start=start,end=end,raw_sha256=sha(raw),relocation=audit,frames=[])
            result['volumes'].append(volume)
            for i in range(start,min(end,start+args.limit) if args.limit else end):
                local=i-start;group,native=packets[i]
                if start and local<2:native=b'\xff'*80
                actual=relocation.run_stage(h,group,native,states[i].tobytes(),local,meta[i],details[i]['cache'])
                before=v['frames'][local]['stage_tstates'];after=actual['total_tstates']
                if after!=before:raise AssertionError(('instruction count differs',part,i,before,after))
                volume['frames'].append(dict(frame=i,baseline_tstates=before,tstates=after,delta_tstates=after-before))
                if local%200==0:save();print(f'Exact relocated compact and both screens: part {part}, {local+1}/{end-start}',flush=True)
            volume.update(checked_frames=len(volume['frames']),baseline_tstates=sum(f['baseline_tstates'] for f in volume['frames']),
                          tstates=sum(f['tstates'] for f in volume['frames']),delta_tstates=0)
            save()
        result.update(complete=args.limit is None,checked_frames=sum(v['checked_frames'] for v in result['volumes']),
                      full_compact_and_both_native_exact=True,delta_tstates=0)
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k!='volumes'}),flush=True)


if __name__=='__main__':main()
