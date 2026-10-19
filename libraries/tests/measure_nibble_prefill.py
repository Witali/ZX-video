"""Pre-normalized LZSA2 low-nibble cache: complete profiles and legal EOF cases."""
import argparse
import json
from pathlib import Path
from measure_long_copy import ROOT, samples, sha
from measure_fast_jumps import layout, summarize
from native_block import execute
from lzsa.block import build as block
from lzsa.resumable import build as coroutine
from lzsa.native import execute as resume
from z80 import Z80Machine


def primitive(profile):
    regions, labels, metadata = profile
    rows = metadata['instruction_listing']
    records = []
    for name in ('LiteralNibble', 'Offset13Nibble', 'Offset5Nibble', 'MatchNibble'):
        branch = next(row for row in rows if row['instruction'] == 'JR '+name)
        start = branch['address']-1
        stop = labels[name]+(0 if metadata.get('nibble_prefill') else 2)
        for value in range(256):
            m=Z80Machine();m.memory[:]=b'\xa5'*65536
            for at,data in regions:m.set_memory_block(at,data)
            m.memory[0x2000]=value
            m.hl=0x2000;m.af=0x55ff;m.alt_af=0x99ff
            m.set_breakpoint(stop)
            costs=[]
            for phase in ('refill', 'cached'):
                m.af=0x55ff;m.pc=start;m.ticks_to_stop=1000
                while m.pc!=stop:
                    assert not m.run()&m._TICKS_LIMIT_HIT
                costs.append(1000-m.ticks_to_stop)
                expected=(value>>4 if phase=='refill' else value&15)|0xf0
                expected_flags=0x80|(expected&0x28)|(4 if expected.bit_count()%2==0 else 0)
                assert m.a==expected and m.hl==0x2001 and m.f==expected_flags
                assert bool(m.alt_af&1)==(phase=='cached')
            records.append(dict(site=name,byte=value,refill_tstates=costs[0],cached_tstates=costs[1]))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=dict(date='2026-10-19',baseline_revision='674a1fc8',goal_baseline='f5a0362c',complete=False,
        release=False,goal_achieved=False,scope=__doc__,profiles={},primitive={})
    report['primitive']['before']=primitive(block())
    report['primitive']['after']=primitive(block(nibble_prefill=True))
    for old,new in zip(report['primitive']['before'],report['primitive']['after']):
        assert (old['refill_tstates'],old['cached_tstates'])==(62,23)
        assert (new['refill_tstates'],new['cached_tstates'])==(65,16)
    cases=list(samples())+[
        ('single-nibble-eof-A',bytes.fromhex('ef41f0e8'),b'A'),
        ('single-nibble-eof-empty',bytes.fromhex('e7f0e8'),b'')]
    for resident in (True,False):
        for fast,tuned,extended in ((False,False,False),(True,False,False),(True,True,False),(True,True,True)):
            options=dict(fast_jumps=fast,branch_tuned=tuned,long_copy=extended,near_literals=extended)
            if not resident:options['restore_compare']=extended
            builder=block if resident else coroutine
            old=builder(core=0x8000,core_limit=0x8400,**options)
            new=builder(core=0x8000,core_limit=0x8400,nibble_prefill=True,**options)
            moved=builder(core=0x9103,core_limit=0x9500,nibble_prefill=True,**options)
            assert new[2]['code_bytes']==old[2]['code_bytes']+4
            rows=[]
            for case,payload,raw in cases:
                def run(profile,irq=False):
                    return execute(profile,payload,raw,interrupts=irq) if resident else resume(*profile,payload,raw,source=0x2000,interrupts=irq)
                before,after,irq,relocated=run(old),run(new),run(new,True),run(moved)
                assert after['tstates']==relocated['tstates']
                row=dict(case=case,payload_bytes=len(payload),raw_bytes=len(raw),payload_sha256=sha(payload),raw_sha256=sha(raw),
                    baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=after['tstates']-before['tstates'],
                    injected_interrupts=irq['injected_interrupts'],exact=True,relocated_exact=True)
                if resident:
                    assert before['stack_bytes']==after['stack_bytes'];row['stack_bytes']=after['stack_bytes']
                else:
                    assert len(before['slices'])==len(after['slices'])
                    delta=[b-a for a,b in zip(before['slices'],after['slices'])]
                    row.update(slices=len(delta),slower_slices=sum(t>0 for t in delta),largest_slice_delta=max(delta))
                rows.append(row)
            name=('block' if resident else 'coroutine')+f'-fast{fast}-tuned{tuned}-extended{extended}'
            summary=summarize(rows)
            report['profiles'][name]=dict(options=options,baseline=layout(old),candidate=layout(new),summary=summary,blocks=rows)
            print(name,json.dumps(summary),'code',old[2]['code_bytes'],'->',new[2]['code_bytes'],flush=True)
    report['complete']=True
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
