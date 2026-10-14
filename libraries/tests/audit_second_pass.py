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


def item17():
    checks=differences=0
    for value in range(23,256):
        old,_=run('3d fe 17 30 01 3c',dict(af=value<<8))
        bounded,t=run('d6 18 ce 17',dict(af=value<<8))
        assert old.a==bounded.a==max(23,value-1) and t==14
        differences+=old.f!=bounded.f;checks+=1
    wrong_lengths=0
    for value in range(2,24):
        bounded,_=run('d6 18 ce 17',dict(af=value<<8))
        wrong_lengths+=bounded.a!=value-1;checks+=1
    ring_counterexample=None
    for value in range(4):
        wrap,_=run('3c e6 03',dict(af=value<<8))
        saturated,_=run('fe 03 28 01 3c',dict(af=value<<8))
        if wrap.a!=saturated.a:ring_counterexample=dict(input=value,required=wrap.a,saturated=saturated.a)
        checks+=1
    assert wrong_lengths==22 and ring_counterexample==dict(input=3,required=0,saturated=3)
    return dict(decision='no saturating counter contract in current codecs',checks=checks,
        corrected_domain=[23,255],corrected_tstates=14,final_flag_differences=differences,
        legal_short_count_failures=wrong_lengths,ring_counterexample=ring_counterexample,
        findings=['Length/offset arithmetic represents exact standard fields, not a saturating minimum/maximum.',
                  'ZX0 four-bank ring index wraps modulo4; holding the upper bound selects the wrong bank.',
                  'The source lower-bound off-by-one and corrected dead-flag primitive remain recorded; no current caller has its preconditions.'])


def item18():
    for flags in range(256):
        memory=((0x300,b'\xc9'),(0xbff0,b'\x00\x01'))
        old,ot=run('cd 00 03 c9',dict(af=0x7300|flags),memory=memory,stop=0x100)
        tail,nt=run('c3 00 03',dict(af=0x7300|flags),memory=memory,stop=0x100)
        assert (old.af,old.sp)==(tail.af,tail.sp) and (ot,nt)==(37,20)
    old,_=run('cd 00 03 23 c9',dict(hl=0),memory=memory,stop=0x100)
    wrong,_=run('c3 00 03',dict(hl=0),memory=memory,stop=0x100)
    assert old.hl==1 and wrong.hl==0
    continuation=dict(required_hl=old.hl,wrong_hl=wrong.hl)
    class_deltas={}
    for value in range(256):
        old_stop=0x300 if value<128 else 0x230 if value<192 else 0x208
        new_stop=0x300 if value<128 else 0x215 if value<192 else 0x320
        old,ot=run('b7 f2 00 03 fe c0 38 28',dict(af=value<<8),stop=old_stop)
        # Reuse the existing Case1xx CP/JP tail instead of the local CP/JR.
        new,nt=run('b7 f2 00 03 c3 10 02 '+'00 '*9+'fe c0 d2 20 03',dict(af=value<<8),stop=new_stop)
        assert old.af==new.af
        name='0xx' if value<128 else '10x' if value<192 else '11x'
        class_deltas[name]=dict(before_tstates=ot,merged_tstates=nt,delta=nt-ot)
    assert [class_deltas[k]['delta'] for k in ('0xx','10x','11x')]==[0,8,13]
    return dict(decision='existing tail jumps retained / slower literal tail merge rejected',checks=513,
        leaf_tail=dict(before_tstates=37,after_tstates=20,delta=-17,includes_callee_ret=True),
        continuation_counterexample=continuation,
        literal_tail_merge=dict(code_bytes_saved=1,classes=class_deltas),
        findings=['ZX0 literal/ring-copy tail jumps and inline match/literal options already avoid CALL/RET where possible.',
                  'LZSA2 guard/input_wait/yield calls have required post-return copy, status clearing or ReadToken continuations; they are not leaf tail calls.',
                  'Sharing the existing literal CP/JP dispatch tail saves one byte but slows 10x/11x entries by8/13 T.'])


def item19():
    stale=0
    for previous in (0xffff,0xfffe,0xffdf,0xfe00,0xe000):
        memory=((0x6004,previous.to_bytes(2,'little')),)
        reset,ot=run('01 ff ff ed 43 04 60 2a 04 60',dict(),memory=memory)
        omitted,nt=run('2a 04 60',dict(),memory=memory)
        assert reset.hl==0xffff and omitted.hl==previous and (ot,nt)==(46,16)
        stale+=omitted.hl!=reset.hl
    from zx0 import banked
    blob,labels=banked.build()
    table=bytes(blob[labels['ring_banks']-banked.CODE:labels['ring_banks']-banked.CODE+4])
    assert table==bytes(banked.BANKS)
    return dict(decision='constant data already emitted / mutable reset cannot be preinitialized once',checks=6,
        compiled_ring_table=list(table),stale_offset_cases=stale,
        omitted_reset_probe=dict(before_tstates=46,omitted_tstates=16,incorrect_after_prior_block=True),
        findings=['Generators emit tables/state using DB/words, not repeated per-byte initializer routines.',
                  'ZX0 last offset must reset to -1 on every block; compile-time data does not reset the operand after a prior decode.',
                  'Caller-owned pointer/end/frontier state changes each block; the only adjacent runtime zero flags were improved in item16.',
                  'Moving state to external BSS without initialization changes storage accounting, not total required RAM or repeated-entry semantics.'])


def item21():
    counts=(2,3,8,9,18,24,255,256,257,511,512,8192,15872)
    lost=[]
    for count in counts:
        word,_=run('0b',dict(bc=count))
        byte,_=run('0d',dict(bc=count))
        assert word.bc==count-1
        if byte.bc!=word.bc:lost.append(dict(input=count,expected=word.bc,byte_counter=byte.bc))
    role_failures=0
    for high in (0,1,0x7f,0x80,0xfe,0xff):
        for length in (2,18,24,255):
            cleared,_=run('06 00',dict(bc=(high<<8)|length))
            omitted,_=run('',dict(bc=(high<<8)|length))
            assert cleared.bc==length
            role_failures+=omitted.bc!=cleared.bc
    from measure_long_copy import noncanonical_cases
    from lzsa.resumable import build
    from lzsa.native import execute
    native=build();short=0
    for _,payload,raw in noncanonical_cases():
        assert execute(*native,payload,raw,source=0x2000)['exact'];short+=1
    return dict(decision='retain per-path width/role proofs; reject global byte-range assumptions',checks=len(counts)+24+short,
        narrowed_count_failures=lost,offset_to_count_role_failures=role_failures,
        short_escaped_word_blocks=short,
        findings=['BC is a negative offset/token/count at different points; SaveOffset must clear B before the next short match.',
                  'DEC C does not borrow from B at256/512/page-multiple lengths, and changes flags.',
                  'All18 short escaped-word blocks remain legal and exact; word encoding alone supplies no lower bound.',
                  'Current fast gamma, byte-form unroll and fixed256-byte refill already use local structural bounds.'])


def item25():
    checks=0;live_de_failures=0
    for word in (0,1,0x9abc,0xffff):
        for flags in range(256):
            registers=dict(hl=0x4000,de=0xc100,bc=0x2468,af=0x7300|flags)
            memory=((0xbff0,word.to_bytes(2,'little')),)
            old,ot=run('eb e1 d5',registers,memory=memory)
            new,nt=run('e3',registers,memory=memory)
            assert (old.hl,old.sp,old.af,old.bc)==(new.hl,new.sp,new.af,new.bc)
            assert bytes(old.memory[0xbff0:0xbff2])==bytes(new.memory[0xbff0:0xbff2])
            assert (ot,nt)==(25,19)
            live_de_failures+=old.de!=new.de;checks+=1
    assert live_de_failures==checks
    standard=(ROOT/'zx0/src/zx0/asm/dzx0_standard.asm').read_text()
    assert standard.count('ex      (sp), hl')==2
    return dict(decision='already present in stack-offset ZX0; retain live DE/continuations elsewhere',
        checks=checks,primitive=dict(before_tstates=25,after_tstates=19,code_bytes_delta=-2),
        live_de_counterexamples=live_de_failures,existing_standard_exchange_sites=2,
        findings=['ZX0 Standard already exchanges the owned offset stack word with HL before/after a match.',
                  'Fast/Turbo/LZSA2 keep the offset in a patched operand; DE remains the advancing output pointer, not dead scratch.',
                  'Coroutine saved words are live source/output/count/AF and a return continuation. An owned word alone is insufficient to replace pair saves.',
                  'No adapted core has an eligible EX DE,HL / POP HL / PUSH DE chain with dead DE; retain current stack and register contracts.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--item',choices=('11','12','13','14','15','17','18','19','21','25'),required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    defaults=profiles();assert defaults==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    report=dict(date='2026-10-14',item=args.item,complete=True,release=False,scope=__doc__,
        baseline_revision=subprocess.check_output(['git','rev-parse','--short=8','HEAD'],text=True).strip(),
        **globals()['item'+args.item](),default_profiles_exact=len(defaults),decoder_changes=0,
        actual_decoder_delta_tstates=0,actual_code_state_payload_delta=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(item=args.item,decision=report['decision'],checks=report['checks'],defaults=len(defaults))))


if __name__=='__main__':main()
