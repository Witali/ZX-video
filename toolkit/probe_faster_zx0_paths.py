"""Count boundary paths up to copying or the CALL into slice_yield.

Synchronization includes its RET. Boundary costs include EX AF restoration
and (when yielding) the CALL instruction, but exclude the yield body and
subsequent resume. These are CPU counts without IRQ or contention.
"""
import argparse
import json
from pathlib import Path
import struct

from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from benchmark_faster_zx0 import fixture
from build_fap3_trd import sha
from test_inplace_slot import block

ROOT=Path(__file__).parent


def measure():
    payload,raw=block(1);stream=struct.pack('<HH',len(raw),len(payload))+payload
    cases=(('lower_high_byte',0xc080,0xc100),('same_high_lower_low',0xc17f,0xc180),
           ('equal_target',0xc180,0xc180),('greater_low',0xc181,0xc180),('greater_high',0xc201,0xc180))
    results=[]
    for variant in ('baseline','turbo_tuned','fast'):
        h,_=fixture(stream,53,variant);c=h.cpu;z=h.z;rows=[]
        for name,output,target in cases:
            word(c,z['slice_target'],target)
            c.pc=z['slice_sync_target'];c.sp=STACK;c.push(STOP);before=c.tstates
            while c.pc!=STOP:c.step()
            sync=c.tstates-before
            sites=('match','slice') if variant!='fast' else ('match','match3','slice')
            for site in sites:
                c.set_de(output);c.set_bc(17);c.a=0xa5;c.carry=True;c.z=False;c.sp=STACK
                c.pc=z[site+'_copy' if variant=='baseline' else site+'_check']
                end=z[site+'_copy_fast' if variant=='baseline' else site+'_fast']+1
                before=c.tstates;steps=c.steps
                while c.pc not in (end,z['slice_yield']):
                    if c.steps-steps>40:raise AssertionError('boundary did not return or yield')
                    c.step()
                if c.a!=0xa5 or not c.carry or c.z or c.bc()!=17 or c.de()!=output:
                    raise AssertionError('boundary corrupts input registers/AF')
                rows.append(dict(case=name,site=site,sync_tstates=sync,boundary_tstates=c.tstates-before,
                                 yielded=c.pc==z['slice_yield']))
        results.append(dict(variant=variant,rows=rows))
    baseline={(r['case'],r['site']):r for r in results[0]['rows']}
    for variant in results[1:]:
        for row in variant['rows']:
            old=baseline[row['case'],'match' if row['site']=='match3' else row['site']]
            if row['yielded']!=old['yielded']:raise AssertionError('pause decision differs')
            row['sync_delta_tstates']=row['sync_tstates']-old['sync_tstates']
            row['boundary_delta_tstates']=row['boundary_tstates']-old['boundary_tstates']
    return dict(complete=True,release=False,scope=__doc__,variants=results,
        sources={n:sha((ROOT/n).read_bytes()) for n in ('probe_faster_zx0_paths.py','faster_zx0.py')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    path=ROOT/'faster_zx0_paths.json';r=measure()
    if a.check:
        if json.loads(path.read_bytes())!=r:raise ValueError('path timings changed')
    else:
        if path.exists():p.error('output exists; use --check')
        path.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({v['variant']:[(r['case'],r['sync_tstates'],r['boundary_tstates'])
        for r in v['rows'] if r['site']=='match'] for v in r['variants']}),flush=True)
