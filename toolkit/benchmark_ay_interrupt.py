"""Verify complete fast/ROM IM2 costs, including the 50 Hz AY callback."""
import argparse
import json
from pathlib import Path

import ay_interrupt
from test_memory_clock import fixture
from test_packet_lookahead import word


def measure(count,slow=False,return_pc=0x5F00):
    cpu,labels=fixture(interleaved=True,direct_input=True,wrapped_input=True,audio_irq=True)
    cpu.write8(labels['audio_enabled'],1)
    cpu.write8(labels['audio_write_index'],1)
    word(cpu,labels,'audio_remaining',12)
    record=bytes([count])+b''.join(bytes([i,0]) for i in range(count))
    for i,b in enumerate(record):cpu.write8(ay_interrupt.QUEUE_BASE+i,b)
    if slow:
        cpu.write8(0xBDBE,0);cpu.write8(0xBDBF,0xBD)
    start=cpu.tstates;cpu.push(return_pc);cpu.pc=0xBDBD
    while cpu.pc!=return_pc:cpu.step()
    return cpu.tstates-start+19


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    records=[]
    for n in range(12):
        routine=367+83*n if n else 377
        fast=measure(n)
        assert fast==116+17+routine
        records.append(dict(register_writes=n,routine_tstates=routine,fast_irq_tstates=fast,
                            delta_vs_old_fast_irq=fast-116))
    slow=[]
    for ret,old in ((0x8001,184),(0x1F53,211),(0x1F54,210),(0x1F60,225)):
        current=measure(3,True,ret)
        assert current==old+17+367+83*3
        slow.append(dict(return_pc=ret,register_writes=3,previous_tstates=old,current_tstates=current,delta_tstates=current-old))
    report=dict(source='https://www.zilog.com/docs/z80/um0080.pdf',
                scope='nominal CPU, includes IM2 19 T and ROM NOP/RET trampoline; excludes ULA and disk latency',
                model=ay_interrupt.TSTATES,fast_irq=records,rom_irq=slow)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
