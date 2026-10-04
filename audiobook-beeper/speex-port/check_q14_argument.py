"""Verify direct Q14 argument reads, page/wrap boundaries and a 45-T saving."""
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import random
import struct
from check_primitives import call
from check_inline_products import step
from check_word_product import preserved
from check_q14_product import parts
from check_q14_sign import checked_machine
from check_q14_negated import cost37
from check_constant_pitch import extra_stream
from verify import ROOT,native,sha

VARIANTS=('pure-r37','pure-r38')


def guarded(folder,direct):
    m,s=checked_machine(folder,True)
    if direct:
        # qcoef[2], qarg[4], qtemp[4]: the private path must no longer
        # access the upper qarg bytes. Writes to them are forbidden.
        m.mark_addrs(s['_q14_scratch_start']+4,2,m.WRITE_MARK)
    return m,s


def product(m,s,a,b,direct,pointer=0x7e00,audit=False):
    raw=struct.pack('<i',b)
    for i,v in enumerate(raw):m.memory[(pointer+i)&65535]=v
    upper=s['_q14_scratch_start']+4
    if direct:m.memory[upper:upper+2]=b'\xa5\x5a'
    if audit:
        m.hl=a&65535;m.de=pointer;m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f'
        m.pc=s['_q14_negated'];cost=0;instructions=0
        while m.pc!=0x7f00:cost+=step(m);instructions+=1
    else:cost=call(m,s['_q14_negated'],hl=a&65535,de=pointer);instructions=0
    hi,lo=parts(b);want=-(a*hi+((a*lo)>>14))&0xffffffff
    assert (m.hl<<16|m.de)==want,(a,b,pointer,m.hl,m.de,want)
    assert cost==cost37(a,b)-45*direct,(a,b,pointer,cost)
    assert bytes(m.memory[(pointer+i)&65535] for i in range(4))==raw
    if direct:assert bytes(m.memory[upper:upper+2])==b'\xa5\x5a'
    preserved(m)
    return cost,instructions


def domains(out):
    m,s=guarded(out/'pure-r38',True);n=0;hist=Counter()
    def check(a,b):
        nonlocal n
        cost,_=product(m,s,a,b,True);n+=1;hist[cost]+=1
    arguments=(-2147483648,-1073741825,-536870912,-16385,-16384,-1,0,1,16383,16384,536870912,2147483647)
    for b in arguments:
        for a in range(-32768,32768):check(a,b)
    coefficients=(-32768,-32767,-16384,-257,-1,0,1,32767);high=(-32768,-1,0,32767)
    for a in coefficients:
        for hi in high:
            for lo in range(16384):check(a,(hi<<14)|lo)
    rng=random.Random(1432)
    for _ in range(32768):check(rng.randrange(-32768,32768),rng.randrange(-2147483648,2147483648))
    return dict(q14_cases=n,all_signed16_coefficients_against_arguments=len(arguments),
                all_14bit_fractions_against_coefficient_high_pairs=len(coefficients)*len(high),random_signed32_cases=32768,
                minimum_tstates=min(hist),maximum_tstates=max(hist),every_case_saves_tstates=45,
                exact_result_rounding_and_instruction_formula=True,register_input_and_writes_guarded=True,
                retired_upper_argument_bytes_unchanged=True)


def pointers_and_audits(out):
    # Use every page-boundary neighborhood outside live code/state/stack.
    # Include all starts crossing FFFF->0000. Host setup writes no decoder code.
    addresses=sorted({((page<<8)+offset)&65535 for page in range(256) for offset in (-3,-2,-1,0,1,252,253,254,255)})
    addresses=[p for p in addresses if all(not 0x8000<=((p+i)&65535)<0xc000 for i in range(4))]
    assert all(x in addresses for x in (0xffff,0xfffe,0xfffd))
    result={}
    for i,v in enumerate(VARIANTS):
        m,s=guarded(out/v,bool(i));n=0;count=0;cycles=0;audits=0
        for pointer in addresses:
            for a in (-32768,-1,0,32767):
                for b in (-2147483648,-1073741825,16383,2147483647):
                    stepping=pointer in (0,0xfd,0xfe,0xff,0x100,0xfffd,0xfffe,0xffff)
                    cost,instructions=product(m,s,a,b,bool(i),pointer,stepping)
                    n+=1
                    if stepping:audits+=1;count+=instructions;cycles+=cost
        result[v]=dict(pointer_starts=len(addresses),pointer_arithmetic_cases=n,
                       instruction_audit_cases=audits,instructions=count,audited_tstates=cycles,
                       every_instruction_matches_timing_table=True,all_page_and_16bit_wrap_cases_exact=True,
                       input_register_and_write_guards=True)
    return result


def observe(out):
    archive=ROOT/'audiobook-beeper/speex-port/rounds/32'
    packed=gzip.decompress((archive/'observed-q14-operands.i16i32.gz').read_bytes())
    pairs=list(struct.iter_unpack('<hi',packed))
    prior=json.loads((ROOT/'audiobook-beeper/speex-port/rounds/37/q14-negated-checks.json').read_text())['speech']
    assert sha(packed)==prior['operands_sha256'] and len(pairs)==93440
    observed=[]
    def observer(name,m):
        observed.append((m.hl-65536 if m.hl&32768 else m.hl,
                         int.from_bytes(m.memory[m.de:m.de+4],'little',signed=True)))
    with redirect_stdout(io.StringIO()):
        r=native(out,'pure-r38-q14-argument-profile',out/'pure-r38',profile=('_q14_negated',),entry_observer=observer)
    assert observed==pairs
    plain=json.loads((out/'pure-r38/report.json').read_text());old=json.loads((out/'pure-r37/report.json').read_text())
    assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
    assert (out/'pure-r38-q14-argument-profile/out-times.u64.gz').read_bytes()==(out/'pure-r38/out-times.u64.gz').read_bytes()
    new=sum(cost37(a,b)-45 for a,b in pairs);previous=prior['new_negated_q14_tstates']
    assert new==r['profile']['inclusive_tstates']['_q14_negated']
    assert previous-new==45*len(pairs)==old['total_tstates']-r['total_tstates']
    times=[list(struct.iter_unpack('<Q',gzip.decompress((out/v/'out-times.u64.gz').read_bytes()))) for v in VARIANTS]
    assert len(times[0])==len(times[1])==186880
    for i,(a,b) in enumerate(zip(*times)):assert a[0]-b[0]==(i//40+1)*900,i
    assert (out/'pure-r37/filter.s').read_text()==(out/'pure-r38/filter.s').read_text()
    prefix=[(out/v/'decoder.s').read_text().split('; Private LPC entry:',1)[0] for v in VARIANTS]
    assert prefix[0]==prefix[1]
    return dict(calls=len(pairs),operands_sha256=sha(packed),every_operand_unchanged=True,
                operand_archive='rounds/32/observed-q14-operands.i16i32.gz',old_q14_tstates=previous,new_q14_tstates=new,
                total_saving=previous-new,old_full_tstates=old['total_tstates'],new_full_tstates=r['total_tstates'],
                isolated_costs_and_full_delta_reconcile=True,every_call_saves_tstates=45,
                profile_preserves_every_uninstrumented_out=True,every_out_delta_matches_cumulative_saving=True,
                other_decoder_and_filter_assembly_unchanged=True,complete_pcm16_and_pcm8_samples=186880)


def main():
    out=ROOT/'build/speex-port';r=dict(pointers_and_audits=pointers_and_audits(out),domains=domains(out))
    print('Pointer audits and arithmetic domains pass:',r['domains']['q14_cases'],flush=True)
    r['speech']=observe(out);print('Speech:',r['speech'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r38','pure-r38')
    (out/'pure-r38/q14-argument-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
