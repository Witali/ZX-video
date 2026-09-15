"""Compare saved binaries, excluding contention; Fuse measures that separately."""
import argparse
import json
from pathlib import Path
import random
import struct

from benchmark_stream_drawing import read_build
from test_packet_lookahead import run, word
from validate_fast_sparse import CPU


def fixture(build):
    player,labels=read_build(build)
    cpu=CPU(player,b'');startup=0
    if 'bootstrap' in labels:
        while cpu.pc!=labels['start']:
            assert cpu.steps<20
            cpu.step()
        startup=cpu.tstates
    cpu.sp=0xBFF0;cpu.port_7ffd=0x17
    return cpu,labels,startup,0x6000 if 'bootstrap' in labels else 0x8000


def prepare(build,background):
    cpu,labels,startup,output=fixture(build)
    frame=struct.pack('<H',998)+random.Random(83).randbytes(998);body=frame*2
    stream=struct.pack('<HH',len(body)|0x8000,len(body))+body
    cpu.banks[0][:len(stream)]=stream
    word(cpu,labels,'ring_count',30);word(cpu,labels,'frames_remaining',3)
    cpu.write8(labels['ring_read_region'],1);cpu.write8(labels['ring_read_high'],0xC0)
    quanta=[]
    if background:
        while cpu.read8(labels['ahead_state'])!=2:quanta.append(run(cpu,labels,'ahead_prefetch'))
        while cpu.read8(labels['slice_output'])|cpu.read8(labels['slice_output']+1)<<8 < output+len(body):
            quanta.append(run(cpu,labels,'ahead_prefetch'))
    run(cpu,labels,'wait_packet');word(cpu,labels,'block_frame_pointer',output+len(frame))
    run(cpu,labels,'wait_packet')
    assert bytes(cpu.read8(output+i) for i in range(len(body)))==body
    return cpu.tstates-startup,quanta


def draw(build,command,payload):
    cpu,labels,startup,output=fixture(build);pointer=output+0xFD
    cpu.pc=labels[command];cpu.ix=pointer;cpu.alt_h=0x12;cpu.alt_l=0x34
    cpu.banks[5][:6912]=bytes([0xA5])*6912
    cpu.write8(labels['update_base'],0x40)
    for i,value in enumerate(payload):cpu.write8(pointer+i,value)
    while cpu.pc!=labels['command_loop']:
        assert cpu.steps<10000
        cpu.step()
    assert cpu.ix==pointer+len(payload)
    assert (cpu.alt_h,cpu.alt_l)==(0x12,0x34)
    return bytes(cpu.banks[5][:6912]),cpu.tstates-startup


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-build',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows={}
    def record(name,before,after):
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    for background in (False,True):
        before,bq=prepare(args.baseline_build,background);after,aq=prepare(args.build,background)
        assert bq==aq
        name='two_packets_background' if background else 'two_packets_foreground'
        record(name,before,after)
        if aq:rows[name].update(quantum_count=len(aq),quantum_max_tstates=max(aq))
    cases={
        'mask_0':('command_row',bytes([95,0,0,0,0])),
        'mask_32':('command_row',bytes([95,255,255,255,255])+bytes(range(32))),
        'points_0':('command_points',bytes([95,0])),
        'points_8':('command_points',bytes([95,8])+b''.join(bytes([i*4,i]) for i in range(8))),
        'spans_2x16':('command_spans',bytes([95,2,15])+bytes(range(16))+bytes([15])+bytes(range(16,32))),
        'rle_repeat_32':('command_row_rle',bytes([95,2,158,75])),
        'rle_literal_32':('command_row_rle',bytes([95,33,31])+bytes(range(32))),
    }
    for name,(command,payload) in cases.items():
        bs,bt=draw(args.baseline_build,command,payload);cs,ct=draw(args.build,command,payload)
        assert bs==cs
        record(name,bt,ct)
    _,_,startup,_=fixture(args.build)
    record('one_time_bootstrap',0,startup)
    report=dict(baseline_commit='a55744f',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='preparation: routine entry through RET; drawing: command entry through JP command_loop',
        exclusions=['ROM','disk latency','ULA contention','IRQ','scheduler'],routines=rows,
        assumptions='same packets; drawing row 95 at 4000h, command stream crosses a page',
        irq_tstates=dict(before=61,after=61,delta=0))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
