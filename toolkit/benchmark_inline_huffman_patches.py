"""Execute bank-6 inline Huffman patches for all exact independent volumes.

Compare compact/native pixels and per-frame CPU cost against the complete
relocated baseline. Counts include compiled metadata/reconstruction/native
output, but not ZX0/queue, disk, ROM, IRQ cadence or ULA waits.
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
from frame_output_pipeline import Harness,frames,serialized_masks,display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from build_fap3_trd import sha
import uncontended_frame as relocation
import inline_huffman_patches as inline


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('directory','states','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--model',type=Path,default=Path('toolkit/combined_uncontended_cpu.json'))
    p.add_argument('--limit',type=int,help='Per-volume smoke only; never complete')
    args=p.parse_args();model=json.loads(args.model.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if (not model['complete'] or not model['full_compact_and_both_native_exact']
        or model['checked_frames']!=len(states) or sha(states.tobytes())!=model['states_sha256']):
        raise ValueError('incomplete or different baseline')
    result=dict(complete=False,release=False,baseline_commit='a6bbbb0',scope=__doc__,
        source_sha256=sha(Path(__file__).read_bytes()),states_sha256=model['states_sha256'],
        model_sha256=sha(args.model.read_bytes()),volumes=[])
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
            h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,
                register_fragments=True,cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
            c=h.cpu;c.guarding=False
            if start:c.banks[5][0x2400:0x3300]=states[start-1].tobytes()
            for bank,i in ((7,start-2),(5,start-1)):
                if i>=0:
                    s=display_screen(states[i].tobytes(),black_borders=True);s=bytes(6144)+s[6144:]
                    c.banks[bank][:6912]=s;h.expected_screens[bank]=s
            relocation.install_stage(h);generated=inline.install_stage(h,tables,mapping)
            volume=dict(part=part,start=start,end=end,raw_sha256=sha(raw),inline_patches=generated,frames=[])
            result['volumes'].append(volume);previous=Counter()
            for i in range(start,min(end,start+args.limit) if args.limit else end):
                local=i-start;group,native=packets[i]
                if start and local<2:native=b'\xff'*80
                actual=relocation.run_stage(h,group,native,states[i].tobytes(),local,meta[i],details[i]['cache'])
                saved=v['frames'][local];before=saved['tstates'];after=actual['total_tstates']
                counts=h.inline_counts-previous;previous=h.inline_counts.copy();wanted=inline.delta(counts)
                if saved['frame']!=i or after-before!=wanted:
                    raise AssertionError(('instruction count differs',part,i,before,after,counts,wanted))
                volume['frames'].append(dict(frame=i,baseline_tstates=before,tstates=after,
                    delta_tstates=after-before,entries=counts['entries'],short=counts['symbols']-counts['long'],long=counts['long']))
                if local%200==0:save();print(f'Exact inline compact/screens/cycle formula: part {part}, {local+1}/{end-start}',flush=True)
            volume['checked_frames']=len(volume['frames'])
            for key in ('baseline_tstates','tstates','delta_tstates','entries','short','long'):
                volume[key]=sum(f[key] for f in volume['frames'])
            save()
        result.update(complete=args.limit is None,checked_frames=sum(v['checked_frames'] for v in result['volumes']),
                      full_compact_and_both_native_exact=True,
                      slower_frames=sum(f['delta_tstates']>0 for v in result['volumes'] for f in v['frames']))
        for key in ('baseline_tstates','tstates','delta_tstates','entries','short','long'):
            result[key]=sum(v[key] for v in result['volumes'])
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k!='volumes'}),flush=True)


if __name__=='__main__':main()
