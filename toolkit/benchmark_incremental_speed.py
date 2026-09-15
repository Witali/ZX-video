"""Compare current scheduling with the saved fddc21e v9 timing baseline."""
import argparse
import json
from pathlib import Path

from benchmark_playback_speed import measure
import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


def copy_counts():
    player,labels=codec.build_player(0,0,blocked=True,incremental=True)
    rows={}
    for name,target in (('lower_high_byte',0x8100),('same_high_byte',0x8008),('exact_target',0x8004)):
        cpu=CPU(player,b'');cpu.sp=0xBFF0
        cpu.write8(labels['slice_high_operand'],target>>8)
        cpu.write8(labels['slice_low_operand'],target&255)
        cpu.set_hl(0xA000);cpu.set_de(0x8000);cpu.set_bc(4)
        cpu.pc=labels['slice_copy'];cpu.push(0x5F00)
        while cpu.pc!=0x5F00:cpu.step()
        old=21*4-5;new=cpu.tstates+17  # Replaces inline LDIR with CALL copier.
        rows[name]=dict(previous_tstates=old,current_tstates=new,delta=new-old)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    old=json.loads(Path(__file__).with_name('playback_speed_cycles.json').read_text())
    options=dict(fast_draw=True,deadline=True,fast_disk=True,irq_disk=True,interleaved=True,
                 incremental=True,keepalive_fields=64,prefetch_quota=3,full_rom_clock=True)
    cases=[('setup_clock','setup_clock',{}),
           ('read_same_track_low','read_n',{}),
           ('read_same_track_high','read_n',dict(sector=8)),
           ('read_track_wrap','read_n',dict(sector=15)),
           ('read_full_dispatch','read_n',dict(cached=False)),
           ('producer_one_sector','producer_one',{}),
           ('producer_full_ring','producer_one',dict(count=320)),
           ('producer_end_of_stream','producer_one',dict(remaining=0)),
           ('schedule_due_no_io','prefetch_loop',dict(count=320,remaining=0))]
    rows={}
    for name,routine,settings in cases:
        before=old['routines'][name]['current_tstates'];after=measure(options,routine,**settings)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    def compare(before,routine,**settings):
        after=measure(options,routine,**settings)
        return dict(previous_tstates=before,current_tstates=after,delta=after-before)
    report=dict(timing_source=old['timing_source'],baseline_commit='fddc21e',
                scope=old['scope'],exclusions=old['exclusions'],assumptions=old['assumptions'],
                options=options,routines=rows,
                extra_paths=dict(
                    producer_full_ring_keepalive_due=compare(73,'producer_one',count=320,elapsed=64),
                    schedule_late_three_reads=compare(223,'prefetch_loop',count=100,elapsed=13)),
                copier_four_bytes=copy_counts(),
                interrupt_tstates=dict(fast_before=61,fast_after=61,fast_delta=0,
                    full_dispatch_normal=160,full_dispatch_break_key=186,
                    full_dispatch_pc_1f00_1f53=187,full_dispatch_pc_1f60_1fff=201),
                interrupt_scope='Includes 19 T IM2 acknowledgement, vector JP for full dispatcher, and ROM NOP/RET when used; old full dispatcher ran the uncounted ROM IM1 handler')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
