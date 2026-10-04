"""Verify a cumulative optimization against saved independent reference streams."""
import argparse
import json
from pathlib import Path
import random
import struct
from check_primitives import audit,call,machine,symbols,primitives
from make_decoder import array
from verify import native,ROOT


def specialized(folder):
    s=symbols(folder);m=machine(folder);rng=random.Random(711)
    pairs=[(a,b) for a in range(-128,128) for b in (-32768,-32767,-256,-1,0,1,255,32767)]
    pairs += [(rng.randrange(-128,128),rng.randrange(-32768,32768)) for _ in range(10000)]
    costs=[]
    for a,b in pairs:
        costs.append(call(m,s['_mul_s8'],a=a&255,de=b&65535))
        assert (m.hl<<16|m.de)==(a*b)&0xffffffff,(a,b,m.hl,m.de)
    def q(a,b,k):return a*(b>>k)+((a*(b&((1<<k)-1)))>>k)
    energy=[q(a,q(28406,g,15),14) for g in array('ol_gain_table') for a in (11546,17224)]
    count=0
    for e in energy:
        for x in sorted(set(array('exc_10_32_table'))):
            m.memory[0x7e00:0x7e04]=struct.pack('<i',e)
            call(m,s['mulq12'],a=x&255,de=0x7e00)
            assert (m.hl<<16|m.de)==q(x*4,e,14)&0xffffffff,(x,e,m.hl,m.de)
            count+=1
    table_entries=0
    if '_build_innovation' in s:
        for e in energy:
            m.memory[0x7b00:0x7b04]=struct.pack('<i',e)
            call(m,s['_build_innovation'],hl=0x7c00,de=0x7b00)
            for i in range(132):
                value=int.from_bytes(m.memory[0x7c00+3*i:0x7c03+3*i],'little',signed=True)
                assert value==q((i-65)*4,e,14),(i,e,value)
                table_entries+=1
    return dict(signed8x16_cases=len(pairs),min_mul_t=min(costs),max_mul_t=max(costs),energy_shape_pairs=count,innovation_table_entries=table_entries)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',required=True);p.add_argument('--output',type=Path,default=ROOT/'build/speex-port')
    p.add_argument('--skip-speech',action='store_true');a=p.parse_args();out=a.output;folder=out/a.variant
    result=dict(specialized=specialized(folder))
    result['audit']=audit(folder,(out/'input.spxraw').read_bytes(),(out/'reference.pcm16').read_bytes())
    if not a.skip_speech:native(out,a.variant)
    fixtures={}
    for name in ('silence','impulses','low-tone','high-tone','noise','level-jumps','six-bank-capacity'):
        r=native(out/'checks'/name,a.variant,folder)
        fixtures[name]={k:v for k,v in r.items() if k!='out_intervals_histogram'}
    result['fixtures']=fixtures
    (folder/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(a.variant,result['specialized'],result['audit'],flush=True)


if __name__=='__main__':main()
