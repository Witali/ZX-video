"""Native eligibility/counterexample audits for unchanged second-pass paths."""
import argparse
import json
from pathlib import Path
import subprocess

from measure_tricks import run
from test_libraries import profiles, ROOT


def item11():
    checks=0
    for value in range(256):
        for carry in (0,1):
            registers=dict(hl=0x6000,bc=0x7373,af=0x9700|carry)
            memory=((0x6000,bytes([value])),)
            old,ot=run('7e b7 08 7e 23 0f 0f 0f 0f f6 f0',registers,memory=memory)
            cached,nt=run('c5 7e 47 b7 08 78 23 0f 0f 0f 0f f6 f0 c1',registers,memory=memory)
            assert tuple(getattr(old,k) for k in ('af','alt_af','bc','de','hl','sp'))==tuple(
                getattr(cached,k) for k in ('af','alt_af','bc','de','hl','sp'))
            assert (ot,nt)==(51,73);checks+=1
    old,ot=run('3a 04 60 3e 55 3a 04 60',dict(af=0x7337),memory=((0x6004,b'\x17'),))
    cached,nt=run('3a 04 60 f5 3e 55 f1',dict(af=0x7337),memory=((0x6004,b'\x17'),))
    assert old.af==cached.af and (ot,nt)==(33,41)
    return dict(decision='already present / caching rejected where registers are live',checks=checks+1,
        nibble_reload=dict(before_tstates=51,cached_tstates=73,delta=22,token_pair_preserved=True),
        history_page_reload=dict(before_tstates=33,cached_tstates=41,delta=8),
        findings=['LZSA2 nibble refill reads the same byte twice across EX AF,AF\'; B/C hold a live token/count, DE output and HL input. Safe BC caching costs more than the second 7-T load.',
                  'ZX0 paging/copy rewrites main scratch pairs; retaining a page on the stack costs more than its 13-T reload.',
                  'Offset and target constants are already patched into operands; the separate sync target reload is evaluated in item20.'])


def item12():
    for value in range(256):
        memory=((0x6004,bytes([value])),)
        old,ot=run('21 04 60 7e',dict(af=0x9737,hl=0x5000),memory=memory)
        direct,nt=run('3a 04 60',dict(af=0x9737,hl=0x5000),memory=memory)
        assert old.af==direct.af and (ot,nt)==(17,13)
    memory=((0x6004,b'A'),)
    old,_=run('21 04 60 7e 23',dict(hl=0x5000),memory=memory)
    wrong,_=run('3a 04 60 23',dict(hl=0x5000),memory=memory)
    assert old.a==wrong.a and old.hl==0x6005 and wrong.hl==0x5001
    dynamic,dt=run('7e',dict(hl=0x6004),memory=memory)
    direct,nt=run('3a 04 60',dict(hl=0x6004),memory=memory)
    assert dynamic.a==direct.a and (dt,nt)==(7,13)
    return dict(decision='already direct for fixed state / input pointer must remain live',checks=258,
        dead_pointer_primitive=dict(before_tstates=17,after_tstates=13),
        live_pointer_counterexample=dict(expected_hl=old.hl,wrong_hl=wrong.hl),
        established_input_pointer=dict(indirect_tstates=7,absolute_tstates=13,delta=6),
        findings=['LZSA2/ZX0 cold state accesses already use absolute load/store forms.',
                  'Core HL is a dynamic advancing input/history pointer, not a disposable construction for one static byte.',
                  'ZX0 ring_banks is dynamically indexed; aligned lookup was measured separately in item06.'])


def item13():
    changed=0
    for value in range(256):
        registers=dict(hl=0x6004,af=0x9737)
        memory=((0x6004,bytes([value])),)
        old,ot=run('7e cb 3f',registers,memory=memory)
        inplace,nt=run('cb 3e',registers,memory=memory)
        assert old.a==value>>1 and old.memory[0x6004]==value
        assert inplace.memory[0x6004]==value>>1 and (ot,nt)==(15,15)
        assert old.f==inplace.f
        changed+=old.memory[0x6004]!=inplace.memory[0x6004]
    return dict(decision='inapplicable to immutable compressed input / no indexed state RMW',checks=256,
        register_shift_tstates=15,inplace_shift_tstates=15,input_bytes_changed=changed,
        indexed_state_primitive_reference='forum_primitive_screen.json',
        findings=['No runtime indexed shift/store sequence exists in adapted codec state; indexed46 ->23-T primitive has no current site.',
                  'Compressed-input shifts produce an A value/reservoir rather than update a mutable memory counter.',
                  'In-place SRL (HL) changes unread/shared nibble bytes and leaves A unchanged, with no saving over LD A,(HL)/SRL A.'])


def item14():
    for value in range(256):
        old,ot=run('0f 0f 0f 0f f6 f0',dict(af=value<<8))
        narrow,nt=run('cb 3f cb 3f cb 3f cb 3f f6 f0',dict(af=value<<8))
        assert old.af==narrow.af and old.a==0xf0|(value>>4) and (ot,nt)==(23,39)
    lost=0
    for value in range(256):
        for carry in (0,1):
            old,ot=run('cb 11 cb 10',dict(bc=value,af=0x7300|carry))
            wrong,nt=run('cb 11',dict(bc=value,af=0x7300|carry))
            assert (ot,nt)==(16,8)
            lost+=old.bc!=wrong.bc
    assert lost==256
    return dict(decision='retain fast accumulator rotations / unproved word narrowing rejected',checks=768,
        high_nibble=dict(before_tstates=23,narrow_shift_tstates=39,delta=16),
        word_shift=dict(checks=512,lost_high_byte_cases=lost),
        findings=['LZSA2 already uses four4-T RRCA instructions; the OR F0 result and flags are live. SRL-based narrowing is slower; RRD would mutate input.',
                  'ZX0 already uses ADD A,A/RLA and specialized short-offset/short-gamma paths. Its longer lengths may carry into B.',
                  'Additional bit-phase specialization is evaluated separately in item23; no generic high-byte omission.'])


def item15():
    checks=0
    for high in (0,1,0x20,0x60,0x7f,0x80,0xfe,0xff):
        for low in range(256):
            registers=dict(hl=(high<<8)|low,af=0x9737)
            old,ot=run('7d c6 1f 7c ce 00',registers)
            cached,nt=run('7d c6 1f 7c ce 00 32 04 60 3a 04 60',registers)
            assert old.af==cached.af and (ot,nt)==(22,48);checks+=1
    old,ot=run('21 00 60 7e 21 01 60 7e',dict(hl=0x6000),memory=((0x6000,b'AB'),))
    running,nt=run('7e 23 7e',dict(hl=0x6000),memory=((0x6000,b'AB'),))
    assert (old.hl,old.af)==(running.hl,running.af) and (ot,nt)==(34,20)
    return dict(decision='running pointers already present / unconditional address cache rejected',checks=checks+1,
        header_address_cache=dict(before_tstates=22,first_cached_tstates=48,first_delta=26,
            later_load_lower_bound=13,extra_state_bytes_at_least=1),
        running_pointer=dict(reconstructed_tstates=34,existing_running_tstates=20),
        findings=['HL/DE advance directly with INC/LDI/LDIR; no per-byte index-to-base recomputation.',
                  'Header/literal guard endpoints depend on the current HL/BC; the ready path cannot assume a previous token\'s address.',
                  'A wait-only cache would need separate pointer/overflow/continuation ownership and preserve reentry through ReadToken after target/frontier updates; it is not a free common-subexpression replacement.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--item',choices=('11','12','13','14','15'),required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    defaults=profiles();assert defaults==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    report=dict(date='2026-10-14',item=args.item,complete=True,release=False,scope=__doc__,
        baseline_revision=subprocess.check_output(['git','rev-parse','--short=8','HEAD'],text=True).strip(),
        **globals()['item'+args.item](),default_profiles_exact=len(defaults),decoder_changes=0,
        actual_decoder_delta_tstates=0,actual_code_state_payload_delta=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(item=args.item,decision=report['decision'],checks=report['checks'],defaults=len(defaults))))


if __name__=='__main__':main()
