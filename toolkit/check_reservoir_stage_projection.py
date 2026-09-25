"""Check projected stage costs by executing cold starts and difficult frames.

Each selected frame starts with its exact compact/native n-1/n-2 state and
the previous attribute-group list. This validates CPU stage composition,
not a sequential full-player run, disk delivery or publication timing.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import attribute_groups_z80 as groups
from benchmark_bank_local_zx0 import sha
from benchmark_static_cache_borders import OPTIONS
from bulk_frame_stream import unpack as unpack_bulk,read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness,frames,serialized_masks,display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('directory','states','model','output'):p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();model=json.loads(args.model.read_bytes())
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if not model['complete'] or sha(states.tobytes())!=model['states_sha256']:raise ValueError('input differs')
    result=dict(complete=False,release=False,scope=__doc__,model_sha256=sha(args.model.read_bytes()),
        states_sha256=model['states_sha256'],frames=[])
    for volume in model['volumes']:
        part,start,end=volume['part'],volume['start'],volume['end']
        raw=(args.directory/f'volume-{part}.raw').read_bytes()
        if sha(raw)!=volume['raw_sha256']:raise ValueError('raw differs')
        cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
        tables,mapping,packets=frames(cells);metadata=serialized_masks(cells)
        r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
        details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
        selected=set(range(start,min(start+4,end)))|{end-1}
        selected.update(s[k]['frame'] for s in volume['scenarios'] for k in ('first_late','worst_late') if s[k])
        selected.add(max(volume['frames'],key=lambda f:f['stage_tstates'])['frame'])
        for i in sorted(selected):
            local=i-start
            h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,register_fragments=True,**OPTIONS)
            cpu=h.cpu;cpu.guarding=False
            page=0x16 if local%2==0 else 0x1e
            cpu.port_7ffd=page
            cpu.write8(h.draw['saved_page'],page);cpu.write8(h.draw['screen_base'],0xc0 if local%2==0 else 0x40)
            if i:cpu.banks[5][0x2400:0x3300]=states[i-1].tobytes()
            target=7 if local%2==0 else 5
            for bank,index in ((target,i-2),(5 if target==7 else 7,i-1)):
                if index>=0:
                    screen=display_screen(states[index].tobytes(),black_borders=True)
                    if index<start:screen=bytes(6144)+screen[6144:]
                    cpu.banks[bank][:6912]=screen;h.expected_screens[bank]=screen
            # Initial next_list=80: the first call writes list 20. The other
            # list holds the preceding frame's changed n-1 attribute groups.
            cpu.write8(h.group_labels['warmup'],max(0,2-local))
            if local:
                previous=packets[i-1][0]
                indices=[j for j in range(8,88) if previous[5][j]]
                full=local<=2 or bool(previous[1]&64)
                base=groups.LISTS[1];cpu.write8(base,72 if full else len(indices))
                if not full:
                    for j,v in enumerate(indices):cpu.write8(base+1+j,v)
            packet,native=packets[i]
            if start and local<2:native=b'\xff'*80
            actual=h.run(packet,native,states[i].tobytes(),local,encoded_metadata=metadata[i],cache_map=details[i]['cache'])
            expected=volume['frames'][local]['stage_tstates']
            if actual['total_tstates']!=expected:raise AssertionError((part,i,actual['total_tstates'],expected))
            result['frames'].append(dict(part=part,frame=i,tstates=expected,compact_and_both_native_exact=True))
            print(f'Projected stage verified by opcodes: disk {part}, frame {i}',flush=True)
    result.update(complete=True,checked_frames=len(result['frames']))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
