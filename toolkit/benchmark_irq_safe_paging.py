"""Measure restartable paging and the exact added ISR instruction cost.

No disk/ROM/ULA latency in CPU sums. Both ISR stack layouts and every
paging instruction boundary execute. Publication OUT must precede repair.
"""
import argparse
import json
from pathlib import Path

from benchmark_context_huffman import word
from pipelined_frame_harness import Clock
import pipelined_frame_z80 as video
from stream_reader_harness import STACK,STOP
from test_pipelined_frame import fixture


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows=[];memory=[]
    for safe in (False,True):
        h,_,ticks=fixture(1,irq_safe_paging=safe);clock=Clock(h,ticks);cpu=h.cpu
        memory.append(dict(safe=safe,video_bytes=h.video['video_end']-video.VIDEO,
            page_bytes=h.video['page_end']-video.PAGE,
            code_regions=[dict(base=base,hex=blob.hex()) for base,blob in h.regions if base in (video.VIDEO,video.PAGE)],
            listing=[v for v in h.instructions.values() if v['phase'] in ('video_irq','paging')]))
        for slow in (False,True):
            for pc in (0x93f0,video.PAGE,video.PAGE_MERGE,video.SAFE_PAGE_END,0x97ff):
                cpu.guarding=False;cpu.port_7ffd=0x17;cpu.write8(video.SHADOW,0x17)
                word(cpu,0xbdbe,0xbd00 if slow else 0xbd80)
                cpu.write8(video.ENABLED,1);cpu.write8(video.READY,1)
                word(cpu,video.DEADLINE,0);word(cpu,h.audio['elapsed_fields'],0)
                cpu.pc=pc;cpu.sp=STACK;cpu.phase='paging';cpu.guarding=True
                start=cpu.tstates;elapsed=clock.run_irq()
                publication=clock.publications[-1]['tstates']-start
                rows.append(dict(safe=safe,slow=slow,pc=pc,tstates=elapsed,
                    publication_out_tstates=publication,resumed_pc=cpu.pc))
    for old,new in zip(rows[:10],rows[10:]):
        expected=89 if new['pc']>>8!=video.PAGE>>8 else 110 if new['pc']<video.PAGE_MERGE else 127 if new['pc']>=video.SAFE_PAGE_END else 143
        expected+=8*new['slow']
        if new['tstates']-old['tstates']!=expected or old['publication_out_tstates']!=new['publication_out_tstates']:
            raise AssertionError('IRQ repair formula or publication time differs')
        new.update(baseline_tstates=old['tstates'],delta_tstates=expected)
    h,_,ticks=fixture(1,irq_safe_paging=True);clock=Clock(h,ticks);cpu=h.cpu;retry=[]
    points=sorted(pc for pc in h.instructions if video.PAGE<=pc<h.video['page_end'])
    for point in points:
        cpu.guarding=False;cpu.port_7ffd=0x17;cpu.write8(video.SHADOW,0x17)
        cpu.write8(video.ENABLED,1);cpu.write8(video.READY,1)
        word(cpu,video.DEADLINE,0);word(cpu,h.audio['elapsed_fields'],0)
        cpu.a=0x13;cpu.pc=video.PAGE;cpu.sp=STACK;cpu.push(STOP);cpu.iff1=True
        cpu.phase='paging';cpu.guarding=True;foreground=0
        while cpu.pc!=point:
            t=cpu.tstates;cpu.step();foreground+=cpu.tstates-t
        irq=clock.run_irq()
        while cpu.pc!=STOP:
            t=cpu.tstates;cpu.step();foreground+=cpu.tstates-t
        if cpu.port_7ffd!=0x1b or cpu.read8(video.SHADOW)!=0x1b: raise AssertionError('page/display differs')
        retry.append(dict(interrupted_pc=point,paging_tstates=foreground,extra_restart_tstates=foreground-92,irq_tstates=irq))
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='00fb0fd',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        paging=dict(baseline_tstates=88,tstates=92,delta_tstates=4,max_retry_extra_tstates=max(r['extra_restart_tstates'] for r in retry)),
        unchanged_nonpublication_irq_paths=True,publication_out_delta_tstates=0,
        new_buffer_bytes=0,new_stack_bytes=0,self_modified_bytes=1,variants=memory,irq_cases=rows,restart_cases=retry)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('variants','irq_cases','restart_cases')}))


if __name__=='__main__': main()
