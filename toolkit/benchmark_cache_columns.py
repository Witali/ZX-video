"""Execute rolling-cache fills on Z80 for all movie maps.

Checks every written and untouched byte after each of the twelve prefetches.
Host supplies the map and preceding compact frame. No packet parsing, ZX0,
motion reconstruction, screen output, IRQ/ULA or disk cost is included.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from benchmark_compact_screen import NativeCPU, STACK, STOP
from benchmark_context_huffman import word
from bulk_frame_stream import read_packet
import causal_tile_z80 as machine
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from probe_sparse_motion_cache import coverage
from validate_fast_sparse import CPU


def copy_tstates(groups, columns=32, unrolled=False):
    """Instruction-table sum for calls [12]+[8]*10+[4], excluding CALL.

    Old: 3795 + 2305*N. Two pairs change 2318 to 2240 T
    per called rows helper (-78). Pair decoding has six refills vs three:
    baseline +24*37+3*65; selected pair adds 1437/1377/2316 for R/L/both.
    Frame setup and zero-border calls are unchanged.
    """
    values=np.asarray(groups,dtype=np.uint8).reshape(24,32//columns)
    if columns==32: return 3795+(2227 if unrolled else 2305)*int(values.sum())
    if columns!=16 or unrolled: raise ValueError('unsupported variant')
    counts=np.bincount(values[:,0]*2+values[:,1],minlength=4)
    return 4878+1437*int(counts[1])+1377*int(counts[2])+2316*int(counts[3])


class CacheCPU(NativeCPU):
    def write8(self,address,value):
        if self.guarding and not (machine.CACHE<=address<machine.CACHE+1024
                or self.state[0]<=address<self.state[1] or STACK-96<=address<STACK):
            raise AssertionError(f'cache write outside contract: {address:04x}')
        CPU.write8(self,address,value)


class Harness:
    def __init__(self,columns=32,unrolled=False,*,tables=None,mapping=None):
        self.columns,self.unrolled=columns,unrolled
        self.code,self.labels,self.listing,_=machine.build(tables if tables is not None else [bytes([8]*256)]*2,
            mapping if mapping is not None else bytes(256),OFFSETS,
            hybrid=True,skip_empty=True,intra_above=True,intra_extended=True,
            fast_fragments=True,unrolled_motion=True,split_literals=True,raw_attributes=True,
            selective_cache=True,skip_noop_runs=True,skip_static_stripes=True,
            cache_columns=columns,unrolled_cache=unrolled)
        if self.labels['end']>0x9000: raise AssertionError('native renderer overlap')
        self.instructions={v['address']:v for v in self.listing}
        self.cpu=CacheCPU(b'',b''); self.cpu.state=(self.labels['state'],self.labels['end'])
        for i,v in enumerate(self.code): self.cpu.write8(machine.CODE+i,v)
        self.histogram=Counter()

    def run(self,groups,source):
        groups=np.asarray(groups,dtype=np.uint8).reshape(24,32//self.columns)
        if len(source)!=3072 or not np.isin(groups,[0,1]).all(): raise ValueError('invalid source/map')
        packed=np.packbits(groups).tobytes(); cpu=self.cpu; cpu.guarding=False
        for i,v in enumerate(source): cpu.write8(machine.FRAME+i,v)
        for i in range(1024): cpu.write8(machine.CACHE+i,0xa5)
        for i,v in enumerate(packed): cpu.write8(machine.CACHE_MAP+i,v)
        word(cpu,self.labels['cache_mask_source'],machine.CACHE_MAP)
        cpu.write8(self.labels['cache_mask_shift'],128)
        cpu.set_hl(machine.FRAME); cpu.set_de(machine.CACHE+1)
        expected=bytearray(b'\xa5'*1024); first=total=0
        for rows in [12]+[8]*10+[4]:
            cpu.guarding=False; cpu.b,cpu.c=rows,0x35
            cpu.pc,cpu.sp=self.labels['cache_copy'],STACK; cpu.push(STOP); cpu.guarding=True
            start=cpu.tstates
            while cpu.pc!=STOP:
                pc,before=cpu.pc,cpu.tstates; cpu.step(); elapsed=cpu.tstates-before
                ticks=self.instructions[pc]['tstates']
                if elapsed not in (ticks if isinstance(ticks,list) else [ticks]):
                    raise AssertionError(('instruction timing',self.instructions[pc],elapsed))
                self.histogram[pc,elapsed]+=1
            total+=cpu.tstates-start
            for group in range(first,first+rows//4):
                for part,enabled in enumerate(groups[group]):
                    if enabled:
                        for y in range(group*4,group*4+4):
                            x=part*self.columns; target=(y%16)*64+1+x
                            expected[target:target+self.columns]=source[y*32+x:y*32+x+self.columns]
            first+=rows//4
            if cpu.hl()!=machine.FRAME+first*128 or cpu.de()!=machine.CACHE+(first%4)*256+1:
                raise AssertionError(('cache cursor',first,cpu.hl(),cpu.de()))
            if cpu.bc()!=0x35 or cpu.sp!=STACK: raise AssertionError('register/stack differs')
            if bytes(cpu.read8(machine.CACHE+i) for i in range(1024))!=expected:
                raise AssertionError(('cache RAM differs',first))
        if word(cpu,self.labels['cache_mask_source'])!=machine.CACHE_MAP+len(packed) or cpu.read8(self.labels['cache_mask_shift'])!=128:
            raise AssertionError('map cursor differs')
        if total!=copy_tstates(groups,self.columns,self.unrolled):
            raise AssertionError(('cycle formula differs',total,copy_tstates(groups,self.columns,self.unrolled)))
        return total


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    r=Reader(raw); _,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    if len(states)!=count: raise ValueError('frame count differs')
    machines={'halves':Harness(16,tables=tables,mapping=mapping),'unrolled':Harness(32,True,tables=tables,mapping=mapping)}
    result=dict(scope=__doc__,complete=False,release=False,frames_expected=count,
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),baseline_commit='4b62e52',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_player_verified=False,nominal_deadlines_verified=False,disk_delivery_verified=False,
        variants={k:dict(columns=h.columns,unrolled=h.unrolled,code_bytes=len(h.code),
            code_end=h.labels['end'],free_before_renderer=0x9000-h.labels['end'],
            map_bytes=96//h.columns,code_hex=h.code.hex(),
            copy_instructions=[v for v in h.listing if h.labels['cache_copy']<=v['address']<h.labels['cache_zero']])
            for k,h in machines.items()},frames=[])
    def save():
        prefix=json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2)
        args.output.write_text(prefix[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in result['frames'])+'\n  ]\n}\n',encoding='utf-8')
    previous=bytes(3840)
    try:
        for i,state in enumerate(states):
            _,packet=read_packet(r,stored_guards=False); start=sum(map(len,packet['ticks']))+5
            vectors=packet['payload'][start+3:start+195]
            fine=coverage(vectors,8).reshape(24,4,4).any(axis=1)
            whole=fine.any(axis=1)
            if np.packbits(whole).tobytes()!=packet['cache']: raise AssertionError('old map mismatch')
            enabled=bool(packet['flags'] & 128)
            if enabled!=bool(whole.any()): raise AssertionError('cache-enable mismatch')
            row=dict(index=i,enabled=enabled,baseline=copy_tstates(whole) if enabled else 0)
            for name,h in machines.items():
                groups=fine.reshape(24,32//h.columns,h.columns//8).any(axis=2)
                row[name]=h.run(groups,previous[:3072]) if enabled else 0
            result['frames'].append(row); previous=state.tobytes()
            if i%200==0: save(); print(f'Cache Z80 verified {i+1}/{count}',flush=True)
        r.end(); baseline=sum(v['baseline'] for v in result['frames'])
        for name,h in machines.items():
            total=sum(v[name] for v in result['frames'])
            if total!=sum(n*t for (_,t),n in h.histogram.items()): raise AssertionError('histogram differs')
            result['variants'][name].update(tstates=total,delta_tstates=total-baseline,
                change_percent=100*(total-baseline)/baseline,
                histogram=[dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())])
        result.update(complete=True,baseline_tstates=baseline,checked_frames=count,
            enabled_frames=sum(v['enabled'] for v in result['frames']))
    except Exception as exc:
        result['failure']=repr(exc); save(); raise
    save(); print(json.dumps({name:{k:v for k,v in item.items() if k in ('tstates','delta_tstates','change_percent','code_bytes','free_before_renderer')}
        for name,item in result['variants'].items()},indent=2),flush=True)


if __name__=='__main__': main()
