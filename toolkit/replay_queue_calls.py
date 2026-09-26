"""Replay every actual Fuse queue request with real Z80 and mocked TR-DOS.

Calls and queue states come from a complete, unpatched real-TRD run. IRQ,
ULA waits and ROM/controller time are excluded from deterministic CPU;
the original elapsed disk/seek intervals stay separate. Every copied byte
and state boundary is checked. This model does not redraw frames or AY.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from bank2_zx0 import install_decoder
from benchmark_bank_local_zx0 import disk_blocks
from benchmark_context_huffman import word
from benchmark_direct_slot_input import Harness as Producer
from benchmark_partial_slots import install_copy_guard
from build_fap3_trd import sha
from profile_integrated_timing import merged,overlap
from test_slot_queue import QueueHarness
import pipelined_frame_z80 as video


STATE=('count','phase','write_slot','read_slot','blocks_left','position','slice_output')


def queue_state(h):
    c=h.cpu
    return {key:(word(c,h.h.decoder.labels[key]) if key=='slice_output' else
                 word(c,h.q[key]) if key in ('blocks_left','position') else c.read8(h.q[key])) for key in STATE}


def phase(h,pc):
    row=h.instructions.get(pc)
    if row is None:return 'zx0'
    if row['phase']=='slot_bridge' and row['instruction']=='LDI':return 'packet_copy'
    return row['phase']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','trace-directory','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();report=dict(complete=False,release=False,scope=__doc__,volumes=[],
        source_sha256=sha(Path(__file__).read_bytes()),baseline_commit='5749312',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',models_queue_functions_only=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for part in (1,2,3):
        m,stream,blocks=disk_blocks(a.directory,part)
        trace_path=a.trace_directory/f'part{part:02}.json';trace=json.loads(trace_path.read_bytes())
        if (not trace['complete'] or trace['errors'] or trace['failure'] or
            trace['trd_sha256']!=m['trd_sha256'] or trace['debugger_installed_bytes']):raise ValueError('invalid playback trace')
        events=trace['queue_call_events']
        if len(events)%2:raise ValueError('unmatched queue calls')
        h=QueueHarness(Producer((a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes(),
            m['video_start_sector'],m['video_sectors'],inline_literals=True),len(blocks),demand_decode=True)
        if h.q!=m['queue_labels']:raise ValueError('queue layout differs')
        install_decoder(h.h.decoder)
        for change in m['bank2_zx0']['external_operands']:
            for i,value in enumerate(change['new_operand'].to_bytes(2,'little')):h.cpu.write8(change['operand_address']+i,value)
        guards=install_copy_guard(h);c=h.cpu
        raw=b''.join(b for _,b in blocks);cursor=0;prefills=0;takes=0;rows=[];totals=Counter()
        intervals=merged([(r['start_tstate'],r['end_tstate']) for r in trace['reads']+trace['seek_calls']])
        row=dict(part=part,trd_sha256=m['trd_sha256'],stream_sha256=sha(stream),
            trace_report_sha256=sha(trace_path.read_bytes()),frames=m['frames'],calls=rows,complete=False)
        report['volumes'].append(row)
        for index in range(0,len(events),2):
            before,after=events[index:index+2];kind=before['kind'].removesuffix('_start')
            if (before['kind']!=kind+'_start' or after['kind']!=kind+'_end' or
                before['page']&7!=7 or after['page']&7!=7 or after['tstate']<before['tstate']):
                raise ValueError('invalid external call ordering')
            c.port_7ffd=before['page'];c.write8(video.SHADOW,before['page'])
            if queue_state(h)!={key:before[key] for key in STATE}:
                raise AssertionError(('entry state differs',part,index//2,queue_state(h),before))
            c.set_bc(before['bc']);c.set_de(before['de']);c.a=before['a']
            hist=Counter(h.histogram);read_start=len(c.reads)
            entry=h.q[{'prefill':'prefill','take':'take','step':'step'}[kind]]
            ticks=h.call(entry);costs=Counter()
            for (pc,t),count in (h.histogram-hist).items():costs[phase(h,pc)]+=t*count
            if kind!='prefill':ticks+=17;costs['external_call']+=17
            if sum(costs.values())!=ticks:raise AssertionError('CPU accounting differs')
            totals.update(costs)
            if queue_state(h)!={key:after[key] for key in STATE}:
                raise AssertionError(('return state differs',part,index//2,queue_state(h),after))
            if kind=='prefill':prefills+=1
            if kind=='take':
                takes+=1;size=before['bc'];address=before['de']
                if (bytes(c.read8(address+i) for i in range(size))!=raw[cursor:cursor+size] or
                    c.de()!=(address+size)&65535):raise AssertionError('copied packet bytes differ')
                cursor+=size
            elapsed=after['tstate']-before['tstate'];service=overlap(intervals,before['tstate'],after['tstate'])
            if elapsed<ticks:raise AssertionError('elapsed time below deterministic CPU')
            # Service contains adapter CALL/JP costs too. Do not subtract it
            # from CPU a second time or call the remainder pure ULA time.
            rows.append(dict(index=index//2,kind=kind,start=before['tstate'],end=after['tstate'],
                elapsed_tstates=elapsed,cpu_tstates=ticks,elapsed_minus_cpu=elapsed-ticks,
                disk_service_elapsed=service,cpu_stages=dict(costs),sectors=len(c.reads)-read_start,
                return_a=after['a'],
                copied_bytes=before['bc'] if kind=='take' else 0,
                local_frame=(takes-1)//2 if kind=='take' else None))
            if index%1000==0:save();print(f'Disk {part}: exact real queue calls {index//2+1}/{len(events)//2}',flush=True)
        if (prefills!=1 or takes!=2*m['frames'] or cursor!=len(raw) or
            guards['checked_copy_bytes']!=cursor or c.read8(h.q['count']) or word(c,h.q['blocks_left']) or
            [r['sector'] for r in c.reads]!=h.h.positions):raise AssertionError('incomplete replay')
        groups={kind:dict(calls=sum(r['kind']==kind for r in rows),
            **{key:sum(r[key] for r in rows if r['kind']==kind) for key in
               ('elapsed_tstates','cpu_tstates','elapsed_minus_cpu','disk_service_elapsed','sectors','copied_bytes')})
            for kind in ('prefill','take','step')}
        row.update(complete=True,cpu_stages=dict(totals),groups=groups,**guards,
            instruction_histogram=[dict(pc=pc,tstates=t,count=n,phase=phase(h,pc)) for (pc,t),n in sorted(h.histogram.items())])
        save();print(json.dumps(dict(part=part,groups=groups,cpu_stages=dict(totals))),flush=True)
    report.update(complete=True,frames=sum(v['frames'] for v in report['volumes']))
    save()


if __name__=='__main__':main()
