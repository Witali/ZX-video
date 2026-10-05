"""Check modulo24 pitch accumulation, guarded writeback and exact block timing."""
import json
import random
from check_primitives import machine,symbols,timing
from verify import ROOT


def run(m,start,end):
    m.pc=start;m.ticks_to_stop=1000
    # The flush entry shares the preceding add block's endpoint breakpoint.
    # Resume that entry once instead of repeatedly stopping without executing.
    m.step_over_breakpoint()
    while m.pc!=end:
        before=m.ticks_to_stop;event=m.run()
        assert not(event&m._TICKS_LIMIT_HIT)
        assert m.pc==end or m.ticks_to_stop<before,('unexpected breakpoint',hex(m.pc))
    return 1000-m.ticks_to_stop


def audit(m,start,end):
    m.pc=start;total=0;instructions=0
    # Do not use step_over_breakpoint here: it executes the first instruction
    # immediately, outside the audit's counters. Temporarily clear the entry.
    m.clear_breakpoint(start)
    while m.pc!=end:
        want=timing(m);tick=m.frame_tick;m.ticks_to_stop=1;m.run()
        got=(m.frame_tick-tick)%100000;assert got==want
        total+=got;instructions+=1
    m.set_breakpoint(start)
    return dict(tstates=total,instructions=instructions,every_instruction_matches=True)


def main():
    folder=ROOT/'build/speex-port/pure-r26';m=machine(folder);s=symbols(folder);rng=random.Random(2626)
    for key in ('init','flush','add_0','add_1','add_2'):m.set_breakpoint(s[f'_pitch_{key}_end'])
    m.mark_addrs(0,65536,m.WRITE_MARK);m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('pitch-sum write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad);m.sp=0xbffe
    m.alt_hl=0xffff;m.alt_c=0xff
    assert run(m,s['_pitch_init_start'],s['_pitch_init_end'])==25
    assert (m.alt_hl,m.alt_c,m.sp)==(0,0,0xbffe)
    initial=audit(m,s['_pitch_init_start'],s['_pitch_init_end'])
    assert initial['tstates']==25
    edges=[0,1,127,128,255,256,32767,32768,65535,65536,0x7fffff,0x800000,0xffffff]
    pairs=[(a,b) for a in edges for b in edges]
    pairs += [((((low*31>>8)&255)<<16)|low,((low>>8)^255)<<16|((low*257+17)&65535)) for low in range(65536)]
    pairs += [(rng.randrange(1<<24),rng.randrange(1<<24)) for _ in range(1024)]
    additions=[]
    for tap in range(3):
        for old,product in pairs:
            m.hl=(product>>16)|(0xff00 if product&0x800000 else 0);m.de=product&65535
            m.alt_hl=old&65535;m.alt_c=old>>16
            assert run(m,s[f'_pitch_add_{tap}_start'],s[f'_pitch_add_{tap}_end'])==52
            assert (m.alt_c<<16|m.alt_hl)==(old+product)&0xffffff,(tap,old,product)
            assert m.sp==0xbffe
        additions.append(audit(m,s[f'_pitch_add_{tap}_start'],s[f'_pitch_add_{tap}_end']))
        assert additions[-1]['tstates']==52
    address=s['_pitch_sum_state'];m.unmark_addrs(address,3,m.WRITE_MARK)
    flush_values=edges+[rng.randrange(1<<24) for _ in range(1024)]
    for value in flush_values:
        m.alt_hl=value&65535;m.alt_c=value>>16
        m.memory[address:address+4]=b'\xa5'*4
        assert run(m,s['_pitch_flush_start'],s['_pitch_flush_end'])==41
        assert bytes(m.memory[address:address+4])==value.to_bytes(3,'little')+b'\xa5'
        assert m.sp==0xbffe
    flush=audit(m,s['_pitch_flush_start'],s['_pitch_flush_end'])
    assert flush['tstates']==41
    r=dict(modulo24_addition_cases_per_tap=len(pairs),modulo24_addition_cases=len(pairs)*3,
           every_low_word_covered=True,init=initial,additions=additions,flush=flush,
           exact_writeback_cases=len(flush_values),all_writes_guarded=True,real_stack_preserved=True,
           previous_tstates=dict(init=42,addition=89,flush=0),
           speech_pitch_terms=559217,speech_samples=186880,
           predicted_full_saving_tstates=559217*37-186880*24)
    (folder/'pitch-accumulator-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r,flush=True)


if __name__=='__main__':main()
