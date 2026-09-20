"""Execute complete native output for all original FAP3 frames with Gray cells.

Host supplies final compact states, native masks and raw/metadata flags.
Real Z80 prepares attribute lists, copies the map and renders both banks.
The baseline is the previous instruction-table formula checked by the old
full output report and paired old/new tests. No bitmap reconstruction,
ZX0, packet parsing, AY cadence, ULA, ROM or physical disk is timed here.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import attribute_groups_z80 as groups
import cell_screen_z80 as machine
from bulk_frame_stream import read_packet
from frame_output_pipeline import Harness as Pipeline,MAP,display_screen
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('states','raw','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(raw); _,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    if len(states)!=count: raise ValueError('different frames')
    opts=dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,selective_cache=True,
        constant_attribute_borders=True,skip_black_borders=True,unrolled_cache=True,
        skip_noop_runs=True,skip_static_stripes=True,attribute_groups=True,attribute_flags=True)
    h=Pipeline(tables,mapping,gray_cells=True,**opts); cpu=h.cpu
    original_write=cpu.write8
    def write8(address,value):
        if cpu.guarding and cpu.phase=='output':
            offset=None
            if 0x4000<=address<0x5b00: offset=address-0x4000
            if 0xc000<=address<0xdb00 and cpu.port_7ffd&7==7: offset=address-0xc000
            if offset is not None:
                if offset<6144:
                    y=((offset>>8)&7)|((offset>>2)&0x38)|((offset>>5)&0xc0)
                    if not 24<=y<168: raise AssertionError(('black bitmap border write',address))
                elif not 96<=offset-6144<672: raise AssertionError(('attribute border write',address))
        original_write(address,value)
    cpu.write8=write8
    report=dict(scope=__doc__,complete=False,release=False,baseline_commit='dcfb953',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames_expected=count,
        compressed_stream_delta_bytes=0,full_player_verified=False,disk_delivery_verified=False,ula_verified=False,
        nominal_deadlines_verified=False,renderer_code_hex=h.draw_code.hex(),renderer_labels=h.draw,
        instruction_listing=[v for v in h.instructions.values() if v['phase'] in ('output','attribute_groups')],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        old_sparse_cell_tstates=289,new_sparse_cell_tstates=254,delta_per_sparse_cell=-35,
        memory=dict(renderer=[machine.CODE,h.draw['end']],attribute_controller=[0x9360,h.recon['attribute_flag_end']],
            new_ring_or_framebuffer_bytes=0,code_bytes_delta=-10),frames=[])
    def save():
        header=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
        args.output.write_text(header[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in report['frames'])+'\n  ]\n}\n',encoding='utf-8')
    try:
        for i,state in enumerate(states):
            _,d=read_packet(r,stored_guards=False)
            native=d['payload'][d['coded_offset']-80:d['coded_offset']]
            start=sum(map(len,d['ticks']))+5+195
            masks=restore(d['payload'][start:start+d['mask_bytes']],1,480,4)[384:]
            if i>=2 and not d['flags']&64 and (any(masks[:12]) or any(masks[84:])):
                raise AssertionError('nonzero constant attribute border masks')
            flags=np.packbits(np.frombuffer(masks,dtype=np.uint8)!=0).tobytes()
            cpu.guarding=False; target=7 if i%2==0 else 5; page=0x16 if target==7 else 0x1e
            cpu.target_bank=target; cpu.port_7ffd=page
            for base,blob in ((machine.FRAME,state.tobytes()),(MAP,native),(0xbfb0,flags)):
                for j,v in enumerate(blob): cpu.write8(base+j,v)
            cpu.write8(h.recon['raw_attributes'],int(bool(d['flags']&64)))
            preparation=h.execute(groups.CODE)['total_tstates']
            if preparation!=groups.prepare_tstates(flags[1:11],raw=bool(d['flags']&64),warmup=i<2):
                raise AssertionError('list preparation formula differs')
            counts=[cpu.read8(base) for base in groups.LISTS]
            cpu.guarding=False; cpu.write8(h.draw['saved_page'],page)
            cpu.a=0xc0 if target==7 else 0x40; cpu.set_hl(MAP)
            drawn=h.execute(h.draw['draw'])
            old=machine.expected_tstates(native,fast_mask_dispatch=True,constant_attribute_borders=True,
                skip_black_borders=True,attribute_group_counts=counts)
            new=machine.expected_tstates(native,fast_mask_dispatch=True,constant_attribute_borders=True,
                skip_black_borders=True,attribute_group_counts=counts,gray_cells=True)
            if drawn['total_tstates']!=new or cpu.port_7ffd!=page or drawn['page_writes']!=[page|1,page]:
                raise AssertionError('output cycles or paging differs')
            h.expected_screens[target]=display_screen(state.tobytes(),black_borders=True)
            for bank,wanted in h.expected_screens.items():
                if bytes(cpu.banks[bank][:6912])!=wanted: raise AssertionError(('native screen differs',i,bank))
            if bytes(cpu.banks[5][0x2400:0x3300])!=state.tobytes() or bytes(cpu.banks[5][0x1b00:0x2400])!=b'\xa5'*0x900:
                raise AssertionError('compact or TR-DOS workspace changed')
            partial=sum(sum(v.bit_count() for v in native[b*4:b*4+4]) for b in range(1,19)
                if native[b*4:b*4+4]!=b'\xff'*4)
            if new-old!=-35*partial: raise AssertionError('sparse delta differs')
            report['frames'].append(dict(index=i,target_bank=target,partial_cells=partial,prepare_tstates=preparation,
                baseline_output_tstates=old,output_tstates=new,output_delta=new-old,
                all_native_pixel_and_attribute_errors=0))
            if i%250==0: save(); print(f'Gray-cell native output verified {i+1}/{count}',flush=True)
        r.end(); before=sum(v['baseline_output_tstates'] for v in report['frames'])
        after=sum(v['output_tstates'] for v in report['frames']); stages=Counter()
        for (pc,t),n in h.histogram.items(): stages[h.instructions[pc]['phase']+'/'+h.instructions[pc]['stage']]+=t*n
        report.update(complete=True,checked_frames=count,baseline_output_tstates=before,output_tstates=after,
            delta_tstates=after-before,change_percent=100*(after-before)/before,stages=dict(stages),
            histogram=[dict(address=pc,tstates=t,count=n) for (pc,t),n in sorted(h.histogram.items())],
            every_frame_no_slower=True,black_border_writes=0,exact_both_native_screens=True)
        if sum(stages.values())!=after+sum(v['prepare_tstates'] for v in report['frames']): raise AssertionError('histogram differs')
    except Exception as exc:
        report['failure']=repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in report.items() if k in ('complete','checked_frames','baseline_output_tstates',
        'output_tstates','delta_tstates','change_percent','memory')},indent=2),flush=True)


if __name__=='__main__': main()
