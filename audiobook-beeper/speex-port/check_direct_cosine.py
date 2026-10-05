"""Verify direct cosine lookup, exact P13 fallback, all angles and playback costs."""
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import struct
from check_primitives import call
from check_inline_products import step
from check_word_product import guarded as word_guarded,preserved,word_cost
from check_constant_pitch import extra_stream
from make_decoder import cos_int
from verify import ROOT,native,sha

VARIANTS=('pure-r35','pure-r36')


def fold(x):return x if x<12868 else 25736-x


def old_cost(x):
    n=fold(x)&15;p=n//2
    return (356 if not p else 346+117*p)+68*(n&1)+61*(x>=12868)


def p13_cost(a,b):return 132+word_cost(a,b,True)+((a*b)&65535>=61440)


def p13(a,b):return (a*b+4096)>>13


def new_cost(x):
    if x%4==0:return 177 if x<12868 else 237
    y=fold(x);x2=p13(y,y);t=p13(x2,-10);u=p13(t+340,x2)
    return (324 if x<12868 else 384)+sum(p13_cost(a,b) for a,b in ((y,y),(x2,-10),(t+340,x2),(u-4096,x2)))


def guarded(folder):
    m,s=word_guarded(folder);scratch=s['_q14_scratch_end']
    if '_cos36_x2' in s:assert s['_cos36_x2']==scratch
    m.unmark_addrs(scratch,2,m.WRITE_MARK)
    return m,s


def check(m,s,x,new,audit=False):
    if audit:
        m.hl=x;m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=s['cosine'];cost=0;count=0
        while m.pc!=0x7f00:cost+=step(m);count+=1
    else:cost=call(m,s['cosine'],hl=x);count=0
    want=cos_int(x) if x<12868 else -cos_int(25736-x)
    assert m.de==want&65535,(x,m.de,want)
    expected=new_cost(x) if new else old_cost(x)
    assert cost==expected,(x,cost,expected)
    preserved(m)
    return cost,count


def domains(out):
    result={};savings=Counter()
    for i,v in enumerate(VARIANTS):
        m,s=guarded(out/v);hist=Counter();kind=Counter()
        for x in range(25737):
            cost,_=check(m,s,x,i==1);hist[cost]+=1;kind['aligned' if x%4==0 else 'unaligned']+=1
            if i:savings[old_cost(x)-cost]+=1
        result[v]=dict(angles=25737,input_classes=dict(kind),cost_histogram=dict(sorted(hist.items())),
                       full_results_and_instruction_formulas_exact=True,register_contracts_and_writes_guarded=True)
    result['saving_range']=dict(minimum=min(savings),maximum=max(savings),
                                aligned_inputs_always_faster=all(new_cost(x)<old_cost(x) for x in range(0,25737,4)))
    m,s=guarded(out/'pure-r36');cases=0;costs=Counter()
    for b in (-32768,-32767,-4096,-10,-1,0,1,340,8192,16384,32767):
        for a in range(-32768,32768):
            cost=call(m,s['_cos36_p13'],hl=a&65535,de=b&65535)
            assert m.hl==p13(a,b)&65535 and cost==p13_cost(a,b),(a,b,m.hl,cost)
            preserved(m);costs[cost]+=1;cases+=1
    result['p13']=dict(cases=cases,every_signed_word_against_constants=11,minimum_tstates=min(costs),maximum_tstates=max(costs),
                       rounded_low16_result_and_cost_exact=True,register_contracts_and_writes_guarded=True)
    return result


def audits(out):
    values=sorted(set(range(16))|set(range(4096,4112))|set(range(8192,8208))|set(range(12860,12877))|set(range(25720,25737)))
    result={}
    for i,v in enumerate(VARIANTS):
        m,s=guarded(out/v);count=0;total=0
        for x in values:
            cost,n=check(m,s,x,i==1,True);count+=n;total+=cost
        result[v]=dict(cases=len(values),instructions=count,tstates=total,every_instruction_matches_table=True)
    return result


def observe(out):
    arrays=[];reports=[]
    for v in VARIANTS:
        angles=[]
        def observer(name,m):angles.append(m.hl)
        with redirect_stdout(io.StringIO()):r=native(out,v+'-cosine-profile',out/v,profile=('cosine',),entry_observer=observer)
        plain=json.loads((out/v/'report.json').read_text())
        assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
        assert (out/(v+'-cosine-profile')/'out-times.u64.gz').read_bytes()==(out/v/'out-times.u64.gz').read_bytes()
        arrays.append(angles);reports.append(r)
    assert arrays[0]==arrays[1];angles=arrays[0];assert len(angles)==46720
    old=sum(map(old_cost,angles));new=sum(map(new_cost,angles))
    assert old==reports[0]['profile']['inclusive_tstates']['cosine']
    assert new==reports[1]['profile']['inclusive_tstates']['cosine']
    saving=old-new;assert saving==reports[0]['total_tstates']-reports[1]['total_tstates']
    cumulative=[];total=0
    for i in range(0,len(angles),10):
        total+=sum(old_cost(x)-new_cost(x) for x in angles[i:i+10]);cumulative.append(total)
    times=[list(struct.iter_unpack('<Q',gzip.decompress((out/v/'out-times.u64.gz').read_bytes()))) for v in VARIANTS]
    assert len(times[0])==len(times[1])==186880
    for i,(a,b) in enumerate(zip(*times)):assert a[0]-b[0]==cumulative[i//40],i
    packed=struct.pack('<'+'H'*len(angles),*angles)
    (out/'pure-r36/observed-cosine-angles.u16.gz').write_bytes(gzip.compress(packed,mtime=0))
    return dict(calls=len(angles),unique_angles=len(set(angles)),residues_mod4=dict(Counter(x%4 for x in angles)),
                angle_bytes_sha256=sha(packed),old_cosine_tstates=old,new_cosine_tstates=new,total_saving=saving,
                old_full_tstates=reports[0]['total_tstates'],new_full_tstates=reports[1]['total_tstates'],
                every_angle_unchanged=True,profile_preserves_every_out=True,every_out_delta_matches_cumulative_cosine_saving=True,
                isolated_cost_formulas_and_full_delta_reconcile=True,complete_pcm16_and_pcm8_samples=186880)


def random_probe(out):
    angles=[]
    def observer(name,m):angles.append(m.hl)
    with redirect_stdout(io.StringIO()):
        r=native(out/'checks/random-packets','pure-r36-cosine-profile',out/'pure-r36',profile=('cosine',),entry_observer=observer)
    old=json.loads((out/'pure-r35/unpaced-checks.json').read_text())['random_packets']
    saving=sum(old_cost(x)-new_cost(x) for x in angles)
    assert old['total_tstates']-r['total_tstates']==saving
    return dict(calls=len(angles),residues_mod4=dict(Counter(x%4 for x in angles)),total_saving=saving,
                total_tstates=r['total_tstates'],complete_pcm16_and_pcm8_samples=r['samples'],
                every_pcm16_exact=r['every_pcm16_exact'],every_pcm8_exact=r['every_pcm8_exact'],
                exact_fallback_exercised=any(x%4 for x in angles),full_saving_matches_call_costs=True)


def packing_analysis():
    """Reproduce the host-only range inspection used to select one candidate."""
    values=[cos_int(x) for x in range(12869)]
    spans={}
    for size in (4,8,16):
        counts=Counter(max(values[i:i+size])-min(values[i:i+size]) for i in range(0,len(values),size))
        spans[size]=dict(span_histogram=dict(sorted(counts.items())),blocks_exceeding_four_bits=sum(n for span,n in counts.items() if span>15))
    return dict(adjacent_delta_histogram=dict(sorted(Counter(b-a for a,b in zip(values,values[1:])).items())),
                block_span_analysis=spans,selected_word_table_entries=3218,selected_word_table_bytes=6436,
                previous_packed_bytes=8050,removed_pair_sum_bytes=256,static_byte_saving=1870,
                scope='Host-only table-layout inspection; no other native candidate was built.')


def main():
    out=ROOT/'build/speex-port';r=dict(packing_analysis=packing_analysis(),domains=domains(out),audits=audits(out))
    print('All angles and P13 domains passed',r['domains']['p13'],flush=True)
    r['speech']=observe(out);r['random_packets']=random_probe(out)
    print('Speech:',r['speech'],flush=True);print('Random packets:',r['random_packets'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r36','pure-r36')
    (out/'pure-r36/direct-cosine-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
