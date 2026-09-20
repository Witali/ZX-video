"""Change only native n-2 output masks; preserve every encoded value and AY byte.

Choose the cheaper sparse/dense native path by its instruction-table cost,
or use threshold 16 to test the disk-size tradeoff. Full PC replay verifies
active pixels in both alternating screens. Predicted CPU deltas cover only
native output, not ZX0, disk delivery or actual publication deadlines.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from bulk_frame_stream import read_packet
from cell_screen_z80 import expected_tstates
from probe_lossless_layouts import sha,measure
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','cache','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    if states.shape!=(count,3840): raise ValueError('different states')
    variants={name:bytearray(raw) for name in ('gray_optimal','compact_16')}
    report=dict(scope=__doc__,complete=False,release=False,baseline_commit='dcfb953',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames_expected=count,
        original_raw_bytes=len(raw),exact_ay_and_coded_fields=True,actual_cpu_run=False,
        disk_delivery_verified=False,cadence_verified=False,variants={},frames=[])
    history=[np.zeros((18,4,32),dtype=np.uint8) for _ in range(2)]
    cpu_options=dict(fast_mask_dispatch=True,constant_attribute_borders=True,skip_black_borders=True,gray_cells=True)
    args.cache.mkdir(parents=True,exist_ok=True)
    for i,state in enumerate(states):
        start=r.pos; _,d=read_packet(r,stored_guards=False)
        pos=start+2+d['coded_offset']-80; original=raw[pos:pos+80]
        active=state[384:2688].reshape(18,4,32); previous=history[i%2]
        dirty=(active!=previous).any(axis=1); packed=np.packbits(dirty,axis=1)
        changed=dirty.sum(axis=1); empty=(packed==0).sum(axis=1)
        before=expected_tstates(original,**cpu_options); row=dict(index=i,baseline_gray_output_formula=before)
        for name,stream in variants.items():
            selected=dirty.copy()
            if name=='gray_optimal':
                full=(5853+4*(np.arange(1,19)&1))<=261*changed-136*empty
            else: full=changed>=16
            selected[full]=True
            candidate=original[:4]+np.packbits(selected,axis=1).tobytes()+original[76:]
            restored=previous.copy(); np.copyto(restored,active,where=selected[:,None,:])
            if not np.array_equal(restored,active): raise AssertionError(('native coverage differs',i,name))
            stream[pos:pos+80]=candidate
            # Reparse the serialized packet; the only differing bytes may be
            # the active native mask. This includes all original AY records.
            q=Reader(bytes(stream[start:r.pos])); _,decoded=read_packet(q,stored_guards=False); q.end()
            if (decoded['ticks']!=d['ticks'] or decoded['coded_offset']!=d['coded_offset']
                    or decoded['payload'][:d['coded_offset']-80]!=d['payload'][:d['coded_offset']-80]
                    or decoded['payload'][d['coded_offset']:]!=d['payload'][d['coded_offset']:]):
                raise AssertionError('non-native field changed')
            after=expected_tstates(candidate,**cpu_options)
            row[name]=dict(output_delta_tstates=after-before,changed_mask_bytes=sum(a!=b for a,b in zip(original,candidate)),
                dense_bands=int(full.sum()),partial_cells=int((dirty&~full[:,None]).sum()))
        report['frames'].append(row); history[i%2]=active.copy()
    r.end()
    for name,data in variants.items():
        if len(data)!=len(raw): raise AssertionError('stream length changed')
        (args.cache/(name+'.raw')).write_bytes(data)
        rows=[row[name] for row in report['frames']]
        report['variants'][name]=dict(raw_bytes=len(data),raw_sha256=sha(data),deflate_8192_screen=measure(data,8192),
            projected_native_output_delta_tstates=sum(v['output_delta_tstates'] for v in rows),
            frames_slower_in_output=sum(v['output_delta_tstates']>0 for v in rows),
            max_output_regression_tstates=max(v['output_delta_tstates'] for v in rows),
            changed_mask_bytes=sum(v['changed_mask_bytes'] for v in rows),exact_active_native_replay=True,
            exact_other_packet_fields=True)
    report.update(complete=True,checked_frames=count)
    header=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
    args.output.write_text(header[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in report['frames'])+'\n  ]\n}\n',encoding='utf-8')
    print(json.dumps(report['variants'],indent=2),flush=True)


if __name__=='__main__': main()
