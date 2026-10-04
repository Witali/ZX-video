"""Verify exact small signed feedback kernels, borrow chains and throughput."""
from collections import Counter
import argparse
from contextlib import redirect_stdout
import gzip
import io
import json
import random
import struct
from check_primitives import call
from check_inline_products import guarded,step,filter_calls
from check_constant_pitch import extra_stream
from verify import ROOT,native,sha

VARIANTS=('pure-r39','pure-r40')


def kind(n):
    if not n:return 'zero'
    if n<256:return 'small_positive'
    if n<4096:return 'top_zero'
    if n==65280:return 'minus_256'
    if n>65280:return 'small_negative'
    return 'general'


def cost(n,new):
    if not n:return 847
    if not new:return 2950 if n<4096 else 3624
    return dict(small_positive=2284,top_zero=2968,minus_256=3660,small_negative=2440,general=3642)[kind(n)]


def distribution(raw):
    ns=[(-y[0])&65535 for y in struct.iter_unpack('<h',raw)]
    return dict(samples=len(ns),reference_sha256=sha(raw),classes=dict(Counter(map(kind,ns))),
                predicted_saving=sum(cost(n,False)-cost(n,True) for n in ns))


def inspect_fixtures(out):
    rows={'speech':distribution((out/'reference.pcm16').read_bytes())}
    for name in ('silence','impulses','low-tone','high-tone','noise','level-jumps','six-bank-capacity','random-packets','all-pitches'):
        rows[name]=distribution((out/'checks'/name/'reference.pcm16').read_bytes())
    return rows


def feedback(out):
    rng=random.Random(3939)
    histories=[[0]*10,[0xffffffff]*10,[0x80000000,0x7fffffff]*5]
    histories += [[rng.getrandbits(32) for _ in range(10)] for _ in range(512)]
    coefficients=[[0]*10,[-32768,-32767,-8192,-257,-1,1,255,8192,32766,32767],
                  [rng.randrange(-32768,32768) for _ in range(10)]]
    audit_words={0,1,15,16,127,128,255,256,4095,4096,8191,32767,32768,65279,65280,65281,65408,65535}
    results={}
    for index,v in enumerate(VARIANTS):
        count=0;costs=Counter();audits=[]
        for coefficient in coefficients:
            m,s=guarded(out/v,True)
            m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coefficient)
            call(m,s['_prepare_coefficients'],budget=1000000)
            m.mark_addrs(0,65536,m.WRITE_MARK)
            m.unmark_addrs(s['_zx_memory'],40,m.WRITE_MARK)
            m.set_breakpoint(s['_filter_emit'])
            def reset(n,history):
                m.memory[s['_zx_memory']:s['_zx_memory']+40]=struct.pack('<10I',*history)
                m.hl=n;m.a=n>>8;m.sp=0xbffe;m.ix=0x1234;m.iy=0x5678
                m.alt_af=0x1234;m.alt_bc=0xabcd;m.alt_de=0x3456;m.alt_hl=0xcafe
                m.memory[s['_filter_saved_sp']:s['_filter_saved_sp']+2]=m.sp.to_bytes(2,'little')
                m.pc=s['_filter_feedback_start']
            def check_result(n,history):
                signed=n-65536 if n&32768 else n
                want=[(signed*c+(history[k+1] if k<9 else 0))&0xffffffff for k,c in enumerate(coefficient)]
                assert bytes(m.memory[s['_zx_memory']:s['_zx_memory']+40])==struct.pack('<10I',*want),(v,n)
                assert (m.sp,m.alt_af,m.alt_bc,m.alt_de,m.alt_hl)==(0xbffe,0x1234,0xabcd,0x3456,0xcafe)
                if not n:assert (m.ix,m.iy)==(0x1234,0x5678)
                if 0<n<4096:assert m.iy>>8==0x56
                if index and (0<n<256 or n>65280):assert m.iy==0x5678
            for n in range(65536):
                history=histories[n%len(histories)];reset(n,history);m.ticks_to_stop=10000
                while m.pc!=s['_filter_emit']:assert not(m.run()&m._TICKS_LIMIT_HIT)
                elapsed=10000-m.ticks_to_stop;assert elapsed==cost(n,bool(index)),(v,n,elapsed)
                check_result(n,history);costs[elapsed]+=1;count+=1
                if n in audit_words:
                    reset(n,history);total=0;instructions=0;borrowed=0
                    while m.pc!=s['_filter_emit']:
                        if 0x7200<=m.sp<0x7c00:borrowed+=1
                        total+=step(m);instructions+=1
                    assert total==elapsed;check_result(n,history)
                    audits.append(dict(n=n,kind=kind(n),tstates=total,instructions=instructions,
                                       instructions_with_table_sp=borrowed))
        results[v]=dict(feedback_cases=count,coefficient_arrays=len(coefficients),arbitrary_histories=len(histories),
                        every_16bit_feedback_word=True,cost_histogram=dict(sorted(costs.items())),audits=audits,
                        only_40_history_bytes_writable=True,real_sp_and_all_alternates_preserved=True,
                        every_instruction_matches_timing_table=True,exact_signed_products_and_modulo32_histories=True,
                        filter_contract=filter_calls(out/v,True))
    return results


def speech(out):
    raw=(out/'reference.pcm16').read_bytes();ns=[(-v[0])&65535 for v in struct.iter_unpack('<h',raw)]
    reports=[]
    for i,v in enumerate(VARIANTS):
        with redirect_stdout(io.StringIO()):
            r=native(out,v+'-small-feedback-profile',out/v,profile=('_zx_speex_filter',),
                     blocks={'feedback':('_filter_feedback_start','_filter_emit')})
        plain=json.loads((out/v/'report.json').read_text())
        assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
        assert (out/(v+'-small-feedback-profile')/'out-times.u64.gz').read_bytes()==(out/v/'out-times.u64.gz').read_bytes()
        block=r['profile']['inline_blocks']['feedback'];hist=Counter(cost(n,bool(i)) for n in ns)
        assert block['calls']==len(ns) and block['duration_histogram']==dict(sorted(hist.items()))
        assert block['total_tstates']==sum(t*c for t,c in hist.items());reports.append(r)
    savings=[cost(n,False)-cost(n,True) for n in ns]
    assert sum(savings)==reports[0]['total_tstates']-reports[1]['total_tstates']
    times=[list(struct.iter_unpack('<Q',gzip.decompress((out/v/'out-times.u64.gz').read_bytes()))) for v in VARIANTS]
    assert len(times[0])==len(times[1])==len(ns);total=0
    for i,(a,b) in enumerate(zip(*times)):
        total+=savings[i];assert a[0]-b[0]==total,i
    assert (out/'pure-r39/decoder.s').read_text()==(out/'pure-r40/decoder.s').read_text()
    return dict(**distribution(raw),old_feedback=reports[0]['profile']['inline_blocks']['feedback'],
                new_feedback=reports[1]['profile']['inline_blocks']['feedback'],total_saving=sum(savings),
                old_full_tstates=reports[0]['total_tstates'],new_full_tstates=reports[1]['total_tstates'],
                every_out_delta_matches_cumulative_saving=True,profile_preserves_all_uninstrumented_out=True,
                complete_pcm16_pcm8_exact=True,decoder_assembly_source_unchanged=True)


def reconcile_fixtures(out,r):
    reports=[]
    for v in VARIANTS:
        folder=out/v
        rows=json.loads((folder/'checks.json').read_text())['fixtures']
        rows['speech']=json.loads((folder/'report.json').read_text())
        rows['random-packets']=json.loads((folder/'unpaced-checks.json').read_text())['random_packets']
        extra='top-zero-checks.json' if v=='pure-r39' else 'small-feedback-checks.json'
        rows['all-pitches']=json.loads((folder/extra).read_text())['all_pitches']
        reports.append(rows)
    result={}
    for name,inspection in r['fixture_inspection'].items():
        old,new=(rows[name] for rows in reports)
        assert old['every_pcm16_exact'] and old['every_pcm8_exact'] and new['every_pcm16_exact'] and new['every_pcm8_exact']
        assert old['samples']==new['samples']==inspection['samples']
        actual=old['total_tstates']-new['total_tstates']
        assert actual==inspection['predicted_saving']
        result[name]=dict(samples=new['samples'],old_tstates=old['total_tstates'],new_tstates=new['total_tstates'],
                          saving_tstates=actual,regressed=actual<0,exact_and_matches_class_prediction=True)
    return result


def negate_domain(out):
    from check_primitives import machine,symbols
    m=machine(out/'pure-r40');s=symbols(out/'pure-r40')
    m.mark_addrs(0,65536,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('negate writes memory',address,value))
    m.set_write_callback(bad);m.set_breakpoint(s['_feedback40_negate_end'])
    cases=0;audits=0;instructions=0
    for high in (0,1,0x7fff,0x8000,0xffff):
        for low in range(65536):
            m.bc=high;m.de=low;m.hl=0xabcd;m.sp=0x7250;m.ix=0x1234;m.iy=0x5678
            m.alt_af=0x9876;m.alt_bc=0x5432;m.alt_de=0xcafe;m.alt_hl=0xfedc
            m.pc=s['_feedback40_negate_start'];m.ticks_to_stop=1000
            while m.pc!=s['_feedback40_negate_end']:assert not(m.run()&m._TICKS_LIMIT_HIT)
            assert 1000-m.ticks_to_stop==54
            assert (m.bc<<16|m.de)==(-(high<<16|low))&0xffffffff
            assert (m.hl,m.sp,m.ix,m.iy)==(0xabcd,0x7250,0x1234,0x5678)
            assert (m.alt_af,m.alt_bc,m.alt_de,m.alt_hl)==(0x9876,0x5432,0xcafe,0xfedc)
            cases+=1
            if low in (0,1,255,256,32767,32768,65534,65535):
                m.bc=high;m.de=low;m.pc=s['_feedback40_negate_start'];t=0
                while m.pc!=s['_feedback40_negate_end']:t+=step(m);instructions+=1
                assert t==54 and (m.bc<<16|m.de)==(-(high<<16|low))&0xffffffff;audits+=1
    return dict(cases=cases,tstates=54,instruction_audits=audits,instructions=instructions,
                all_low_words_against_high_words=5,every_borrow_and_instruction_exact=True,
                all_memory_writes_forbidden=True,hl_sp_indexes_and_alternates_preserved=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reconcile-fixtures',action='store_true')
    args=parser.parse_args();out=ROOT/'build/speex-port';target=out/'pure-r40/small-feedback-checks.json'
    if args.reconcile_fixtures:
        r=json.loads(target.read_text());r['complete_fixture_cost_proofs']=reconcile_fixtures(out,r)
        target.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('All full fixture costs match their class predictions');return
    r=dict(fixture_inspection=inspect_fixtures(out))
    print('Input classes:',r['fixture_inspection']['speech'],flush=True)
    r['feedback']=feedback(out);print('All feedback words and arbitrary-state filter calls pass',flush=True)
    r['negate_domain']=negate_domain(out);print('Borrow-chain domain passes',flush=True)
    r['speech']=speech(out);print('Speech:',r['speech'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r40','pure-r40')
    (out/'pure-r40/small-feedback-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
