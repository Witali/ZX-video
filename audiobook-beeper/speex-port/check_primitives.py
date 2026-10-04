"""Exhaustive LUT/cosine checks and instruction-table timing audit on the Z80."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import struct
import sys
from z80 import Z80Machine
from verify import image
from make_decoder import cos_int

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'toolkit'))
from benchmark_z80_c_compilers import timing as base_timing

def symbols(folder):
    return {name:int(addr,16) for addr,name in re.findall(r'([0-9A-F]{8})\s+(\w+)\s',(folder/'player.map').read_text())}

def timing(m):
    op,sub=m.memory[m.pc:m.pc+2]
    if op in (0xf3,0xfb):return 4
    if op==0xd3:return 11
    if op==0xed and sub&0xc7==0x41:return 12
    return base_timing(m)

def machine(folder):
    m=Z80Machine();m.memory[:]=bytes(65536)
    for a,v in image(folder/'player.ihx').items():m.memory[a]=v
    m.set_breakpoint(0x7f00)
    return m

def call(m,address,budget=100000,**regs):
    for k,v in regs.items():setattr(m,k,v)
    m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=address;m.ticks_to_stop=budget
    while m.pc!=0x7f00:
        e=m.run();assert not(e&m._TICKS_LIMIT_HIT),'primitive timeout'
    return budget-m.ticks_to_stop

def primitives(folder):
    s=symbols(folder);m=machine(folder);eight=Counter();sixteen=Counter()
    for a in range(256):
        for b in range(256):
            cost=call(m,s['_zx_mul8'],a=a,c=b)
            assert m.hl==a*b,(a,b,m.hl)
            eight[cost]+=1
    values=[-32768,-32767,-16384,-8192,-257,-256,-255,-1,0,1,15,16,127,128,255,256,257,8192,16384,32767]
    rng=random.Random(711)
    pairs=[(a,b) for a in values for b in values]+[(rng.randrange(-32768,32768),rng.randrange(-32768,32768)) for _ in range(10000)]
    for a,b in pairs:
        cost=call(m,s['_zx_mul_table'],hl=a&65535,de=b&65535)
        assert (m.hl<<16|m.de)==(a*b)&0xffffffff,(a,b,m.hl,m.de)
        sixteen[cost]+=1
    cos_cost=Counter()
    for x in range(25737):
        cost=call(m,s['cosine'],hl=x)
        want=cos_int(x) if x<12868 else -cos_int(25736-x)
        assert m.de==want&65535,(x,m.de,want)
        cos_cost[cost]+=1
    for i in range(3000):
        a=rng.randrange(-32768,32768);b=rng.randrange(-250000000,250000000)
        m.memory[0x7e00:0x7e04]=struct.pack('<i',b)
        call(m,s['mulq14'],hl=a&65535,de=0x7e00)
        # Match Speex's intentional signed16 truncation of the high part.
        high=(b>>14)&65535;high=high-65536 if high&32768 else high
        want=(a*high+((a*(b&16383))>>14))&0xffffffff
        assert (m.hl<<16|m.de)==want,(a,b,m.hl,m.de,want)
    for x in [-2147483648,-1000000,-32769,-32768,-32767,-1,0,1,32767,32768,1000000,2147483647]:
        call(m,s['_zx_clip'],hl=(x>>16)&65535,de=x&65535)
        assert m.de==max(-32767,min(32767,x))&65535
    return dict(unsigned8_pairs=65536,signed16_pairs=len(pairs),cosine_angles=25737,q14_cases=3000,clip_edges=12,
                multiply8_tstates=dict(sorted(eight.items())),multiply16_tstates=dict(sorted(sixteen.items())),
                cosine_tstates=dict(sorted(cos_cost.items())))

def audit(folder,payload,reference,frames=1):
    s=symbols(folder);m=machine(folder);m.clear_breakpoint(0x7f00)
    assert 1<=frames<=819
    m.memory[s['_packet_count']:s['_packet_count']+2]=frames.to_bytes(2,'little')
    m.set_memory_block(0xc000,payload[:20*frames]+bytes(16384-20*frames))
    seen=[];counts=Counter();total=0
    def output(port,value):
        if port==0x7ffd:assert value==16
        else:assert port&255==0xfb;seen.append(value)
    m.set_output_callback(output);m.pc=s['_entry'];m.sp=0xbffe
    while m.pc!=s['_complete']:
        pc=m.pc;before=m.frame_tick;expected=timing(m);op=bytes(m.memory[pc:pc+2]).hex()
        m.ticks_to_stop=5 if m.memory[pc] in (0xdd,0xfd) else 1
        m.run();actual=(m.frame_tick-before)%100000
        # The emulator can yield at a frame boundary between an index prefix
        # and its opcode. Finish that same instruction before auditing it.
        if m.memory[pc] in (0xdd,0xfd) and actual==4 and m.pc==(pc+1)&65535:
            before=m.frame_tick;m.ticks_to_stop=1;m.run()
            actual+=(m.frame_tick-before)%100000
        assert actual==expected,(hex(pc),op,actual,expected)
        total+=actual;counts[str(expected)]+=1
    assert seen==[(x>>8)+128 for x in struct.unpack('<'+'h'*(160*frames),reference[:320*frames])]
    return dict(scope=f'{frames} complete frame(s), including startup, packet parsing, LPC and port output',
                tstates=total,instructions=sum(counts.values()),instruction_tstate_histogram=dict(sorted(counts.items(),key=lambda x:int(x[0]))),
                every_instruction_matches_zilog_table=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/speex-port');a=p.parse_args()
    result={}
    for variant in ('pure-asm','pure-fast'):
        folder=a.output/variant
        result[variant]=dict(primitives=primitives(folder),audit=audit(folder,(a.output/'input.spxraw').read_bytes(),(a.output/'reference.pcm16').read_bytes()))
        print(variant,result[variant]['audit'],flush=True)
    (a.output/'primitives.json').write_text(json.dumps(result,indent=2)+'\n')
