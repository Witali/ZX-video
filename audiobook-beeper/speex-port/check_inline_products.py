"""Verify inline feedback, stack borrowing and complete filter register contracts."""
import json
import random
import struct
from check_primitives import machine,symbols,call,timing
from verify import ROOT


def step(m):
    pc=m.pc;want=timing(m);tick=m.frame_tick
    m.ticks_to_stop=5 if m.memory[pc] in (0xdd,0xfd) else 1
    m.run();actual=(m.frame_tick-tick)%100000
    if m.memory[pc] in (0xdd,0xfd) and actual==4 and m.pc==(pc+1)&65535:
        tick=m.frame_tick;m.ticks_to_stop=1;m.run()
        actual+=(m.frame_tick-tick)%100000
    assert actual==want,(hex(pc),actual,want)
    return actual


def guarded(folder,inline):
    m=machine(folder);s=symbols(folder)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    m.unmark_addrs(0x7200,2560,m.WRITE_MARK)
    if not inline:
        for i in range(4):m.unmark_addrs(s[f'_smc{i}'],1,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('filter write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad)
    return m,s


def feedback(folder,inline,values,histories,coefficients):
    m,s=guarded(folder,inline)
    m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coefficients)
    call(m,s['_prepare_coefficients'],budget=1000000)
    # The feedback block must write only the forty history bytes and, for the
    # baseline helper calls, the real stack/declared immediate operands.
    m.mark_addrs(0x7200,2560,m.WRITE_MARK)
    m.mark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    m.unmark_addrs(s['_zx_memory'],40,m.WRITE_MARK)
    m.set_breakpoint(s['_filter_emit']);costs={};audits={}
    for i,n in enumerate(values):
        history=histories[i%len(histories)]
        m.memory[s['_zx_memory']:s['_zx_memory']+40]=struct.pack('<10I',*history)
        m.hl=n&65535;m.a=m.hl>>8;m.sp=0xbffe;m.ix=0x1234;m.iy=0x5678;m.alt_hl=0xcafe
        if '_filter_saved_sp' in s:
            m.memory[s['_filter_saved_sp']:s['_filter_saved_sp']+2]=m.sp.to_bytes(2,'little')
        m.pc=s['_filter_feedback_start'];m.ticks_to_stop=10000
        while m.pc!=s['_filter_emit']:assert not(m.run()&m._TICKS_LIMIT_HIT)
        elapsed=10000-m.ticks_to_stop;kind='zero' if n==0 else 'nonzero'
        if kind in costs:assert costs[kind]==elapsed
        costs[kind]=elapsed
        want=[(n*c+(history[k+1] if k<9 else 0))&0xffffffff for k,c in enumerate(coefficients)]
        assert bytes(m.memory[s['_zx_memory']:s['_zx_memory']+40])==struct.pack('<10I',*want)
        assert (m.sp,m.alt_hl)==(0xbffe,0xcafe)
        if not inline or n==0:assert (m.ix,m.iy)==(0x1234,0x5678)
        if kind not in audits:
            m.hl=n&65535;m.a=m.hl>>8;m.pc=s['_filter_feedback_start'];total=0;instructions=0;borrowed=0
            while m.pc!=s['_filter_emit']:
                if 0x7200<=m.sp<0x7c00:borrowed+=1
                total+=step(m);instructions+=1
            assert total==elapsed and m.sp==0xbffe
            audits[kind]=dict(tstates=total,instructions=instructions,instructions_with_table_sp=borrowed,
                              every_instruction_matches=True)
    return dict(cases=len(values),costs=costs,audits=audits,arbitrary_history_exact=True,
                real_sp_and_alternate_cursor_preserved=True,writes_guarded=True)


def filter_calls(folder,inline):
    m,s=guarded(folder,inline);rng=random.Random(2304);samples=0;calls=0
    for case in range(128):
        coeffs=[0]*10 if case==0 else [rng.randrange(-32768,32768) for _ in range(10)]
        history=[0]*10 if case<2 else [rng.getrandbits(32) for _ in range(10)]
        excitation=[0]*40 if case==0 else [rng.randrange(-32768,32768) for _ in range(40)]
        m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coeffs)
        m.memory[s['_zx_memory']:s['_zx_memory']+40]=struct.pack('<10I',*history)
        m.memory[0xc000:0xc050]=struct.pack('<40h',*excitation)
        want=[]
        for x in excitation:
            rounded=(history[0]+4096)&0xffffffff
            if rounded&0x80000000:rounded-=1<<32
            y=max(-32767,min(32767,x+(rounded>>13)))
            want.append(y)
            history=[(-y*c+(history[k+1] if k<9 else 0))&0xffffffff for k,c in enumerate(coeffs)]
        seen=[]
        def output(port,value):
            assert port&255==0xfb
            y=int.from_bytes(m.memory[s['_last_pcm16']:s['_last_pcm16']+2],'little',signed=True)
            assert value==(y>>8)+128;seen.append(y)
        m.set_output_callback(output);m.ix=0x1234;m.iy=0x5678
        call(m,s['_zx_speex_filter'],hl=0xc000,budget=1000000)
        assert (m.sp,m.ix,m.iy)==(0xbffe,0x1234,0x5678)
        assert seen==want,(case,seen,want)
        assert bytes(m.memory[s['_zx_memory']:s['_zx_memory']+40])==struct.pack('<10I',*history)
        if inline:assert m.alt_hl==0xc050
        calls+=1;samples+=len(seen)
    return dict(calls=calls,samples=samples,every_pcm16_and_pcm8_exact=True,
                final_history_exact=True,sp_ix_iy_preserved=True,writes_guarded=True,
                all_code_immutable=inline)


def main():
    out=ROOT/'build/speex-port';rng=random.Random(2323)
    histories=[[0]*10,[0xffffffff]*10,[0x80000000,0x7fffffff]*5]
    histories += [[rng.getrandbits(32) for _ in range(10)] for _ in range(512)]
    values=[0]*len(histories)+[-32768,-32767,-257,-1,1,127,128,255,256,32767]
    values += [rng.choice((-1,1))*rng.randrange(1,32768) for _ in range(2048)]
    coeffs=[[0]*10,[-32768,-32767,-8192,-257,-1,1,255,8192,32766,32767],
            [rng.randrange(-32768,32768) for _ in range(10)]]
    expected={'pure-r22':4136,'pure-r23':3723,'pure-r23-pop':3603};results={}
    for variant,cost in expected.items():
        checks=[feedback(out/variant,variant!='pure-r22',values,histories,c) for c in coeffs]
        assert all(c['costs']==dict(zero=847,nonzero=cost) for c in checks)
        results[variant]=dict(feedback=checks,feedback_cases=len(values)*len(coeffs),
                              filter_contract=filter_calls(out/variant,variant!='pure-r22'))
    r=dict(variants=results,baseline='pure-r22',full_speech_samples=186880,zero_feedback_samples=3340,
           ordinary_path_saving=dict(registers=413,table_pop=533),
           input_fetch_saving_per_sample=3,function_overhead_delta=dict(registers=33,table_pop=53),
           predicted_full_saving=dict(registers=183540*413+186880*3-4672*33,
                                      table_pop=183540*533+186880*3-4672*53))
    (out/'pure-r23-pop/inline-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items() if k!='variants'},flush=True)
    for variant,result in results.items():
        print(variant,result['feedback_cases'],result['feedback'][0]['costs'],result['filter_contract'],flush=True)


if __name__=='__main__':main()
