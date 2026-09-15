"""Compare saved clock/read wrappers, including exact IRQ instruction costs."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import fixture
from benchmark_read_debt import measure as measure_schedule
from test_packet_lookahead import run,word


def routine(build,name,kind=None):
    cpu,labels,_,_=fixture(build)
    if name!='setup_clock':run(cpu,labels,'setup_clock')
    cpu.trd=bytes(2560*256);cpu.alt_h=0;cpu.alt_l=100
    for key,value in dict(elapsed_fields=100,last_disk_fields=0,disk_sectors_remaining=20).items():word(cpu,labels,key,value)
    for key,value in dict(disk_track=3,disk_sector=2,fast_disk_track={'same':3,'new':2,'cold':255}.get(kind,3)).items():cpu.write8(labels[key],value)
    cpu.write8(0x5CF5,3);cpu.set_hl(0xC000);cpu.b=1
    return run(cpu,labels,name)


def irq(build,slow=False,return_pc=0x5F00):
    cpu,labels,_,_=fixture(build);run(cpu,labels,'setup_clock')
    if slow:
        for i,value in enumerate(bytes.fromhex('c300bd')):cpu.write8(0xBDBD+i,value)
    cpu.pc=0xBDBD;cpu.push(return_pc);start=cpu.tstates
    while cpu.pc!=return_pc:cpu.step()
    return cpu.tstates-start+19


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    def record(name,fn):
        before=fn(args.baseline_build);after=fn(args.build)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    for name in ('setup_clock','wait_field','keepalive_seek'):
        record(name,lambda b,n=name:routine(b,n))
    for kind in ('same','new','cold'):
        record('read_'+kind+'_track',lambda b,k=kind:routine(b,'read_n',k))
    record('fast_irq',irq)
    record('slow_irq_normal',lambda b:irq(b,True))
    record('slow_irq_break',lambda b:irq(b,True,0x1F54))
    record('late_scheduler',lambda b:measure_schedule(b)['tstates'])
    report=dict(baseline_commit='bcf303f',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='routine entry through RET; IRQ includes 19 T acknowledge and ROM mapper; scheduler through flip_screen entry',
        exclusions=['disk latency','TR-DOS service execution','ULA contention','HALT waiting'],
        assumptions='IRQ not injected into ordinary routines; stream track 3, sector 2, one sector; clock value 100',
        routines=rows,
        handler_switch=dict(previous_tstates=46,current_tstates=26,delta=-20),
        scheduler_snapshot=dict(previous_tstates=24,current_tstates=4,delta=-20),
        after_background=dict(previous_tstates=4,current_tstates=0,delta=-4))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
