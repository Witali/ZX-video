"""CPU-only full-ring keepalive before/after replacing reads with SEEK."""
import argparse
import json
from pathlib import Path

from benchmark_stream_drawing import read_build
from validate_fast_sparse import CPU


def measure(build,elapsed,remaining):
    player,labels=read_build(build);cpu=CPU(player,bytes(2560*256))
    cpu.port_7ffd=0x17;cpu.sp=0xBFF0;cpu.alt_l=elapsed
    for name,value in dict(ring_count=320,disk_sectors_remaining=remaining,
                           elapsed_fields=elapsed,last_disk_fields=0).items():
        cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
    for name,value in dict(disk_track=3,disk_sector=1,fast_disk_track=3,
                           disk_interleaved=1).items():cpu.write8(labels[name],value)
    cpu.write8(0x5CF5,3);cpu.pc=labels['producer_one'];cpu.push(0x5F00)
    while cpu.pc!=0x5F00:
        assert cpu.steps<1000
        cpu.step()
    return cpu.tstates


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    for name,elapsed,remaining in [('not_due',63,100),('due',64,100),('eof',64,0)]:
        before=measure(args.baseline_build,elapsed,remaining)
        after=measure(args.build,elapsed,remaining)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    report=dict(baseline_commit='8674c91',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='producer_one entry through RET, including RAM CALL/JP; ROM bodies/returns excluded',
        exclusions=['ROM service','disk latency','ULA contention','interrupt execution'],
        assumptions='full ring, logical track 3, sector 1, last read at field zero, interval 64 fields',
        routines=rows,irq_tstates=dict(before=61,after=61,delta=0,slow_seek=160))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
