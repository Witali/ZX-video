"""Exhaust every signed16 coefficient and audit the negated table-step arithmetic."""
from collections import Counter
import json
import struct
from check_primitives import machine,symbols,call,timing
from verify import ROOT


def guarded(folder):
    m=machine(folder);s=symbols(folder);m.ix=0x1234;m.iy=0x5678
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    m.unmark_addrs(0x7200,2560,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('builder write',hex(address),value))
    m.set_write_callback(bad)
    # First use must populate even all-zero pages. Later only page zero changes.
    call(m,s['_prepare_coefficients'],budget=1000000)
    assert bytes(m.memory[0x7200:0x7c00])==bytes(2560)
    m.mark_addrs(0x7300,2304,m.WRITE_MARK)
    return m,s


def full_domain(old_folder,new_folder,saving=282):
    variants=[guarded(old_folder),guarded(new_folder)];costs=[Counter(),Counter()]
    factors=[(n-16 if part==3 and n>=8 else n)<<(part*4) for part in range(4) for n in range(16)]
    for coef in range(-32768,32768):
        want=struct.pack('<64I',*[(coef*f)&0xffffffff for f in factors]);pair=[]
        for i,(m,s) in enumerate(variants):
            m.memory[s['_zx_lpc']:s['_zx_lpc']+2]=struct.pack('<h',coef)
            t=call(m,s['_prepare_coefficients'],budget=1000000)
            assert bytes(m.memory[0x7200:0x7300])==want,('coefficient',i,coef)
            assert (m.sp,m.ix,m.iy)==(0xbffe,0x1234,0x5678)
            pair.append(t);costs[i][t]+=1
        assert pair[0]-pair[1]==saving,(coef,pair)
    unchanged=[]
    for m,s in variants:
        before=bytes(m.memory[0x7200:0x7c00])
        unchanged.append(call(m,s['_prepare_coefficients'],budget=1000000))
        assert bytes(m.memory[0x7200:0x7c00])==before
    assert unchanged==[976,976]
    return dict(signed16_coefficients=65536,exact_entries_per_variant=65536*64,
                previous_tstates=dict(costs[0]),selected_tstates=dict(costs[1]),
                saving_per_changed_page=saving,unchanged_cache_tstates=unchanged,
                sp_ix_iy_preserved=True,all_writes_guarded_other_pages_immutable=True)


def negations(folder):
    m=machine(folder);s=symbols(folder);audits=[]
    m.mark_addrs(0,65536,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('negation write',hex(address),value))
    m.set_write_callback(bad)
    for part in range(4):
        start=s[f'_coef_neg_{part}_start'];end=s[f'_coef_neg_{part}_end'];cost=65 if part<2 else 50
        m.set_breakpoint(end)
        for coef in range(-32768,32768):
            word=(coef<<(4*part))&0xffffffff
            m.de=word&65535;m.alt_de=word>>16;m.hl=0xabcd;m.alt_hl=0x1234
            m.pc=start;m.ticks_to_stop=1000
            while m.pc!=end:assert not(m.run()&m._TICKS_LIMIT_HIT)
            assert (m.alt_de<<16|m.de)==(-word)&0xffffffff,(coef,part)
            assert (m.hl,m.alt_hl)==(0xabcd,0x1234)
            assert 1000-m.ticks_to_stop==cost
        m.pc=start;total=0;instructions=0
        while m.pc!=end:
            want=timing(m);tick=m.frame_tick;m.ticks_to_stop=1;m.run()
            got=(m.frame_tick-tick)%100000;assert got==want
            total+=got;instructions+=1
        assert total==cost
        audits.append(dict(part=part,cases=65536,tstates=cost,instructions=instructions,
                           every_instruction_matches=True,accumulator_halves_preserved=True))
        m.clear_breakpoint(end)
    return audits


def main():
    out=ROOT/'build/speex-port'
    r=dict(baseline='pure-r23-pop',variant='pure-r24',
           full_coefficient_domain=full_domain(out/'pure-r23-pop',out/'pure-r24'),
           step_negations=negations(out/'pure-r24'),
           previous_update_tstates=42,selected_update_tstates=34,updates_per_page=64,
           negation_setup_tstates=230,net_page_saving=64*8-230)
    (out/'pure-r24/coefficient-step-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r,flush=True)


if __name__=='__main__':main()
