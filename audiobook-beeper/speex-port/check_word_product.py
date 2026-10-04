"""Compare exact signed word products, observed operands and instruction costs."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import struct
from check_primitives import machine,symbols,call
from check_inline_products import step
from check_constant_pitch import extra_stream
from verify import ROOT,sha


VARIANTS=('pure-r30','pure-r31')


def u8_cost(a,general=True):
    if not a:
        assert general
        return 29
    bits=a.bit_length()
    return (16 if general else 0)+11*(8-bits)+34+27*(bits-1)+13*(a.bit_count()-1)+10


def word_cost(a,b,new):
    if not a:return 50
    if not b:return 60
    # Shared entry/sign normalization and byte-path dispatch, including RET.
    total=35+28+(39 if a<0 else 20)+(39 if b<0 else 20)
    tail=89 if (a<0)!=(b<0) else 28
    x,y=abs(a),abs(b)
    if x<256:total+=20;byte=True
    elif y<256:total+=34;x,y=y,x;byte=True
    else:total+=35;byte=False
    if new:
        return total+tail+(46+u8_cost(x,False) if byte else 114+u8_cost(x&255)+u8_cost(x>>8,False))
    # Simulate only carry decisions in the old 32-bit shift/add recurrence.
    # Each zero bit costs 39 T, each one 57 T plus one T if low ADD carries.
    acc=x<<(24 if byte else 16);total+=31 if byte else 18
    for _ in range(8 if byte else 16):
        bit=acc>>31;acc=(acc<<1)&0xffffffff
        if bit:
            total+=57+((acc&65535)+y>65535);acc=(acc+y)&0xffffffff
        else:total+=39
    assert acc==x*y
    return total+12+tail


def guarded(folder):
    m=machine(folder);s=symbols(folder)
    first=s['_zx_mul_table'];data=bytes(m.memory[first:s['_zx_mul8']])
    pattern=bytes.fromhex('7caae68032');assert data.count(pattern)==1
    offset=data.index(pattern)+len(pattern);sign=int.from_bytes(data[offset:offset+2],'little')
    m.mark_addrs(0,65536,m.WRITE_MARK);m.unmark_addrs(0xbf00,256,m.WRITE_MARK);m.unmark_addrs(sign,1,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('word product write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad)
    m.alt_af=0x1234;m.alt_bc=0xabcd;m.alt_de=0x3456;m.alt_hl=0x5678;m.ix=0xcafe;m.iy=0xdead
    return m,s


def preserved(m):
    assert (m.alt_af,m.alt_bc,m.alt_de,m.alt_hl,m.ix,m.iy,m.sp)==(0x1234,0xabcd,0x3456,0x5678,0xcafe,0xdead,0xbffe)


def product(m,s,a,b,new):
    cost=call(m,s['_zx_mul_table'],hl=a&65535,de=b&65535)
    assert (m.hl<<16|m.de)==(a*b)&0xffffffff,(a,b,m.hl,m.de)
    assert cost==word_cost(a,b,new),(a,b,cost,word_cost(a,b,new))
    preserved(m)
    return cost


def audits(out):
    values=(-32768,-32767,-257,-256,-255,-1,0,1,2,127,128,255,256,257,16384,32767)
    result={}
    for v in VARIANTS:
        m,s=guarded(out/v);total=0;instructions=0;hist=Counter()
        for a in values:
            for b in values:
                m.hl=a&65535;m.de=b&65535;m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=s['_zx_mul_table'];cost=0
                while m.pc!=0x7f00:cost+=step(m);instructions+=1
                assert cost==word_cost(a,b,v=='pure-r31')
                assert (m.hl<<16|m.de)==(a*b)&0xffffffff
                preserved(m);hist[cost]+=1;total+=1
        result[v]=dict(cases=total,instructions=instructions,tstates=dict(sorted(hist.items())),all_instruction_costs_and_results_exact=True)
    return result


def observe(out):
    from verify import native
    reports=[];all_pairs=[];old=json.loads((out/'pure-r30/report.json').read_text())
    for v in VARIANTS:
        pairs=[]
        def observer(name,m):pairs.append((m.hl-65536 if m.hl&32768 else m.hl,m.de-65536 if m.de&32768 else m.de))
        with redirect_stdout(io.StringIO()):r=native(out,v+'-word-profile',out/v,profile=('_zx_mul_table',),entry_observer=observer)
        reports.append(r);all_pairs.append(pairs)
    assert all_pairs[0]==all_pairs[1]
    assert reports[0]['total_tstates']==old['total_tstates'] and reports[0]['binary_sha256']==old['binary_sha256']
    assert (out/'pure-r30/out-times.u64.gz').read_bytes()==(out/'pure-r30-word-profile/out-times.u64.gz').read_bytes()
    counts=Counter(all_pairs[0]);totals=[];rows=[]
    for i,v in enumerate(VARIANTS):
        m,s=guarded(out/v);total=0;hist=Counter()
        for (a,b),n in counts.items():
            cost=product(m,s,a,b,i==1);total+=cost*n;hist[cost]+=n
        assert total==reports[i]['profile']['inclusive_tstates']['_zx_mul_table']
        totals.append(total);rows.append(dict(variant=v,product_tstates=total,cost_histogram=dict(sorted(hist.items())),
                                           full_tstates=reports[i]['total_tstates'],binary_sha256=reports[i]['binary_sha256']))
    assert reports[0]['total_tstates']-reports[1]['total_tstates']==totals[0]-totals[1]
    packed=b''.join(struct.pack('<hh',*p) for p in all_pairs[0])
    (out/'pure-r31/observed-word-operands.i16.gz').write_bytes(gzip.compress(packed,mtime=0))
    kinds=Counter('zero' if not a or not b else 'byte' if min(abs(a),abs(b))<256 else 'word' for a,b in all_pairs[0])
    return dict(calls=len(all_pairs[0]),unique_operand_pairs=len(counts),operands_sha256=sha(packed),operand_classes=dict(kinds),
                every_operand_unchanged=True,baseline_every_out_unchanged=True,isolated_cost_sum_equals_profile=True,
                complete_total_delta_reconciles=True,total_saving=totals[0]-totals[1],variants=rows,
                samples=reports[1]['samples'],every_pcm16_and_pcm8_exact=True)


def domains(out):
    m,s=guarded(out/'pure-r31');hist=Counter();cases=0
    for byte in range(256):
        expected=u8_cost(byte);m.bc=0x789a
        for word in range(65536):
            cost=call(m,s['_word31_u8'],a=byte,de=word)
            assert (m.a<<16|m.hl)==byte*word
            assert cost==expected and (m.bc,m.de)==(0x789a,word)
            preserved(m);cases+=1
        hist[expected]+=65536
        if byte%64==63:print('Unsigned byte/word domain:',byte+1,'of 256 multipliers passed',flush=True)
    # Exercise the alternate entry and all signed words in both argument orders.
    nonzero=0
    for byte in range(1,256):
        for word in (0,1,255,256,32767,32768,65535):
            cost=call(m,s['_word31_u8_nonzero'],a=byte,de=word)
            assert (m.a<<16|m.hl)==byte*word and cost==u8_cost(byte,False)
            assert m.de==word;preserved(m);nonzero+=1
    fixed=(-32768,-32767,-16384,-257,-256,-255,-1,0,1,2,127,128,255,256,257,16384,32767)
    signed_cases=0;word_hist=Counter()
    for a in fixed:
        for b in range(-32768,32768):
            for left,right in ((a,b),(b,a)):
                cost=product(m,s,left,right,True);word_hist[cost]+=1;signed_cases+=1
        print('Signed word domain in both orders:',a,'passed',flush=True)
    return dict(unsigned8x16_products=cases,unsigned_cost_histogram=dict(sorted(hist.items())),
                nonzero_entry_cases=nonzero,signed16_products=signed_cases,signed_cost_histogram=dict(sorted(word_hist.items())),
                all_exact_with_instruction_formula=True,all_register_contracts_preserved=True,all_writes_guarded=True)


def timing_bound():
    """Bound every nonzero signed16 input pair by ignoring old add carries."""
    minima={};counts={}
    for byte in (True,False):
        savings=[]
        for x in (range(1,256) if byte else range(256,32769)):
            steps=8 if byte else 16;pop=x.bit_count()
            old=(31 if byte else 18)+12+39*(steps-pop)+57*pop
            new=46+u8_cost(x,False) if byte else 114+u8_cost(x&255)+u8_cost(x>>8,False)
            savings.append(old-new)
        name='byte' if byte else 'word'
        minima[name]=min(savings);counts[name]=len(savings)
    assert minima==dict(byte=94,word=110)
    return dict(normalized_magnitudes_checked=counts,minimum_nonzero_saving_tstates=minima,
                zero_paths_unchanged=True,old_low_word_carry_can_only_increase_saving=True,
                common_entry_sign_and_dispatch_costs_cancel=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--quick',action='store_true');a=p.parse_args()
    out=ROOT/'build/speex-port';r=dict(audits=audits(out),speech=observe(out),timing_lower_bound=timing_bound())
    print({k:v for k,v in r['speech'].items() if k!='variants'},flush=True)
    for row in r['speech']['variants']:print({k:v for k,v in row.items() if k!='cost_histogram'},flush=True)
    if not a.quick:r['domains']=domains(out);r['all_pitches']=extra_stream(out/'pure-r31','pure-r31')
    (out/'pure-r31/word-product-checks.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')


if __name__=='__main__':main()
