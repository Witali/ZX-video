"""Verify shared Q14 normalization, exact floor rounding and instruction costs."""
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
from check_word_product import u8_cost,word_cost,preserved
from check_constant_pitch import extra_stream
from verify import ROOT,sha

VARIANTS=('pure-r31','pure-r32')


def parts(b):
    hi=(b>>14)&65535
    return (hi-65536 if hi&32768 else hi),b&16383


def unsigned_cost(x,y):
    if not x:return 50
    if not y:return 60
    if x<256:return 35+20+46+u8_cost(x,False)+10
    if y<256:return 35+34+46+u8_cost(y,False)+10
    return 35+35+114+u8_cost(x&255)+u8_cost(x>>8,False)+10


def q14_cost(a,b,new):
    hi,lo=parts(b)
    if not new:return 491+word_cost(hi,a,True)+word_cost(lo,a,True)
    c=abs(a)
    # Sign store, normalize coefficient, store magnitude, copy argument,
    # extract high word, reload coefficient, sign/call high product.
    wrapper=24+(39 if a<0 else 20)+16+103+74+20+(150 if hi<0 else 37)
    # Store high product, extract/call low product, choose sign tail.
    wrapper+=36+68+27
    # The unsigned low product needs zero extension after >>14; then add hi.
    wrapper+=137
    if a<0:wrapper+=25+(77 if c*lo%16384==0 else 74)
    else:wrapper+=10
    return wrapper+unsigned_cost(abs(hi),c)+unsigned_cost(lo,c)


def guarded(folder):
    m=machine(folder);s=symbols(folder)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    if '_q14_sign' in s:
        assert s['_q14_scratch_end']-s['_q14_scratch_start']==10
        m.unmark_addrs(s['_q14_sign'],1,m.WRITE_MARK)
        m.unmark_addrs(s['_q14_scratch_start'],10,m.WRITE_MARK)
    else:m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('Q14 write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad)
    m.alt_af=0x1234;m.alt_bc=0xabcd;m.alt_de=0x3456;m.alt_hl=0x5678;m.ix=0xcafe;m.iy=0xdead
    return m,s


def product(m,s,a,b,new,audit=False):
    raw=struct.pack('<i',b);m.memory[0x7e00:0x7e04]=raw
    if audit:
        m.hl=a&65535;m.de=0x7e00;m.sp=0xbffc
        m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=s['mulq14'];cost=0;instructions=0
        while m.pc!=0x7f00:cost+=step(m);instructions+=1
    else:cost=call(m,s['mulq14'],hl=a&65535,de=0x7e00);instructions=0
    hi,lo=parts(b);want=(a*hi+((a*lo)>>14))&0xffffffff
    assert (m.hl<<16|m.de)==want,(a,b,m.hl,m.de,want)
    assert cost==q14_cost(a,b,new),(a,b,cost,q14_cost(a,b,new))
    assert bytes(m.memory[0x7e00:0x7e04])==raw
    preserved(m)
    return cost,instructions


def audits(out):
    values=(-32768,-32767,-16384,-257,-256,-255,-1,0,1,2,127,128,255,256,257,16384,32767)
    arguments=(-2147483648,-2147483647,-1073741825,-1073741824,-1073741823,
               -536870913,-536870912,-536870911,-16385,-16384,-16383,-1,0,1,
               16383,16384,16385,536870911,536870912,1073741823,1073741824,2147483647)
    result={}
    for v in VARIANTS:
        m,s=guarded(out/v);hist=Counter();instructions=0
        for a in values:
            for b in arguments:
                cost,n=product(m,s,a,b,v=='pure-r32',True);hist[cost]+=1;instructions+=n
        result[v]=dict(cases=len(values)*len(arguments),instructions=instructions,
                       minimum_tstates=min(hist),maximum_tstates=max(hist),
                       every_instruction_matches_timing_table=True,all_registers_and_writes_guarded=True)
    return result


def observe(out):
    from verify import native
    pairs=[];reports=[];totals=[];rows=[];categories=Counter();saving_hist=Counter()
    for i,v in enumerate(VARIANTS):
        operands=[]
        def observer(name,m):
            operands.append((m.hl-65536 if m.hl&32768 else m.hl,
                             int.from_bytes(m.memory[m.de:m.de+4],'little',signed=True)))
        with redirect_stdout(io.StringIO()):
            r=native(out,v+'-q14-profile',out/v,profile=('mulq14',),entry_observer=observer)
        if i:assert operands==pairs
        else:
            pairs=operands
            old=json.loads((out/v/'report.json').read_text())
            assert r['total_tstates']==old['total_tstates'] and r['binary_sha256']==old['binary_sha256']
            assert (out/v/'out-times.u64.gz').read_bytes()==(out/(v+'-q14-profile')/'out-times.u64.gz').read_bytes()
        m,s=guarded(out/v);total=0;hist=Counter()
        for (a,b),n in Counter(pairs).items():
            cost,_=product(m,s,a,b,i==1);total+=cost*n;hist[cost]+=n
        assert total==r['profile']['inclusive_tstates']['mulq14']
        totals.append(total);reports.append(r)
        rows.append(dict(variant=v,q14_tstates=total,minimum_call_tstates=min(hist),maximum_call_tstates=max(hist),
                         full_tstates=r['total_tstates'],binary_sha256=r['binary_sha256']))
    # Reconcile with the independently archived round31 signed-word operands.
    previous=list(struct.iter_unpack('<hh',gzip.decompress((ROOT/'audiobook-beeper/speex-port/rounds/31/observed-word-operands.i16.gz').read_bytes())))
    reconstructed=[]
    for a,b in pairs:
        hi,lo=parts(b);reconstructed.extend(((hi,a),(lo,a)))
        saving_hist[q14_cost(a,b,False)-q14_cost(a,b,True)]+=1
        categories[f'coefficient_{"negative" if a<0 else "nonnegative"}/high_{"negative" if hi<0 else "nonnegative"}']+=1
    assert previous==reconstructed
    assert reports[0]['total_tstates']-reports[1]['total_tstates']==totals[0]-totals[1]
    packed=b''.join(struct.pack('<hi',*p) for p in pairs)
    (out/'pure-r32/observed-q14-operands.i16i32.gz').write_bytes(gzip.compress(packed,mtime=0))
    return dict(calls=len(pairs),unique_pairs=len(set(pairs)),operands_sha256=sha(packed),sign_categories=dict(categories),
                saving_histogram=dict(sorted(saving_hist.items())),regressed_calls=sum(n for t,n in saving_hist.items() if t<0),
                variants=rows,total_saving=totals[0]-totals[1],every_operand_and_baseline_out_unchanged=True,
                previous_word_operands_reconstructed_exactly=True,isolated_costs_and_full_delta_reconcile=True,
                complete_pcm16_and_pcm8_samples=reports[1]['samples'])


def domains(out):
    m,s=guarded(out/'pure-r32');n=0;hist=Counter();saving=Counter()
    def check(a,b):
        nonlocal n
        cost,_=product(m,s,a,b,True);n+=1;hist[cost]+=1
        saving[q14_cost(a,b,False)-cost]+=1
    # Every signed16 coefficient, including zero and -32768, at 12 high/low,
    # sign, exact-divisibility and intentional high-part wrap boundaries.
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
    print('Q14 domains:',n,'passed',flush=True)
    # The unsigned entry newly permits magnitudes above signed16. Its byte
    # cores are unchanged from the exhaustive round31 check; cover word
    # combination/carry and byte dispatch with every word in both orders.
    unsigned=0
    for fixed in (0,1,255,256,257,32767,32768,65534,65535):
        for x in range(65536):
            for a,b in ((fixed,x),(x,fixed)):
                cost=call(m,s['_q14_unsigned'],hl=a,de=b)
                assert (m.hl<<16|m.de)==a*b and cost==unsigned_cost(a,b),(a,b,cost)
                preserved(m);unsigned+=1
    print('Unsigned domain:',unsigned,'passed',flush=True)
    return dict(q14_cases=n,all_signed16_coefficients_against_arguments=len(arguments),
                all_14bit_fractions_against_coefficient_high_pairs=len(coefficients)*len(high),random_signed32_cases=32768,
                unsigned16_products=unsigned,minimum_q14_tstates=min(hist),maximum_q14_tstates=max(hist),
                minimum_saving_tstates=min(saving),maximum_saving_tstates=max(saving),
                exact_results_rounding_and_instruction_formulas=True,register_contracts_input_and_writes_guarded=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--quick',action='store_true');a=p.parse_args()
    out=ROOT/'build/speex-port';r=dict(audits=audits(out),speech=observe(out))
    print({k:v for k,v in r['speech'].items() if k not in ('saving_histogram','variants')},flush=True)
    for row in r['speech']['variants']:print(row,flush=True)
    if not a.quick:r['domains']=domains(out);r['all_pitches']=extra_stream(out/'pure-r32','pure-r32')
    (out/'pure-r32/q14-product-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
