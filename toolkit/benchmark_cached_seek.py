"""CPU-only read paths before/after cached seek; ROM execution is excluded."""
import argparse,json
from pathlib import Path
from benchmark_playback_speed import measure


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    before=dict(fast_draw=True,deadline=True,fast_disk=True,irq_disk=True,interleaved=True,
                incremental=True,keepalive_fields=64,prefetch_quota=3,full_rom_clock=True)
    after=dict(before,cached_seek=True)
    rows={}
    for name,routine,settings in (
        ('same_track','read_n',{}),('cold_dispatcher','read_n',dict(cached=False)),
        ('new_logical_track','read_n',dict(cached_track=2)),
        ('new_track_producer','producer_one',dict(cached_track=2)),
        ('sector15_wrap','read_n',dict(sector=15))):
        old=measure(before,routine,**settings);new=measure(after,routine,**settings)
        rows[name]=dict(previous_tstates=old,current_tstates=new,delta=new-old)
    report=dict(timing_source='https://www.zilog.com/docs/z80/um0080.pdf',baseline_commit='a936ac8',
        scope='Routine entry through RET, including RAM CALL/JP instructions; ROM bodies and native returns excluded',
        exclusions=['ROM service','disk latency','ULA contention','interrupt execution'],
        assumptions='logical track 3, sector 1, destination C000 bank 1, deadline quota 3, motor interval 64 fields, full ROM clock',
        routines=rows,irq_tstates=dict(before=61,after=61,delta=0,full_dispatcher=160))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
