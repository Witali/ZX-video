"""Full same-quota Fast/Maximum comparison and every added instruction cost."""
import argparse,json
from collections import Counter
from pathlib import Path
from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from measure_long_copy import ROOT,sha
from measure_fast_jumps import layout
from maximum_coroutine_native import execute
from native_block import execute as resident
from zx0.maximum import build as raw_build
from zx0.maximum_coroutine import build
from zx0.resumable import build as fast


def added_watch(profile):
    """Observe only new instructions; all costs come from the Z80 table.

    The raw Maximum core remains byte-for-byte the same instruction stream
    between these ranges. Replaying it separately makes the sum of added
    costs an independent whole-block delta proof, rather than a fitted model.
    """
    regions,labels,meta=profile;memory={at+i:value for at,blob in regions for i,value in enumerate(blob)}
    hits=Counter();watch={};rows=[]
    for lo,hi in meta['added_instruction_ranges']:
        pc=lo
        while pc<hi:
            op=memory[pc];sub=memory.get(pc+1)
            if op==0xdd:
                assert sub in (0x22,0x2a,0xbc,0xbd)
                size,t=(4,20) if sub in (0x22,0x2a) else (2,8)
            elif op==0xed:size,t=4 if sub in (0x43,0x4b,0x53,0x5b,0x73,0x7b) else 2,15 if sub in (0x42,0x52) else 20
            elif op in (0x01,0x11,0x21,0x31,0xc3,0xc2,0xda,0xcd,0x2a,0x32):
                size,t=3,17 if op==0xcd else 16 if op==0x2a else 13 if op==0x32 else 10
            elif op in (0x20,0x28,0x30,0x38):size,t=2,None
            elif op in (0x3e,0xfe):size,t=2,7
            elif op in (0xc5,0xd5,0xe5,0xf5):size,t=1,11
            elif op in (0xc1,0xd1,0xe1,0xf1,0xc9):size,t=1,10
            elif op==0xd0:size,t=1,None
            else:
                assert op in (0x08,0xd9,0x78,0x79,0x7a,0x7b,0xaf,0xb7,0xba,0xbb,0x76),hex(op)
                size,t=1,4
            code=bytes(memory[pc+i] for i in range(size));rows.append(dict(address=pc,code_hex=code.hex(),tstates=t))
            def observe(m,at=pc,opcode=op,fixed=t):
                if fixed is not None:cost=fixed
                elif opcode==0xd0:cost=5 if m.f&1 else 11
                else:
                    taken={0x20:not(m.f&0x40),0x28:bool(m.f&0x40),0x30:not(m.f&1),0x38:bool(m.f&1)}[opcode]
                    cost=12 if taken else 7
                hits[at,cost]+=1
            watch[pc]=observe;pc+=size
        assert pc==hi
    return watch,hits,rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--high-word',action='store_true');a=p.parse_args()
    if a.high_word:
        common=dict(prefix=0x2b00,prefix_limit=0x2d00,stack=0x2af0,output_base=0x3000)
        origin,moved=0x0800,0x0903;run_options=dict(source=0x0400,caller_stack=0x2ff0)
    else:common={};origin,moved=0x8000,0x9103;run_options={}
    before_profile=fast(core=origin,core_limit=origin+0x400,**common)
    candidates={cap:build(core=origin,prefix_cap=cap,**common) for cap in (31,63,127)}
    relocated={cap:build(core=moved,prefix_cap=cap,**common) for cap in candidates}
    raw_profiles={cap:raw_build(core=origin,prefix_cap=cap) for cap in candidates}
    frozen=json.loads((ROOT/'libraries/evidence/ten_percent_tuned_branches.json').read_text())['profiles']['zx0-coroutine']['blocks']
    frozen={r['case']:r for r in frozen};rows={cap:[] for cap in candidates}
    for name,payload,raw in high_word_samples() if a.high_word else samples():
        before=execute(before_profile,payload,raw,**run_options)
        if not a.high_word:
            assert before['tstates']==frozen[name]['baseline_tstates']
            assert sha(payload)==frozen[name]['payload_sha256'] and sha(raw)==frozen[name]['raw_sha256']
        for cap,profile in candidates.items():
            watch,hits,instructions=added_watch(profile)
            after=execute(profile,payload,raw,watch=watch,**run_options)
            irq=execute(profile,payload,raw,interrupts=True,**run_options)
            move=execute(relocated[cap],payload,raw,**run_options)
            assert after['output_cursors']==before['output_cursors']==move['output_cursors']==irq['output_cursors'],name
            assert after['finished_states']==before['finished_states']==move['finished_states']==irq['finished_states'],name
            assert after['tstates']==move['tstates']
            raw_cost=resident(raw_profiles[cap],payload,raw,source=run_options.get('source',0x2000),
                output=common.get('output_base',0xc000),caller_stack=run_options.get('caller_stack',0xbff0))['tstates']
            predicted=sum(t*n for (_,t),n in hits.items())
            assert after['tstates']-raw_cost==predicted,(name,cap,after['tstates']-raw_cost,predicted)
            delta=[y-x for x,y in zip(before['slices'],after['slices'])]
            rows[cap].append(dict(case=name,payload_bytes=len(payload),raw_bytes=len(raw),payload_sha256=sha(payload),raw_sha256=sha(raw),
                baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=sum(delta),
                raw_maximum_tstates=raw_cost,added_instruction_tstates=predicted,
                slices=len(delta),slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta),
                slower_slice_deltas=[dict(index=i,delta_tstates=t) for i,t in enumerate(delta) if t>0],
                output_cursors=after['output_cursors'],eof_states=after['finished_states'],same_fast_return_cursors=True,same_fast_eof_states=True,
                caller_stack_bytes=after['caller_stack_bytes'],private_stack_bytes=after['private_stack_bytes'],
                irq_caller_stack_bytes=irq['caller_stack_bytes'],irq_private_stack_bytes=irq['private_stack_bytes'],
                injected_interrupts=irq['injected_interrupts'],relocated_exact=True,exact=True,
                added_instruction_histogram=[dict(address=pc,tstates=t,count=n) for (pc,t),n in sorted(hits.items())]))
        if name in ('real-2-0','real-3-0'):print(name,'exact',flush=True)
    report=dict(date='2026-10-20',complete=True,release=False,baseline_revision='f5a0362c',raw_maximum_revision='6759dedf',
        high_word_supplement=a.high_word,physical_rom_disk_ula_publication=False,profiles={})
    for cap,profile in candidates.items():
        items=rows[cap];real=[r for r in items if r['case'].startswith('real-')]
        summary=dict(cases=len(items),real_blocks=len(real),baseline_tstates=sum(r['baseline_tstates'] for r in items),candidate_tstates=sum(r['candidate_tstates'] for r in items),
            real_baseline_tstates=sum(r['baseline_tstates'] for r in real),real_candidate_tstates=sum(r['candidate_tstates'] for r in real),
            slower_blocks=sum(r['delta_tstates']>0 for r in items),slower_real_blocks=sum(r['delta_tstates']>0 for r in real),
            slices=sum(r['slices'] for r in items),slower_slices=sum(r['slower_slices'] for r in items),maximum_slice_delta=max(r['largest_slice_delta'] for r in items))
        report['profiles'][str(cap)]=dict(layout=layout(profile),metadata=profile[2],added_instruction_listing=added_watch(profile)[2],summary=summary,blocks=items)
        print(cap,json.dumps(summary),flush=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
