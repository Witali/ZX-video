"""Verify the private negative Q14 entry, caller fusion and exact stream savings."""
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
from check_q14_product import parts,unsigned_cost
from check_q14_sign import checked_machine,cost33,product as ordinary_product
from check_constant_pitch import extra_stream
from verify import ROOT,native,sha

VARIANTS=('pure-r36','pure-r37')


def cost37(a,b):
    hi,lo=parts(b);c=abs(a)
    # Instruction-table sums excluding the two unchanged unsigned products:
    # dispatch 18, prepare 213, fraction 153, coefficient normalization 0/24.
    # a>=0: high-sign setup 66/121 (negative/nonnegative hi), subtract 98.
    # a<0: high-sign setup 145/42, add-ceiling tail 99 plus low carry.
    if a<0:
        carry=(((c*hi)&65535)+((c*lo+16383)>>14))>65535
        wrapper=18+24+213+(145 if hi<0 else 42)+153+99+carry
    else:wrapper=18+213+(66 if hi<0 else 121)+153+98
    return wrapper+unsigned_cost(abs(hi),c)+unsigned_cost(lo,c)


def product(m,s,a,b):
    raw=struct.pack('<i',b);m.memory[0x7e00:0x7e04]=raw
    cost=call(m,s['_q14_negated'],hl=a&65535,de=0x7e00)
    hi,lo=parts(b);want=-(a*hi+((a*lo)>>14))&0xffffffff
    assert (m.hl<<16|m.de)==want,(a,b,m.hl,m.de,want)
    assert cost==cost37(a,b),(a,b,cost,cost37(a,b))
    assert bytes(m.memory[0x7e00:0x7e04])==raw
    preserved(m)
    return cost


def caller_audits(out):
    values=(-32768,-32767,-16384,-257,-256,-255,-1,0,1,2,127,128,255,256,257,16384,32767)
    arguments=(-2147483648,-2147483647,-1073741825,-1073741824,-1073741823,
               -536870913,-536870912,-536870911,-16385,-16384,-16383,-1,0,1,
               16383,16384,16385,536870911,536870912,1073741823,1073741824,2147483647)
    result={}
    for i,v in enumerate(VARIANTS):
        m,s=checked_machine(out/v,True)
        label='_q14_negated' if i else 'mulq14'
        callbytes=b'\xcd'+struct.pack('<H',s[label]);mem=bytes(m.memory)
        addresses=[a for a in range(0x8000,0xb000) if mem[a:a+3]==callbytes]
        assert len(addresses)==20
        start=addresses[0];stop=start+(3 if i else 6)
        if not i:assert mem[start+3]==0xcd
        instructions=0;total=0;ordinary=0
        for a in values:
            for b in arguments:
                raw=struct.pack('<i',b);m.memory[0x7e00:0x7e04]=raw
                m.hl=a&65535;m.de=0x7e00;m.sp=0xbffe;m.pc=start;cost=0
                while m.pc!=stop:cost+=step(m);instructions+=1
                hi,lo=parts(b);want=-(a*hi+((a*lo)>>14))&0xffffffff
                assert (m.hl<<16|m.de)==want,(v,a,b,m.hl,m.de,want)
                assert cost==(cost37(a,b)+17 if i else cost33(a,b)+101),(v,a,b,cost)
                assert bytes(m.memory[0x7e00:0x7e04])==raw
                preserved(m);total+=cost
                # The original entry remains callable with the original sign/result.
                ordinary_product(m,s,a,b,True,True);ordinary+=1
        result[v]=dict(actual_call_sites=len(addresses),combined_caller_cases=len(values)*len(arguments),
                       instructions=instructions,tstates=total,ordinary_q14_boundary_cases=ordinary,
                       every_instruction_matches_timing_table=True,register_input_and_write_guards=True)
    return result


def domains(out):
    m,s=checked_machine(out/'pure-r37',True);n=0;hist=Counter();savings=Counter();paths=Counter()
    def check(a,b):
        nonlocal n
        cost=product(m,s,a,b);n+=1;hist[cost]+=1;savings[cost33(a,b)+84-cost]+=1
        hi,lo=parts(b);c=abs(a)
        if a<0:
            carry=(((c*hi)&65535)+((c*lo+16383)>>14))>65535
            paths[f'negative/high_{hi<0}/carry_{carry}/rounding_{bool(c*lo%16384)}']+=1
        else:paths[f'nonnegative/high_{hi<0}']+=1
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
                minimum_tstates=min(hist),maximum_tstates=max(hist),paths=dict(paths),
                saving_histogram=dict(sorted(savings.items())),minimum_saving=min(savings),maximum_saving=max(savings),
                exact_results_rounding_and_instruction_formulas=True,register_input_and_write_guards=True)


def source_identity(out):
    texts=[(out/v/'decoder.s').read_text() for v in VARIANTS]
    assert texts[0].split('_zx_speex_decode::',1)[0]==texts[1].split('_zx_speex_decode::',1)[0]
    assert (out/'pure-r36/filter.s').read_text()==(out/'pure-r37/filter.s').read_text()
    return dict(retained_decoder_prefix_source_unchanged=True,full_filter_assembly_unchanged=True)


def observe(out):
    archive=ROOT/'audiobook-beeper/speex-port/rounds/32'
    packed=gzip.decompress((archive/'observed-q14-operands.i16i32.gz').read_bytes())
    pairs=list(struct.iter_unpack('<hi',packed));prior=json.loads((archive/'q14-product-checks.json').read_text())['speech']
    assert sha(packed)==prior['operands_sha256'] and len(pairs)==93440
    reports=[];costs=[]
    for i,v in enumerate(VARIANTS):
        observed=[];label='_q14_negated' if i else 'mulq14'
        def observer(name,m):
            observed.append((m.hl-65536 if m.hl&32768 else m.hl,
                             int.from_bytes(m.memory[m.de:m.de+4],'little',signed=True)))
        with redirect_stdout(io.StringIO()):r=native(out,v+'-negated-q14-profile',out/v,profile=(label,),entry_observer=observer)
        assert observed==pairs
        plain=json.loads((out/v/'report.json').read_text())
        assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
        assert (out/(v+'-negated-q14-profile')/'out-times.u64.gz').read_bytes()==(out/v/'out-times.u64.gz').read_bytes()
        total=sum((cost37 if i else cost33)(a,b) for a,b in pairs)
        assert total==r['profile']['inclusive_tstates'][label]
        reports.append(r);costs.append(total+(0 if i else 84*len(pairs)))
    savings=[cost33(a,b)+84-cost37(a,b) for a,b in pairs];hist=Counter(savings)
    assert sum(savings)==costs[0]-costs[1]==reports[0]['total_tstates']-reports[1]['total_tstates']
    cumulative=[];total=0
    for i in range(0,len(savings),20):
        total+=sum(savings[i:i+20]);cumulative.append(total)
    times=[list(struct.iter_unpack('<Q',gzip.decompress((out/v/'out-times.u64.gz').read_bytes()))) for v in VARIANTS]
    assert len(times[0])==len(times[1])==186880
    for i,(a,b) in enumerate(zip(*times)):assert a[0]-b[0]==cumulative[i//40],i
    identity=source_identity(out)
    return dict(calls=len(pairs),unique_pairs=len(set(pairs)),operands_sha256=sha(packed),
                operand_archive='rounds/32/observed-q14-operands.i16i32.gz',every_operand_unchanged=True,
                old_q14_plus_negate_tstates=costs[0],new_negated_q14_tstates=costs[1],total_saving=sum(savings),
                old_full_tstates=reports[0]['total_tstates'],new_full_tstates=reports[1]['total_tstates'],
                saving_histogram=dict(sorted(hist.items())),regressed_calls=sum(n for t,n in hist.items() if t<0),
                isolated_costs_and_full_delta_reconcile=True,profile_preserves_every_uninstrumented_out=True,
                every_out_delta_matches_cumulative_saving=True,**identity,
                complete_pcm16_and_pcm8_samples=186880)


def main():
    out=ROOT/'build/speex-port';r=dict(caller_audits=caller_audits(out),domains=domains(out))
    print('Caller audits and domains pass:',r['domains']['q14_cases'],flush=True)
    r['speech']=observe(out);print('Speech:',r['speech'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r37','pure-r37')
    (out/'pure-r37/q14-negated-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
