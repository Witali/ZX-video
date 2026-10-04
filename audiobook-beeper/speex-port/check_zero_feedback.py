"""Check both feedback paths against arbitrary history and an independent integer model."""
import argparse
import json
import random
import struct
from check_primitives import machine,symbols,call,timing
from verify import ROOT


def locations(m,s):
    if '_filter_feedback_start' in s:
        return s['_filter_feedback_start'],s['_filter_emit'],None
    # The previous block begins with the dead absolute store, then CALL split.
    code=bytes(m.memory[s['s__CODE']:s['s__CODE']+s['l__CODE']])
    needle=b'\xcd'+s['_split_nibbles'].to_bytes(2,'little')+b'\x3e\x72'
    assert code.count(needle)==1
    start=s['s__CODE']+code.index(needle)-3
    assert m.memory[start]==0x22
    dead=int.from_bytes(m.memory[start+1:start+3],'little')
    emit=b'\x3a'+(s['_last_pcm16']+1).to_bytes(2,'little')+b'\xee\x80\xd3\xfb'
    assert code.count(emit)==1
    return start,s['s__CODE']+code.index(emit),dead


def check(folder,histories,values,coefficients):
    m=machine(folder);s=symbols(folder);start,end,dead=locations(m,s)
    m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coefficients)
    call(m,s['_prepare_coefficients'],budget=1000000)
    m.set_breakpoint(end)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['_zx_memory'],40,m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    for i in range(4):m.unmark_addrs(s[f'_smc{i}'],1,m.WRITE_MARK)
    if dead is not None:m.unmark_addrs(dead,2,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('feedback write',hex(address),value))
    m.set_write_callback(bad)
    costs={};audits={}
    for i,n in enumerate(values):
        history=histories[i%len(histories)]
        before=list(struct.unpack('<10I',history))
        m.memory[s['_zx_memory']:s['_zx_memory']+40]=history
        m.hl=n&65535;m.a=m.hl>>8;m.ix=0x1234;m.iy=0x5678;m.sp=0xbffe
        m.pc=start;m.ticks_to_stop=10000
        while m.pc!=end:assert not(m.run()&m._TICKS_LIMIT_HIT)
        elapsed=10000-m.ticks_to_stop
        kind='zero' if n==0 else 'nonzero'
        if kind in costs:assert costs[kind]==elapsed
        costs[kind]=elapsed
        expected=[(n*c+(before[k+1] if k<9 else 0))&0xffffffff for k,c in enumerate(coefficients)]
        assert bytes(m.memory[s['_zx_memory']:s['_zx_memory']+40])==struct.pack('<10I',*expected)
        assert (m.ix,m.iy,m.sp)==(0x1234,0x5678,0xbffe)
        if kind not in audits:
            m.hl=n&65535;m.a=m.hl>>8;m.pc=start;total=0;instructions=0
            while m.pc!=end:
                want=timing(m);tick=m.frame_tick;m.ticks_to_stop=1;m.run()
                actual=(m.frame_tick-tick)%100000;assert actual==want
                total+=actual;instructions+=1
            assert total==elapsed
            audits[kind]=dict(tstates=total,instructions=instructions,every_instruction_matches=True)
    return dict(cases=len(values),costs=costs,audits=audits,writes_guarded=True,sp_ix_iy_preserved=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',default='pure-r22');p.add_argument('--previous',default='pure-r20')
    a=p.parse_args();out=ROOT/'build/speex-port';rng=random.Random(2204)
    histories=[bytes(40),bytes([255])*40,bytes(range(40)),bytes([128,0,255,127])*10]
    histories += [rng.getrandbits(320).to_bytes(40,'little') for _ in range(512)]
    values=[0]*len(histories)+[-32768,-32767,-257,-1,1,127,128,255,256,32767]
    values += [rng.choice((-1,1))*rng.randrange(1,32768) for _ in range(1024)]
    coeffs=[[0]*10,[-32768,-32767,-8192,-257,-1,1,255,8192,32766,32767],
            [rng.randrange(-32768,32768) for _ in range(10)]]
    old=[check(out/a.previous,histories,values,c) for c in coeffs]
    new=[check(out/a.variant,histories,values,c) for c in coeffs]
    assert all(x['costs']==dict(zero=4138,nonzero=4138) for x in old)
    assert all(x['costs']==dict(zero=847,nonzero=4136) for x in new)
    r=dict(previous=a.previous,variant=a.variant,previous_checks=old,selected_checks=new,
           cases_per_variant=len(values)*len(coeffs),zero_cases_per_variant=len(histories)*len(coeffs),
           independent_signed_product_and_modulo32_history_model=True,
           zero_path_delta_tstates=-3291,nonzero_path_delta_tstates=-2)
    (out/a.variant/'zero-feedback-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r,flush=True)


if __name__=='__main__':main()
