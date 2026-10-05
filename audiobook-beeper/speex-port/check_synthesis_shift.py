"""Check exact synthesis shifts, all 32-bit rounding boundaries and port deltas."""
from collections import Counter
import gzip
import json
import struct
from check_primitives import machine,symbols
from check_inline_products import step,filter_calls
from check_constant_pitch import extra_stream
from verify import ROOT


VARIANTS=('pure-r29','pure-r30')


def signed(value,bits):
    return value-(1<<bits) if value&(1<<(bits-1)) else value


def setup(folder):
    m=machine(folder);s=symbols(folder)
    if '_synthesis_shift_start' in s:
        start=s['_synthesis_shift_start'];end=s['_synthesis_shift_end'];round_start=s['_synthesis_round_start']
    else:
        # Identify only within the actual filter entry/feedback prefix. Keep the
        # frozen baseline binary unchanged rather than adding labels to it.
        first=s['_zx_speex_filter'];last=s['_filter_feedback_start']
        data=bytes(m.memory[first:last]);pattern=bytes.fromhex('cb2bcb1ccb1d')*5
        assert data.count(pattern)==1;start=first+data.index(pattern);end=start+len(pattern)
        prefix=b'\x2a'+s['_zx_memory'].to_bytes(2,'little')+b'\x01\x00\x10'
        assert data.count(prefix)==1;round_start=first+data.index(prefix)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('shift write',hex(m.pc),hex(address),value))
    m.set_write_callback(bad);m.set_breakpoint(end)
    m.ix=0x1234;m.iy=0x5678;m.sp=0xbffe
    m.alt_af=0xabcd;m.alt_bc=0x9876;m.alt_de=0x4567;m.alt_hl=0xcafe
    return m,s,start,end,round_start


def preserved(m):
    assert (m.ix,m.iy,m.sp,m.alt_af,m.alt_bc,m.alt_de,m.alt_hl)==(0x1234,0x5678,0xbffe,0xabcd,0x9876,0x4567,0xcafe)


def run(m,start,end):
    m.pc=start;m.ticks_to_stop=1000
    while m.pc!=end:
        event=m.run();assert not(event&m._TICKS_LIMIT_HIT)
    return 1000-m.ticks_to_stop


def audit(m,start,end):
    m.pc=start;cost=0;count=0
    while m.pc!=end:cost+=step(m);count+=1
    return dict(tstates=cost,instructions=count,every_instruction_matches=True)


def arithmetic(folder,direct):
    m,s,start,end,round_start=setup(folder);cost=93 if direct else 120
    cases=0;m.bc=0x4567;m.d=0x89;hist=Counter()
    # Every upper word with low-byte boundaries; carry-in and other flags vary.
    for upper in range(65536):
        for low in (0,1,127,128,254,255):
            value=upper*256+low;m.e=value>>16;m.hl=value&65535;m.f=low
            assert run(m,start,end)==cost
            assert (m.e<<16|m.hl)==(signed(value,24)>>5)&0xffffff
            assert (m.bc,m.d)==(0x4567,0x89);preserved(m);cases+=1
    audits=[]
    for value in (0,1,31,32,255,256,0x7fffff,0x800000,0x80001f,0xffffdf,0xffffe0,0xffffff):
        m.e=value>>16;m.hl=value&65535;m.f=value&255
        r=audit(m,start,end);assert r['tstates']==cost;r['signed24_input']=signed(value,24);audits.append(r)
    # Every quotient boundary of the full signed32 rounded >>13 operation,
    # immediately before/at/after it. Explicit modulo32 matches Speex overflow.
    rounded_cases=0
    for quotient in range(-262144,262144):
        for delta in (-1,0,1):
            history=((quotient<<13)-4096+delta)&0xffffffff
            at=s['_zx_memory'];m.memory[at:at+4]=history.to_bytes(4,'little')
            elapsed=run(m,round_start,end);hist[elapsed]+=1
            want=signed((history+4096)&0xffffffff,32)>>13
            assert (m.e<<16|m.hl)==want&0xffffff,(history,want,m.e,m.hl)
            carry=(history&65535)>=0xf000
            assert elapsed==cost+81+carry and m.bc==4096
            preserved(m);rounded_cases+=1
    round_audits=[]
    for value in (0,0xefff,0xf000,0x7fffefef,0x7fffefff,0x7ffff000,0x80000000,0xffffefff,0xfffff000,0xffffffff):
        at=s['_zx_memory'];m.memory[at:at+4]=value.to_bytes(4,'little')
        r=audit(m,round_start,end);assert r['tstates']==cost+81+((value&65535)>=0xf000)
        r['history_uint32']=value;round_audits.append(r)
    return dict(isolated_cases=cases,isolated_tstates=cost,every_upper_word_covered=True,
                all_rounding_boundaries=True,rounding_boundary_cases=rounded_cases,
                rounding_tstates=dict(sorted(hist.items())),isolated_audits=audits,rounding_audits=round_audits,
                all_results_exact=True,all_cpu_writes_forbidden=True,register_contracts_preserved=True)


def stream_delta(out):
    reports=[json.loads((out/v/'report.json').read_text()) for v in VARIANTS]
    samples=reports[0]['samples'];assert all(r['complete'] and r['every_pcm16_exact'] and r['every_pcm8_exact'] for r in reports)
    assert reports[1]['samples']==samples
    assert reports[0]['total_tstates']-reports[1]['total_tstates']==27*samples
    traces=[struct.unpack('<'+'Q'*samples,gzip.decompress((out/v/'out-times.u64.gz').read_bytes())) for v in VARIANTS]
    assert all(old-new==27*(i+1) for i,(old,new) in enumerate(zip(*traces)))
    return dict(samples=samples,baseline_total_tstates=reports[0]['total_tstates'],total_tstates=reports[1]['total_tstates'],
                saving_per_sample=27,total_saving=27*samples,every_out_timestamp_delta_exact=True,
                binary_sha256=reports[1]['binary_sha256'])


def main():
    out=ROOT/'build/speex-port';rows={}
    for v in VARIANTS:
        row=arithmetic(out/v,v=='pure-r30');row['full_filter_contract']=filter_calls(out/v,True);rows[v]=row
        print(v,{k:x for k,x in row.items() if 'audits' not in k},flush=True)
    result=dict(variants=rows,speech=stream_delta(out),all_pitches=extra_stream(out/'pure-r30','pure-r30'))
    (out/'pure-r30/synthesis-shift-checks.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(result['speech'],flush=True)


if __name__=='__main__':main()
