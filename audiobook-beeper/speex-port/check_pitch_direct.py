"""Check direct A:HL pitch accumulation and every mode-3 pitch/book combination."""
from collections import Counter
import json
import random
import struct
from check_primitives import machine,symbols
from check_pitch_accumulator import run as run_sum,audit as audit_sum
from check_pitch_paths import run,audit
from constant_pitch import gains
from verify import ROOT


VARIANTS=('pure-r28','pure-r29')


def guarded(folder):
    m=machine(folder);s=symbols(folder)
    m.mark_addrs(0,65536,m.WRITE_MARK);m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('pitch write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad)
    return m,s


def additions(out):
    rng=random.Random(2929)
    edges=[0,1,127,128,255,256,32767,32768,65535,65536,0x7fffff,0x800000,0xffffff]
    pairs=[(a,b) for a in edges for b in edges]
    pairs += [((((low*31>>8)&255)<<16)|low,((low>>8)^255)<<16|((low*257+17)&65535)) for low in range(65536)]
    pairs += [(rng.randrange(1<<24),rng.randrange(1<<24)) for _ in range(1024)]
    results={}
    for variant in VARIANTS:
        m,s=guarded(out/variant);direct=variant=='pure-r29';expected=48 if direct else 52
        m.sp=0xbffe;m.ix=0x1234;m.iy=0x5678;m.alt_af=0xcafe
        for tap in range(3):m.set_breakpoint(s[f'_pitch_add_{tap}_end'])
        audits=[]
        for tap in range(3):
            start=s[f'_pitch_add_{tap}_start'];end=s[f'_pitch_add_{tap}_end']
            for old,product in pairs:
                if direct:m.hl=product&65535;m.a=product>>16
                else:m.de=product&65535;m.hl=(product>>16)|(0xff00 if product&0x800000 else 0)
                m.alt_hl=old&65535;m.alt_c=old>>16
                assert run_sum(m,start,end)==expected
                assert (m.alt_c<<16|m.alt_hl)==(old+product)&0xffffff
                assert (m.sp,m.ix,m.iy,m.alt_af)==(0xbffe,0x1234,0x5678,0xcafe)
            r=audit_sum(m,start,end);assert r['tstates']==expected;audits.append(r)
        results[variant]=dict(cases=len(pairs)*3,all_low_words_covered=True,exact_modulo24=True,
                              tstates=expected,audits=audits,sp_ix_iy_alt_af_preserved=True,writes_guarded=True)
    return results


def history_paths(out):
    cpus=[];syms=[];reads=[[],[]];ready=[]
    for i,variant in enumerate(VARIANTS):
        m,s=guarded(out/variant);cpus.append(m);syms.append(s)
        m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
        m.mark_addrs(0xc000,16384,m.READ_MARK)
        def read(address,cpu=m,trace=reads[i]):trace.append(address);return cpu.memory[address]
        m.set_read_callback(read)
        ends={s['_pitch_flush_end'],s['_pitch27_fast_sum_end']}
        ready.append({s['_pitch27_general_ready'],s['_pitch27_fast_ready']})
        for address in ends|ready[-1]:m.set_breakpoint(address)
    plans=[json.loads((out/v/'constant-pitch-plan.json').read_text()) for v in VARIANTS]
    costs=[{r['gain']:r['tstates_including_ret'] for r in p['routines']} for p in plans]
    book=gains();rng=random.Random(2927);base=0xd400;cases=0;histogram=Counter();audits=[]
    for book_index in range(32):
        triple=book[3*book_index:3*book_index+3]
        history=[rng.randrange(-32768,32768) for _ in range(184)]
        history[:8]=[-32768,-32767,-1,0,1,255,256,32767]
        for m,s in zip(cpus,syms):
            m.memory[base-368:base]=struct.pack('<184h',*history)
            at=s['_pitch_gain_targets']+6*book_index
            m.memory[s['_pitch27_gains']:s['_pitch27_gains']+6]=m.memory[at:at+6]
        for pitch in range(17,145):
            for i,(m,s) in enumerate(zip(cpus,syms)):
                m.memory[s['_pitch27_period']]=pitch
                m.memory[s['_pitch27_exc_ptr']:s['_pitch27_exc_ptr']+2]=base.to_bytes(2,'little')
                m.sp=0xbffe;m.ix=0x1234;m.iy=0x5678;m.alt_af=0xcafe
                assert run(m,s['_pitch27_setup'],ready[i])==(128 if pitch>=41 else 30)
            for j in range(40):
                want=0;addresses=[];saving=0
                for tap in range(3):
                    at=j-(pitch+1-tap)
                    if at>=0:at-=pitch
                    if at<0:
                        gain=triple[2-tap];want+=gain*history[184+at]
                        saving+=costs[0][gain]-costs[1][gain]+4
                        addresses += [base+2*at,base+2*at+1]
                actual=[]
                for i,(m,s) in enumerate(zip(cpus,syms)):
                    m.memory[s['_pitch27_sample_index']]=j
                    m.memory[s['_pitch27_exc_ptr']:s['_pitch27_exc_ptr']+2]=(base+2*j).to_bytes(2,'little')
                    start=s['_pitch27_fast_sum_start'] if pitch>=41 else s['_pitch_init_start']
                    end=s['_pitch27_fast_sum_end'] if pitch>=41 else s['_pitch_flush_end']
                    before_ix=m.ix;reads[i].clear();actual.append(run(m,start,{end}))
                    at=s['_pitch_sum_state']
                    assert int.from_bytes(m.memory[at:at+3],'little')==want&0xffffff,(i,book_index,pitch,j)
                    assert reads[i]==addresses,(i,book_index,pitch,j,reads[i],addresses)
                    assert (m.sp,m.iy,m.alt_af)==(0xbffe,0x5678,0xcafe)
                    assert m.ix==(base-2*(pitch+1)+2*(j+1) if pitch>=41 else 0x1234)
                    if book_index in (0,15,31) and pitch in (17,40,41,144) and j in (0,39):
                        m.ix=before_ix;reads[i].clear();r=audit(m,start,end)
                        assert r['tstates']==actual[-1] and reads[i]==addresses
                        r.update(variant=VARIANTS[i],book_index=book_index,pitch=pitch,sample=j);audits.append(r)
                assert actual[0]-actual[1]==saving,(book_index,pitch,j,actual,saving)
                histogram[saving]+=1;cases+=1
    return dict(variants=VARIANTS,cases_per_variant=cases,book_triples=32,pitch_values=128,
                every_history_address_and_modulo24_sum_exact=True,every_delta_matches_formula=True,
                sp_iy_alt_af_preserved=True,ix_cursor_exact=True,writes_guarded=True,
                sum_saving_histogram=dict(sorted(histogram.items())),instruction_audits=audits)


def main():
    out=ROOT/'build/speex-port';r=dict(additions=additions(out),history_paths=history_paths(out))
    (out/'pure-r29/direct-pitch-checks.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print({v:{k:x for k,x in row.items() if k!='audits'} for v,row in r['additions'].items()},flush=True)
    print({k:x for k,x in r['history_paths'].items() if k!='instruction_audits'},flush=True)


if __name__=='__main__':main()
