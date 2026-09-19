"""Bound CPU-only lookahead time at every copy boundary in the saved movie.

Execute every complete block and record copy-entry times. A quota can end
only at the next copy boundary or EOF. Target-dependent fast comparisons
can add at most 32 T per copied run relative to this full-block trace.
Add 308 T for the slowest resume, 189 T for the stopping comparison/yield,
and 17 T for its caller CALL. Source decoding/refills/copies/paging are
measured, not estimated. No ULA/ROM/disk/IRQ cost is claimed by this bound.
The bound is specific to this verified stream and ring placement.
"""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

import banked_zx0
from benchmark_banked_zx0 import Harness,STACK,STOP
from benchmark_context_huffman import word
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

RESUME = 308  # sync 100 + CALL 17 + comparison 91 + stack restoration 90 + JP 10.
STOPPING = 189


def bound_trace(trace,quota):
    positions = [r['produced'] for r in trace]; result=[]
    if positions[0] != 0 or any(b<=a for a,b in zip(positions,positions[1:])):
        raise AssertionError('complete block trace must advance at each copy')
    for i,row in enumerate(trace[:-1]):
        target = min(row['produced']+quota,positions[-1])
        j = bisect_left(positions,target,i+1)
        elapsed = trace[j]['tstates']-row['tstates']
        result.append(dict(first=row['produced'],requested=target,produced=positions[j],copies=j-i,
            full_block_trace_interval=elapsed,bound_tstates=elapsed+32*(j-i)+RESUME+STOPPING+17))
    return max(result,key=lambda r:r['bound_tstates'])


def copy_paths():
    """Execute common copy-helper paths, excluding outer CALL and sync."""
    result=[]
    for name,destination,count,target in (('lower_high_byte',0xe020,3,0xe300),
            ('same_high_byte',0xe020,3,0xe080),('last_byte_wrap',0xffff,1,0)):
        values=[]
        for enabled in (False,True):
            code,labels = banked_zx0.build(fast_literal=True,fast_refill=True,token_boundaries=enabled)
            cpu = CPU(b'',b''); cpu.port_7ffd=0x17
            for i,value in enumerate(code): cpu.write8(banked_zx0.CODE+i,value)
            word(cpu,labels['slice_target'],target)
            def run(entry):
                cpu.pc,cpu.sp=entry,STACK; cpu.push(STOP); before=cpu.tstates
                while cpu.pc != STOP: cpu.step()
                if cpu.sp != STACK: raise AssertionError('copy-helper stack differs')
                return cpu.tstates-before
            sync = run(labels['slice_sync_target'])
            for i in range(count): cpu.write8(banked_zx0.INPUT+i,i+19)
            cpu.set_hl(banked_zx0.INPUT); cpu.set_de(destination); cpu.set_bc(count)
            cpu.a,cpu.carry = 0x93,True
            ticks = run(labels['slice_copy'])
            if cpu.a != 0x93 or not cpu.carry or cpu.bc() or cpu.de() != (destination+count)&65535:
                raise AssertionError('copy-helper registers/flags differ')
            if bytes(cpu.read8(destination+i) for i in range(count)) != bytes(i+19 for i in range(count)):
                raise AssertionError('copy-helper output differs')
            values.append(dict(copy_tstates=ticks,sync_tstates=sync))
        result.append(dict(path=name,length=count,before=values[0],after=values[1],
            delta_tstates=values[1]['copy_tstates']-values[0]['copy_tstates']))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw','storage-report','cache','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--quota',type=int,default=256)
    p.add_argument('--payload-start',type=lambda s:int(s,0),default=0xfff4,
        help='First compressed payload in the ring; FAP3 ring FFF0 plus 4-byte header is FFF4')
    args=p.parse_args(); raw=args.raw.read_bytes(); storage=json.loads(args.storage_report.read_text(encoding='utf-8'))
    if not storage['complete'] or storage['input_sha256'] != sha(raw) or not 1 <= args.quota <= 8192:
        raise ValueError('invalid storage/quota')
    report=dict(scope=__doc__,complete=False,release=False,baseline_commit='81779ce',
        input_sha256=sha(raw),quota=args.quota,copy_paths=copy_paths(),blocks=[],
        extra_per_copied_run_tstates=32,resume_bound_tstates=RESUME,stop_bound_tstates=STOPPING,
        external_call_tstates=17,irq_included=False,ula_included=False,disk_delivery_verified=False,
        first_payload_ring_offset=args.payload_start%65536)
    position,ring=0,args.payload_start%65536
    h=Harness(fast_literal=True,fast_refill=True,token_boundaries=True)
    report['decoder_sha256']=sha(h.code)
    for index,b in enumerate(storage['blocks']):
        expected=raw[position:position+b['decoded_bytes']]; position+=len(expected)
        payload=(args.cache/(b['sha256']+'.zx0')).read_bytes()
        if sha(expected)!=b['sha256'] or len(payload)!=b['zx0_bytes']: raise ValueError('block mismatch')
        h.begin(payload,expected,ring_start=ring); trace=[]
        h.run(len(expected),copy_trace=trace); h.finish()
        bound=bound_trace(trace,args.quota)
        h.begin(payload,expected,ring_start=ring)
        while h.cpu.produced<len(expected): h.run(min(h.cpu.produced+args.quota,len(expected)))
        actual=h.finish()
        # The first begin/refill is not lookahead; compare subsequent resumes.
        maximum=max((r['tstates']+17 for r in actual['slices'][1:]),default=0)
        if maximum>bound['bound_tstates']: raise AssertionError('measured resume exceeds bound')
        report['blocks'].append(dict(index=index,copy_boundaries=len(trace)-1,ring_start=ring,
            bound=bound,measured_relative_quota_max_resume=maximum,relative_quota_total=actual['tstates']))
        ring=(ring+len(payload)+4)%65536
        if index%25==0:
            args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(f'Latency trace/relative quota verified {index+1}/{len(storage["blocks"])}',flush=True)
    if position!=len(raw): raise AssertionError('incomplete coverage')
    worst=max(report['blocks'],key=lambda r:r['bound']['bound_tstates'])
    report.update(complete=True,summary=dict(blocks=len(report['blocks']),
        copy_boundaries=sum(r['copy_boundaries'] for r in report['blocks']),worst=worst,
        measured_max_resume=max(r['measured_relative_quota_max_resume'] for r in report['blocks']),
        total_relative_quota_tstates=sum(r['relative_quota_total'] for r in report['blocks'])))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__': main()
