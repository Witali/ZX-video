"""Measure group preparation and native attribute writes for every frame.

Host supplies final compact attributes, original raw flag and expanded mask
flags. Real Z80 builds both lists and updates alternating native attributes.
Bitmap reconstruction/output, metadata decoding, ZX0, IRQ/ULA/disk and
publication are excluded. New stage includes the added outer 17-T CALL.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import attribute_groups_z80 as machine
from benchmark_compact_screen import STACK,STOP
from bulk_frame_stream import read_packet
from frame_output_pipeline import Harness as Pipeline
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header


class Harness:
    def __init__(self,tables=None,mapping=None):
        self.h=Pipeline(tables if tables is not None else [bytes([8]*256)]*2,
            mapping if mapping is not None else bytes(256),raw_attributes=True,decode_metadata=True,
            fast_mask_dispatch=True,selective_cache=True,constant_attribute_borders=True,skip_black_borders=True,
            skip_noop_runs=True,skip_static_stripes=True,attribute_groups=True)
        self.cpu=self.h.cpu; self.histogram=Counter(); self.expected={5:b'\1'*768,7:b'\1'*768}
        self.expected_lists=[[],[]]

    def execute(self,entry,stop=STOP):
        cpu=self.cpu; cpu.guarding=False; cpu.pc,cpu.sp=entry,STACK
        if stop==STOP: cpu.push(STOP)
        cpu.guarding=True; start=cpu.tstates; irq=0
        while cpu.pc!=stop:
            pc,before=cpu.pc,cpu.tstates; row=self.h.instructions[pc]; cpu.phase=row['phase']; cpu.step()
            actual=cpu.tstates-before; want=row['tstates']
            if actual not in (want if isinstance(want,list) else [want]): raise AssertionError(('cycles',row,actual))
            self.histogram[pc,actual]+=1
            if getattr(self,'interrupt',None) and cpu.pc!=stop: irq+=self.interrupt(cpu)
        if cpu.sp!=STACK: raise AssertionError('unbalanced stack')
        return cpu.tstates-start-irq

    def run(self,attrs,masks,raw,index):
        if len(attrs)!=768 or len(masks)!=96 or attrs[:96]!=b'\1'*96 or attrs[672:]!=b'\1'*96:
            raise ValueError('invalid attributes/borders')
        if index>=2 and not raw and (any(masks[:12]) or any(masks[84:])):
            raise ValueError('nonzero outside masks')
        if raw and any(masks): raise ValueError('raw attribute masks must be zero')
        flags=np.packbits(np.frombuffer(masks,dtype=np.uint8)!=0).tobytes()
        cpu=self.cpu; cpu.guarding=False; target=7 if index%2==0 else 5
        cpu.target_bank=target; cpu.port_7ffd=0x17 if target==7 else 0x1f
        for i,v in enumerate(attrs): cpu.write8(0x7000+i,v)
        for i,v in enumerate(flags): cpu.write8(0xbfb0+i,v)
        cpu.write8(self.h.recon['raw_attributes'],int(raw))
        prepare=self.execute(machine.CODE)
        if prepare!=machine.prepare_tstates(flags[1:11],raw=raw,warmup=index<2): raise AssertionError('prepare formula')
        self.expected_lists[index%2]=list(range(12,84)) if raw or index<2 else [i for i in range(12,84) if masks[i]]
        for base,wanted in zip(machine.LISTS,self.expected_lists):
            # 72 is also the full-copy marker; its indices are intentionally unused.
            count=len(wanted); expected=bytes([count]) if count==72 else bytes([count]+wanted)
            if bytes(cpu.read8(base+i) for i in range(len(expected)))!=expected:
                raise AssertionError(('group list differs',index,base))
        cpu.guarding=False; cpu.write8(self.h.draw['screen_base'],0xc0 if target==7 else 0x40)
        draw=self.execute(self.h.draw['attributes'],self.h.draw['attribute_end'])
        counts=list(map(len,self.expected_lists))
        if draw!=machine.draw_tstates(counts): raise AssertionError(('draw formula',draw,counts))
        self.expected[target]=attrs
        for bank,expected in self.expected.items():
            if bytes(cpu.banks[bank][6144:6912])!=expected or any(cpu.banks[bank][:6144]):
                raise AssertionError(('native attributes/bitmap differ',index,bank))
        return dict(index=index,raw=raw,group_counts=counts,prepare_tstates=prepare,
            draw_tstates=draw,added_call_tstates=17,total_tstates=prepare+draw+17,
            baseline_tstates=9778,delta_tstates=prepare+draw+17-9778)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(raw); _,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    if len(states)!=count: raise ValueError('frame counts differ')
    h=Harness(tables,mapping); rows=[]
    report=dict(scope=__doc__,complete=False,release=False,raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        baseline_commit='a4a3f82',frames_expected=count,compressed_stream_delta_bytes=0,
        helper_code_hex=h.h.group_code.hex(),helper_labels=h.h.group_labels,renderer_code_hex=h.h.draw_code.hex(),
        renderer_labels=h.h.draw,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        instruction_listing=[v for v in h.h.instructions.values() if v['phase']=='attribute_groups'
            or v['phase']=='output' and v['stage']=='attributes'],
        memory=dict(lists=machine.LISTS,list_bytes=machine.LIST_BYTES,helper=[machine.CODE,h.h.group_labels['end']],
            stack_reserved=[STACK-96,STACK],extra_screen_or_disk_bytes=0),frames=rows)
    def save():
        prefix=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
        args.output.write_text(prefix[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in rows)+'\n  ]\n}\n',encoding='utf-8')
    try:
        for i,state in enumerate(states):
            _,d=read_packet(r,stored_guards=False); start=sum(map(len,d['ticks']))+5+195
            masks=restore(d['payload'][start:start+d['mask_bytes']],1,480,4)[384:]
            rows.append(h.run(state[3072:].tobytes(),masks,bool(d['flags']&64),i))
            if i%500==0: save(); print(f'Attribute Z80 verified {i+1}/{count}',flush=True)
        r.end()
        report['histogram']=[dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())]
        total=sum(v['total_tstates'] for v in rows); baseline=9778*count
        if sum(t*n for (_,t),n in h.histogram.items())+17*count!=total: raise AssertionError('histogram differs')
        report.update(complete=True,frames_verified=len(rows),summary=dict(tstates=total,baseline_tstates=baseline,
            delta_tstates=total-baseline,change_percent=100*(total-baseline)/baseline,
            prepare_tstates=sum(v['prepare_tstates'] for v in rows),draw_tstates=sum(v['draw_tstates'] for v in rows),
            slower_frames=sum(v['delta_tstates']>0 for v in rows),max_extra_tstates=max(v['delta_tstates'] for v in rows)))
    except Exception as exc: report['failure']=repr(exc); save(); raise
    save(); print(json.dumps(report['summary'],indent=2),flush=True)


if __name__=='__main__': main()
