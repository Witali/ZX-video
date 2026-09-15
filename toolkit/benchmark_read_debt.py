"""Count scheduler paths in saved binaries; ROM/disk waits are excluded."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import fixture
from test_packet_lookahead import word


def measure(build, *, queue=200, unread=300, elapsed=13, deadline=6, same_track=True, first_action=False):
    cpu,labels,startup,_=fixture(build);cpu.trd=bytes(2560*256)
    for name,value in dict(ring_count=queue,disk_sectors_remaining=unread,
                           elapsed_fields=elapsed,next_frame_field=deadline,last_disk_fields=elapsed).items():
        word(cpu,labels,name,value)
    cpu.alt_h=elapsed>>8;cpu.alt_l=elapsed&255
    for name,value in dict(disk_track=3,disk_sector=2,fast_disk_track=3 if same_track else 2,
                           ring_write_region=1,ring_write_high=0xC0).items():cpu.write8(labels[name],value)
    cpu.write8(0x5CF5,3);cpu.pc=labels['prefetch_loop']
    stops={labels[n]:n for n in (('producer_one','ahead_prefetch','wait_field','flip_screen') if first_action else ('flip_screen',))}
    while cpu.pc not in stops:
        assert cpu.steps<10000
        cpu.step()
    return dict(tstates=cpu.tstates-startup,reads=cpu.dos_reads,action=stops[cpu.pc])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-build',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows={}
    cases={'late_with_reserve':{},'late_below_reserve':dict(queue=60),
           'late_full_ring':dict(queue=320),'late_eof':dict(queue=1,unread=0)}
    for same in (False,True):
        for left in (1,2,3,4):
            cases[f'first_action_{"same" if same else "new"}_track_{left}_fields']=dict(
                elapsed=10-left,deadline=10,same_track=same,first_action=True)
    for name,options in cases.items():
        before=measure(args.baseline_build,**options);after=measure(args.build,**options)
        rows[name]=dict(previous=before,current=after,delta_tstates=after['tstates']-before['tstates'])
    report=dict(baseline_commit='233179c',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='prefetch_loop through flip_screen entry, or first action entry; includes calling instruction',
        exclusions=['ROM service','disk latency','ULA contention','interrupt execution','HALT wait'],
        assumptions='reserve 64; quota 3; debt initially zero; same-track sector data mocked; keepalive not due',
        quota_initialization=dict(previous_tstates=20,current_tstates=115,delta=95,
                                  current_saturated_tstates=114),routines=rows,
        irq_tstates=dict(before=61,after=61,delta=0))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
