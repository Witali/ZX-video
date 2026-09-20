"""Execute both attribute reconstruction paths on all original FAP3 tails.

Host positions the original coded/literal cursor after bitmap work, verified
independently against the source states. The real attribute Huffman primitive
and all attribute writes execute on Z80. Bitmap work, ZX0, metadata expansion,
native rendering, IRQ cadence, ULA, ROM and disk are excluded here.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import attribute_mask_z80 as machine
from attribute_update_stream import strip_attributes
from benchmark_context_huffman import word
from bulk_frame_stream import read_packet
from frame_output_pipeline import Harness as Pipeline,INPUT,ATTRS
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header


class Harness:
    def __init__(self,tables=None,mapping=None,*,flags=False):
        self.h=Pipeline(tables if tables is not None else [bytes([8]*256)]*2,
            mapping if mapping is not None else bytes(256),raw_attributes=True,decode_metadata=True,
            fast_mask_dispatch=True,selective_cache=True,constant_attribute_borders=True,
            skip_black_borders=True,skip_noop_runs=True,skip_static_stripes=True,
            unrolled_cache=True,attribute_groups=True,attribute_flags=flags)
        self.cpu=self.h.cpu; self.flags=flags

    def run(self,previous,current,masks,coded,literals,bitmap_bits,total_bits,raw,interrupt=None):
        cpu=self.cpu; cpu.guarding=False
        if len(masks)!=96 or len(previous)!=768 or len(current)!=768: raise ValueError('one frame required')
        payload=coded+literals+b'\0'
        for base,data in ((0x7000,previous),(ATTRS,masks),(INPUT,payload),
                (0xbfb0,np.packbits(np.frombuffer(masks,dtype=np.uint8)!=0).tobytes())):
            for i,v in enumerate(data): cpu.write8(base+i,v)
        cpu.input_end=INPUT+len(payload); cpu.port_7ffd=0x16
        word(cpu,self.h.recon['attribute_masks'],ATTRS)
        word(cpu,self.h.recon['literal_source'],INPUT+len(coded)+len(literals)-(768 if raw else 0))
        cpu.write8(self.h.recon['raw_attributes'],int(raw))
        cpu.ix=INPUT+bitmap_bits//8; cpu.alt_c=0xf0+(bitmap_bits&7)
        before=bytes(cpu.banks[5][:0x3000])+bytes(cpu.banks[5][0x3300:0x3800])
        result=self.h.execute(self.h.recon['attribute_pass'],interrupt)
        if bytes(cpu.banks[5][0x3000:0x3300])!=current:
            raise AssertionError('reconstructed attributes differ')
        if bytes(cpu.banks[5][:0x3000])+bytes(cpu.banks[5][0x3300:0x3800])!=before:
            raise AssertionError('bitmap/cache/native screen changed')
        if (cpu.ix-INPUT)*8+(cpu.alt_c&7)!=total_bits:
            raise AssertionError(('attribute coded cursor differs',cpu.ix,cpu.alt_c,total_bits))
        if word(cpu,self.h.recon['literal_source'])!=INPUT+len(coded)+len(literals):
            raise AssertionError('literal cursor differs')
        if word(cpu,self.h.recon['attribute_masks'])!=ATTRS+(0 if raw else 96):
            raise AssertionError('mask cursor differs')
        for base,data in ((ATTRS,masks),(INPUT,payload),*self.h.protected_regions):
            if bytes(cpu.read8(base+i) for i in range(len(data)))!=data:
                raise AssertionError(('input or immutable tables changed',base))
        return result['total_tstates']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); data=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(data); _,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    if len(states)!=count: raise ValueError('frame count differs')
    machines={name:Harness(tables,mapping,flags=flag) for name,flag in (('before',False),('after',True))}
    rows=[]; report=dict(scope=__doc__,complete=False,release=False,baseline_commit='6dbb142',
        raw_sha256=sha(data),states_sha256=sha(states.tobytes()),frames_expected=count,
        compressed_stream_delta_bytes=0,full_player_verified=False,nominal_deadlines_verified=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        delta_formula='raw=0; coded=-5551+530*nonempty_flags+50*nonempty_masks',variants={},frames=rows)
    for name,h in machines.items():
        report['variants'][name]=dict(reconstruction_bytes=len(h.h.recon_code),code_end=h.h.recon['end'],
            controller_end=h.h.recon.get('attribute_flag_end'),
            code_hex=h.h.recon_code.hex(),
            extra_code=[dict(base=base,code_hex=blob.hex()) for base,blob in h.h.protected_regions if base==machine.CODE],
            instructions=[v for v in h.h.instructions.values() if v['stage'] in ('attribute_pass','huffman')])
    def save():
        head=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
        args.output.write_text(head[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in rows)+'\n  ]\n}\n',encoding='utf-8')
    previous=bytes(768)
    try:
        for i,state in enumerate(states):
            _,d=read_packet(r,stored_guards=False); current=state[3072:].tobytes()
            fields=strip_attributes(d,previous,current,tables[-1])
            start=sum(map(len,d['ticks']))+5+195
            masks=restore(d['payload'][start:start+d['mask_bytes']],1,480,4)[384:]
            coded=d['payload'][d['coded_offset']:d['literal_offset']]; literals=d['payload'][d['literal_offset']:]
            bits=8*len(coded)-((8-(d['flags']&7))&7); raw=bool(d['flags']&64)
            row=dict(index=i,raw=raw,nonempty_flags=sum(any(masks[j:j+8]) for j in range(0,96,8)),
                nonempty_masks=sum(bool(x) for x in masks))
            for name,h in machines.items():
                row[name]=h.run(previous,current,masks,coded,literals,fields['bitmap_bits'],bits,raw)
            row['delta']=row['after']-row['before']
            if row['delta']!=machine.delta_tstates(masks,raw): raise AssertionError(('formula differs',row))
            rows.append(row); previous=current
            if i%500==0: save(); print(f'Attribute reconstruction verified {i+1}/{count}',flush=True)
        r.end()
        for name,h in machines.items():
            total=sum(row[name] for row in rows); stages=Counter()
            for (pc,t),n in h.h.histogram.items(): stages[h.h.instructions[pc]['stage']]+=t*n
            if total!=sum(stages.values()): raise AssertionError('histogram differs')
            report['variants'][name].update(tstates=total,stages=dict(stages),
                histogram=[dict(address=pc,tstates=t,count=n) for (pc,t),n in sorted(h.h.histogram.items())])
        before=report['variants']['before']['tstates']; after=report['variants']['after']['tstates']
        report.update(complete=True,checked_frames=len(rows),delta_tstates=after-before,change_percent=100*(after-before)/before,
            slower_frames=sum(v['delta']>0 for v in rows),max_extra_tstates=max(v['delta'] for v in rows),
            exact_all_attributes=True,other_frame_bytes_untouched=True)
    except Exception as exc:
        report['failure']=repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in report.items() if k not in ('variants','frames','scope')},indent=2),flush=True)


if __name__=='__main__': main()
