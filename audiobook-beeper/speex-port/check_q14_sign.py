"""Verify exact Q14 sign-specific tails, carry/borrow rounding and total savings."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import random
import struct
from check_primitives import machine,symbols,call
from check_inline_products import step
from check_word_product import preserved
from check_q14_product import parts,unsigned_cost,q14_cost,guarded
from check_constant_pitch import extra_stream
from verify import ROOT,image,sha

VARIANTS=('pure-r32','pure-r33')


def cost33(a,b):
    hi,lo=parts(b);c=abs(a)
    if a<0:wrapper=585 if hi<0 else 650
    else:
        carry=(((a*hi)&65535)+((c*lo)>>14))>65535
        wrapper=494+113*(hi<0)+carry
    return wrapper+unsigned_cost(abs(hi),c)+unsigned_cost(lo,c)


def product(m,s,a,b,new,audit=False):
    raw=struct.pack('<i',b);m.memory[0x7e00:0x7e04]=raw
    if audit:
        m.hl=a&65535;m.de=0x7e00;m.sp=0xbffc
        m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=s['mulq14'];cost=0;instructions=0
        while m.pc!=0x7f00:cost+=step(m);instructions+=1
    else:cost=call(m,s['mulq14'],hl=a&65535,de=0x7e00);instructions=0
    hi,lo=parts(b);want=(a*hi+((a*lo)>>14))&0xffffffff
    assert (m.hl<<16|m.de)==want,(a,b,m.hl,m.de,want)
    expected=cost33(a,b) if new else q14_cost(a,b,True)
    assert cost==expected,(a,b,cost,expected)
    assert bytes(m.memory[0x7e00:0x7e04])==raw
    preserved(m)
    return cost,instructions


def checked_machine(folder,new):
    m,s=guarded(folder)
    # The new path no longer accesses the old sign slot. Only ten scratch
    # bytes and the existing real stack may be written by Q14 or its helpers.
    if new:m.mark_addrs(s['_q14_sign'],1,m.WRITE_MARK)
    return m,s


def audits(out):
    values=(-32768,-32767,-16384,-257,-256,-255,-1,0,1,2,127,128,255,256,257,16384,32767)
    arguments=(-2147483648,-2147483647,-1073741825,-1073741824,-1073741823,
               -536870913,-536870912,-536870911,-16385,-16384,-16383,-1,0,1,
               16383,16384,16385,536870911,536870912,1073741823,1073741824,2147483647)
    result={}
    for i,v in enumerate(VARIANTS):
        m,s=checked_machine(out/v,i==1);hist=Counter();instructions=0
        for a in values:
            for b in arguments:
                cost,n=product(m,s,a,b,i==1,True);hist[cost]+=1;instructions+=n
        result[v]=dict(cases=len(values)*len(arguments),instructions=instructions,
                       minimum_tstates=min(hist),maximum_tstates=max(hist),
                       every_instruction_matches_timing_table=True,all_registers_input_and_writes_guarded=True)
    return result


def observe(out):
    from verify import native
    archive=ROOT/'audiobook-beeper/speex-port/rounds/32'
    packed=gzip.decompress((archive/'observed-q14-operands.i16i32.gz').read_bytes())
    pairs=list(struct.iter_unpack('<hi',packed));baseline=json.loads((archive/'report.json').read_text())
    previous=json.loads((archive/'q14-product-checks.json').read_text())['speech']
    assert sha(packed)==previous['operands_sha256']
    m=image(out/'pure-r32/player.ihx');assert sha(bytes(m[k] for k in sorted(m)))==baseline['binary_sha256']
    observed=[]
    def observer(name,m):
        observed.append((m.hl-65536 if m.hl&32768 else m.hl,
                         int.from_bytes(m.memory[m.de:m.de+4],'little',signed=True)))
    with redirect_stdout(io.StringIO()):
        r=native(out,'pure-r33-q14-profile',out/'pure-r33',profile=('mulq14',),entry_observer=observer)
    assert observed==pairs
    plain=json.loads((out/'pure-r33/report.json').read_text())
    assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
    assert (out/'pure-r33-q14-profile/out-times.u64.gz').read_bytes()==(out/'pure-r33/out-times.u64.gz').read_bytes()
    totals=[];rows=[];saving=Counter()
    for i,v in enumerate(VARIANTS):
        m,s=checked_machine(out/v,i==1);total=0;hist=Counter()
        for (a,b),n in Counter(pairs).items():
            cost,_=product(m,s,a,b,i==1);total+=cost*n;hist[cost]+=n
        measured=r['profile']['inclusive_tstates']['mulq14'] if i else previous['variants'][-1]['q14_tstates']
        assert total==measured
        totals.append(total)
        report=r if i else baseline
        rows.append(dict(variant=v,q14_tstates=total,minimum_call_tstates=min(hist),maximum_call_tstates=max(hist),
                         full_tstates=report['total_tstates'],binary_sha256=report['binary_sha256']))
    for a,b in pairs:saving[q14_cost(a,b,True)-cost33(a,b)]+=1
    assert min(saving)>0
    assert sum(t*n for t,n in saving.items())==totals[0]-totals[1]==baseline['total_tstates']-r['total_tstates']
    # Only decoder.s changes. Reuse the previous unsigned helper proof with
    # an exact assembly-source identity check for the entire filter unit.
    assert (out/'pure-r32/filter.s').read_text()==(out/'pure-r33/filter.s').read_text()
    return dict(calls=len(pairs),unique_pairs=len(set(pairs)),operands_sha256=sha(packed),
                operand_archive='rounds/32/observed-q14-operands.i16i32.gz',saving_histogram=dict(sorted(saving.items())),
                every_call_faster=True,variants=rows,total_saving=totals[0]-totals[1],
                every_operand_unchanged=True,profile_preserves_every_uninstrumented_out=True,
                baseline_image_identity_verified=True,isolated_costs_and_full_delta_reconcile=True,
                full_filter_assembly_unchanged=True,complete_pcm16_and_pcm8_samples=r['samples'])


def domains(out):
    m,s=checked_machine(out/'pure-r33',True);n=0;hist=Counter();saving=Counter();paths=Counter()
    def check(a,b):
        nonlocal n
        cost,_=product(m,s,a,b,True);n+=1;hist[cost]+=1
        delta=q14_cost(a,b,True)-cost;saving[delta]+=1;assert delta>=30
        hi,lo=parts(b)
        if a<0:
            remainder=(abs(a)*lo)%16384!=0
            paths[f'negative/high_{hi<0}/rounding_borrow_{remainder}']+=1
        else:
            carry=((a*hi)&65535)+((a*lo)>>14)>65535
            paths[f'nonnegative/high_{hi<0}/carry_{carry}']+=1
    arguments=(-2147483648,-1073741825,-536870912,-16385,-16384,-1,0,1,16383,16384,536870912,2147483647)
    for b in arguments:
        for a in range(-32768,32768):check(a,b)
    coefficients=(-32768,-32767,-16384,-257,-1,0,1,32767)
    high=(-32768,-1,0,32767)
    for a in coefficients:
        for hi in high:
            for lo in range(16384):check(a,(hi<<14)|lo)
    rng=random.Random(1432)
    for _ in range(32768):check(rng.randrange(-32768,32768),rng.randrange(-2147483648,2147483648))
    assert len(paths)==8 and set(saving)=={30,33,77,78,208,211}
    return dict(q14_cases=n,all_signed16_coefficients_against_arguments=len(arguments),
                all_14bit_fractions_against_coefficient_high_pairs=len(coefficients)*len(high),random_signed32_cases=32768,
                minimum_q14_tstates=min(hist),maximum_q14_tstates=max(hist),paths=dict(paths),
                saving_histogram=dict(sorted(saving.items())),minimum_saving_tstates=min(saving),maximum_saving_tstates=max(saving),
                exact_results_rounding_and_instruction_formulas=True,register_contracts_input_and_writes_guarded=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--quick',action='store_true');a=p.parse_args()
    out=ROOT/'build/speex-port';r=dict(audits=audits(out),speech=observe(out))
    print({k:v for k,v in r['speech'].items() if k!='variants'},flush=True)
    for row in r['speech']['variants']:print(row,flush=True)
    if not a.quick:
        r['domains']=domains(out);print('Q14 domains:',r['domains']['q14_cases'],'passed',flush=True)
        r['all_pitches']=extra_stream(out/'pure-r33','pure-r33')
    (out/'pure-r33/q14-sign-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
