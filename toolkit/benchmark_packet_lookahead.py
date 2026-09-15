"""Count the same stored packets with foreground and background preparation."""
import argparse
import json
import random
import struct
from pathlib import Path

from benchmark_stream_drawing import read_build
from test_packet_lookahead import run,word
from validate_fast_sparse import CPU


def fixture(build):
    player,labels=read_build(build);cpu=CPU(player,b'');cpu.sp=0xBFF0;cpu.port_7ffd=0x17
    frame=struct.pack('<H',998)+random.Random(83).randbytes(998);data=frame*2
    stream=struct.pack('<HH',0x8000|len(data),len(data))+data
    cpu.banks[0][:len(stream)]=stream
    for name,value in dict(ring_count=30,frames_remaining=3).items():word(cpu,labels,name,value)
    cpu.write8(labels['ring_read_region'],1);cpu.write8(labels['ring_read_high'],0xC0)
    return cpu,labels,frame


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    for name in ('two_packets_foreground','two_packets_background'):
        totals=[];quanta=[]
        for current,build in ((False,args.baseline_build),(True,args.build)):
            cpu,labels,frame=fixture(build)
            if current and name.endswith('background'):
                while cpu.read8(labels['ahead_state'])!=2:quanta.append(run(cpu,labels,'ahead_prefetch'))
                while cpu.read8(labels['slice_output'])|cpu.read8(labels['slice_output']+1)<<8 < 0x8000+2*len(frame):
                    quanta.append(run(cpu,labels,'ahead_prefetch'))
            run(cpu,labels,'wait_packet')
            word(cpu,labels,'block_frame_pointer',0x8000+len(frame))
            run(cpu,labels,'wait_packet')
            assert bytes(cpu.banks[2][:len(frame)*2])==frame*2
            totals.append(cpu.tstates)
        rows[name]=dict(previous_tstates=totals[0],current_tstates=totals[1],delta=totals[1]-totals[0])
        if quanta:rows[name].update(quantum_count=len(quanta),quantum_max_tstates=max(quanta))
    report=dict(baseline_commit='0ec3bfe',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='routine entry through RET; same two 1000-byte stored packets including their 2000-byte block copy',
        exclusions=['ROM','disk latency','ULA contention','IRQ','scheduler'],
        routines=rows,checkpoint=dict(foreground_entry_tstates=55,foreground_with_call_tstates=72,
        background_suspend_entry_tstates=130,resume_entry_tstates=70),
        irq_tstates=dict(before=61,after=61,delta=0))
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
