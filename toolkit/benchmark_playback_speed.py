"""Reproducible player CPU counts; ROM service, contention and waits excluded."""
import argparse
import json
from pathlib import Path

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


def measure(options, routine, *, sector=1, count=64, remaining=100, cached=True,
            elapsed=6, last_read=0, cached_track=None):
    player, labels = codec.build_player(3,0,blocked=True,clocked=True,**options)
    cpu = CPU(player,bytes(2560*256))
    cpu.port_7ffd=0x17;cpu.sp=0xBFF0 if options.get('irq_disk') else 0x5FF0
    values=dict(disk_track=3,disk_sector=sector,ring_write_high=0xC0,
                ring_write_region=1,fast_disk_track=(3 if cached else 255) if cached_track is None else cached_track,
                disk_interleaved=1,hold_counter=1)
    for name,value in values.items():
        if name in labels:cpu.write8(labels[name],value)
    for name,value in dict(ring_count=count,disk_sectors_remaining=remaining,
                           elapsed_fields=elapsed,last_disk_fields=last_read,next_frame_field=6).items():
        if name in labels:
            cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
    cpu.alt_l=elapsed&255;cpu.alt_h=elapsed>>8
    cpu.write8(0x5CF5,3);cpu.set_hl(0xC000);cpu.b=1
    cpu.pc=labels[routine];cpu.push(0x5F00)
    if routine=='isr':raise ValueError('use setup_clock for clock initialization')
    stop=labels['flip_screen'] if routine=='prefetch_loop' else 0x5F00
    while cpu.pc!=stop:
        if cpu.steps>10000:raise AssertionError('routine did not terminate')
        cpu.step()
    return cpu.tstates


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    current=dict(fast_draw=True,deadline=True,fast_disk=True,irq_disk=True,interleaved=True)
    rows={}
    cases=[('setup_clock','setup_clock',{}),
           ('read_same_track_low','read_n',{}),
           ('read_same_track_high','read_n',dict(sector=8)),
           ('read_track_wrap','read_n',dict(sector=15)),
           ('read_full_dispatch','read_n',dict(cached=False)),
           ('producer_one_sector','producer_one',{}),
           ('producer_full_ring','producer_one',dict(count=320)),
           ('producer_end_of_stream','producer_one',dict(remaining=0)),
           ('schedule_due_no_io','prefetch_loop',dict(count=320,remaining=0))]
    for name,routine,settings in cases:
        before=measure({},routine,**settings);after=measure(current,routine,**settings)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    result=dict(timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                scope='routine entry through RET; schedule through CALL flip_screen; ROM entry CALL/JP counted, ROM body excluded',
                exclusions=['ROM service','disk latency','contention','IRQ execution','HALT wait beyond its first 4 T'],
                assumptions='single sector, bank 1 queue at C000, track 3, interleaving active, no ring/bank wrap unless specified',
                comparison='v8 cpu-fields/legacy drawing versus v9 deadline/registers/trdos503-irq/interleaved',
                routines=rows,
                irq=dict(previous_tstates=88,current_tstates=61,delta=-27,
                         scope='includes 19 T IM2 acknowledgement and 14 T ROM mapper NOP/RET for current ISR'))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
